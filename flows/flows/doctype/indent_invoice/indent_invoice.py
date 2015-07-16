# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

from flows.stdlogger import root
import frappe
import frappe.defaults
from flows import utils as flow_utils
from erpnext.controllers.selling_controller import StockController
from erpnext.accounts import utils as account_utils
from erpnext.accounts.party import get_party_account
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.stock.stock_ledger import make_sl_entries
from frappe.utils import today
from frappe.utils import cint
from frappe.utils import get_first_day
from flows.flows import payer


class IndentInvoice(StockController):
	def __init__(self, *args, **kwargs):
		super(IndentInvoice, self).__init__(*args, **kwargs)

	def before_submit(self):
		if not self.posting_date:
			self.posting_date = today()
			self.fiscal_year = account_utils.get_fiscal_year(self.get("transaction_date"))[0]

		self.check_previous_doc()
		self.make_gl_entries()
		self.make_stock_refill_entry()
		self.raise_transportation_bill()

	def check_previous_doc(self):
		if self.indent:
			indent = frappe.db.sql("""
	        SELECT name FROM `tabIndent` WHERE docstatus = 1 AND name = '{}'
	        """.format(self.indent))

			if not indent:
				frappe.throw("Indent {} not found. check if is canceled, amended or deleted".format(
					self.indent
				))

	def on_update_after_submit(self):
		if self.cross_sold == 0:
			cp = frappe.db.sql("""
			SELECT cp.name
			FROM `tabCross Purchase` cp,
			`tabCross Purchase Item` cpi
			WHERE cpi.parent = cp.name
			AND cpi.invoice = "{invoice}"
			AND cp.docstatus = 1;
			""".format(invoice=self.name), as_dict=True
			)
			if cp:
				frappe.throw(
					"This Indent Invoice is already settled in Cross Purchase {}".
						format(", ".join([x.name for x in cp]))
				)

	def cancel(self):
		super(IndentInvoice, self).cancel()
		self.set_missing_values()
		self.make_gl_entries()
		self.make_stock_refill_entry()
		self.cancel_transport_bill()

	def validate(self):
		self.set_missing_values()
		self.validate_branch_out_for_special_cases()

		if self.docstatus == 0:
			if self.amended_from != "":
				self.update_data_bank({
				'transportation_invoice': self.transportation_invoice,
				'credit_note': self.credit_note
				})
				self.transportation_invoice = ''
				self.credit_note = ''
			else:
				self.data_bank = ''

		if cint(self.indent_linked) == 1:
			if not (self.indent_item and self.indent_item != ''):
				frappe.throw('{} is required if invoice is linked with indent'.format('indent_item'))

			indent_item = frappe.get_doc("Indent Item", self.indent_item)
			indent = frappe.get_doc("Indent", indent_item.parent)

			self.vehicle = indent.vehicle

			self.customer = indent_item.customer
			self.item = indent_item.item
			self.qty = indent_item.qty
			self.rate = indent_item.rate

			self.indent = indent_item.parent

			self.load_type = indent_item.load_type
			self.payment_type = indent_item.payment_type
			self.tentative_amount = indent_item.amount

			self.indent_date = indent.posting_date
			self.logistics_partner = indent.logistics_partner
			self.supplier = indent.plant
			self.company = indent.company

		return super(IndentInvoice, self).validate()

	def make_gl_entries(self, repost_future_gle=True):
		gl_entries = self.get_gl_entries()

		root.debug("Gl Entry Map: {}".format(gl_entries))

		if gl_entries:
			make_gl_entries(gl_entries, cancel=(self.docstatus == 2),
							update_outstanding='Yes', merge_entries=False)

	def set_missing_values(self, *args, **kwargs):

		# self.fiscal_year = account_utils.get_fiscal_year(self.get("transaction_date"))[0]
		#
		# super(IndentInvoice, self).set_missing_values(*args, **kwargs)

		if self.supplier and self.supplier != '' and \
				self.company and self.company != '' and \
						cint(self.indent_linked) == 1 and cint(self.sub_contracted) == 0:
			warehouse_object = flow_utils.get_suppliers_warehouse_account(self.supplier, self.company)
			self.warehouse = warehouse_object.name

	def make_stock_refill_entry(self):
		if cint(self.sub_contracted) == 1:
			return

		supplier_warehouse_account = frappe.get_doc("Warehouse", self.warehouse)

		stock_refill_entries = self.convert_stock_in_place(
			supplier_warehouse_account,
			self.item.replace('F', 'E'),
			self.qty,
			self.item,
			self.qty,
			process='Refill'
		)

		root.debug({
		"stock_refill_entries": stock_refill_entries,
		"supplier_warehouse_account": supplier_warehouse_account.name,
		})

		make_sl_entries(stock_refill_entries)

	def convert_stock_in_place(self, warehouse, from_item, from_item_quantity, to_item, to_item_quantity, process=''):
		conversion_sl_entries = []

		conversion_sl_entries.append(
			self.get_sl_entry({
			"item_code": from_item,
			"actual_qty": -1 * from_item_quantity,
			"warehouse": warehouse.name,
			"company": warehouse.company,
			"process": process
			})
		)
		conversion_sl_entries.append(
			self.get_sl_entry({
			"item_code": to_item,
			"actual_qty": 1 * to_item_quantity,
			"warehouse": warehouse.name,
			"company": warehouse.company,
			"process": process
			})
		)

		return conversion_sl_entries

	def get_gl_entries(self, warehouse_account=None):

		gl_entries = []

		self.make_customer_gl_entry(gl_entries)

		# # merge gl entries before adding pos entries
		# gl_entries = merge_similar_entries(gl_entries)

		return gl_entries

	def validate_branch_out_for_special_cases(self):
		# Pull out config
		indent_invoice_settings = frappe.db.get_values_from_single(
			'*', None, 'Cross Sale Purchase Settings', as_dict=True
		)[0]

		if self.customer == indent_invoice_settings.customer_account:
			self.company = indent_invoice_settings.buyer_company
			self.logistics_partner = indent_invoice_settings.buyer_company

			self.handling_charges = 0
			self.payment_type = 'Direct'
			self.sub_contracted = 0
			self.cross_sold = 0
			self.indent_linked = 0

	def submit_branch_out_for_special_cases(self, gl_entries):

		# Pull out config
		indent_invoice_settings = frappe.db.get_values_from_single(
			'*', None, 'Cross Sale Purchase Settings', as_dict=True
		)[0]

		if self.customer == indent_invoice_settings.customer_account:
			# a/c as suggested by cross sale purchase settings, used to balance VK sale/purchase
			buyer_company = indent_invoice_settings.buyer_company
			supplier_account = flow_utils.get_supplier_account(buyer_company, self.supplier)

			gl_entries.append(
				self.get_gl_dict({
				"company": buyer_company,
				"account": indent_invoice_settings.buyer_purchase_head,
				"cost_center": indent_invoice_settings.buyer_purchase_cost_center,
				"debit": self.actual_amount,
				"remarks": "Against Invoice Id {}".format(self.invoice_number),
				"against_voucher": self.name,
				"against_voucher_type": self.doctype,
				})
			)

			gl_entries.append(
				self.get_gl_dict({
				"company": buyer_company,
				"account": supplier_account,
				"against": indent_invoice_settings.buyer_purchase_head,
				"credit": self.actual_amount,
				"remarks": "Against Invoice Id {}".format(self.invoice_number),
				"against_voucher": self.name,
				"against_voucher_type": self.doctype,
				})
			)

			return True

	def make_customer_gl_entry(self, gl_entries):

		self.set_missing_values()

		# Is Anti Patten but have to use this for now
		break_out = self.submit_branch_out_for_special_cases(gl_entries)
		if break_out:
			return

		customer_obj = frappe.get_doc("Customer", self.customer)

		logistics_partner_account = flow_utils.get_supplier_account(self.company, self.logistics_partner)

		logistics_company_object = frappe.get_doc("Company", self.logistics_partner)
		if logistics_company_object:
			customer_account = get_party_account(self.logistics_partner, self.customer, "Customer")
			ba_account = get_party_account(self.logistics_partner, self.company, "Customer")

		if self.actual_amount:

			company = self.company if self.payment_type == "Indirect" else self.supplier.split(' ')[0].title()

			# BA paid on behalf of Customer, but asks logistics partner to collect amount from customer
			# and pay him the same

			if self.payment_type == "Indirect":
				gl_entry_1_debit_cost_center = ''
				# get_party_account(company, self.customer, "Customer") \
				# 	if customer_obj.payment_company == 'BA' else
				gl_entry_1_debit_ac = logistics_partner_account
				gl_entry_1_credit_ac = payer.get_payer_account(company, self.supplier, self.customer,
															   self.payment_type)
			else:
				# Invert entry to match our side of books
				s_comp = frappe.db.get_value(
					"Company", company,
					["default_income_account", "cost_center"],
					as_dict=True
				)
				gl_entry_1_debit_ac = s_comp.default_income_account
				gl_entry_1_debit_cost_center = s_comp.cost_center
				gl_entry_1_credit_ac = payer.get_payer_account(company, self.supplier, self.customer,
															   self.payment_type)

			gl_entry_2_enabled = customer_obj.payment_company != 'BA' and self.payment_type == "Indirect"
			gl_entry_2_debit_ac = customer_account
			gl_entry_2_credit_ac = ba_account

			gl_entries.append(
				self.get_gl_dict({
				"account": gl_entry_1_debit_ac,
				"cost_center": gl_entry_1_debit_cost_center,
				"against": gl_entry_1_credit_ac,
				"debit": self.actual_amount,
				"remarks": "Against Invoice Id {}".format(self.invoice_number),
				"against_voucher": self.name,
				"against_voucher_type": self.doctype,
				"company": company
				})
			)

			gl_entries.append(
				self.get_gl_dict({
				"account": gl_entry_1_credit_ac,
				"against": gl_entry_1_debit_ac,
				"credit": self.actual_amount,
				"remarks": "Against Invoice Id {}".format(self.invoice_number),
				"against_voucher": self.name,
				"against_voucher_type": self.doctype,
				"company": company
				})
			)

			if logistics_company_object and gl_entry_2_enabled:
				# Entry in logistics partner account to get money form customer
				gl_entries.append(
					self.get_gl_dict({
					"account": gl_entry_2_debit_ac,
					"against": gl_entry_2_credit_ac,
					"debit": self.actual_amount,
					"remarks": "Against Invoice no. {}".format(self.invoice_number),
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"company": self.logistics_partner
					})
				)

				gl_entries.append(
					self.get_gl_dict({
					"account": gl_entry_2_credit_ac,
					"against": gl_entry_2_debit_ac,
					"credit": self.actual_amount,
					"remarks": "Against Invoice no. {}".format(self.invoice_number),
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"company": self.logistics_partner
					})
				)

	def get_gl_dict(self, args):
		"""this method populates the common properties of a gl entry record"""
		gl_dict = frappe._dict({
		'company': self.company,
		'posting_date': self.transaction_date,
		'voucher_type': self.doctype,
		'voucher_no': self.name,
		'aging_date': self.get("aging_date") or self.transaction_date,
		'remarks': self.get("remarks"),
		'fiscal_year': self.fiscal_year,
		'debit': 0,
		'credit': 0,
		'is_opening': "No"
		})
		gl_dict.update(args)
		return gl_dict

	def get_sl_entry(self, args):
		sl_dict = frappe._dict(
			{
			"posting_date": self.transaction_date,
			"posting_time": self.posting_time,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"actual_qty": 0,
			"incoming_rate": 0,
			"company": self.company,
			"fiscal_year": account_utils.get_fiscal_year(self.get("transaction_date"))[0],
			"is_cancelled": self.docstatus == 2 and "Yes" or "No"
			})

		sl_dict.update(args)

		return sl_dict

	def cancel_transport_bill(self):
		if self.transportation_invoice and self.transportation_invoice != '':
			sales_invoice = frappe.get_doc("Sales Invoice", self.transportation_invoice)
			if sales_invoice.docstatus != 2:
				sales_invoice.docstatus = 2
				sales_invoice.save()

		if self.credit_note and self.credit_note != '':
			credit_note = frappe.get_doc("Journal Voucher", self.credit_note)
			if credit_note.docstatus != 2:
				credit_note.docstatus = 2
				credit_note.save()

	def raise_transportation_bill(self):

		# Hard code skip for now, will fix this later
		if self.supplier == 'Aggarwal Enterprises' or \
						self.customer == 'VK Logistics':
			return

		# Pull out config
		indent_invoice_settings = frappe.db.get_values_from_single(
			'*', None, 'Indent Invoice Settings', as_dict=True)[0]
		root.debug(indent_invoice_settings)

		# Check if we are instructed to raise bills
		if not indent_invoice_settings.auto_raise_consignment_notes == '1':
			return

		qty_in_kg = get_conversion_factor(self.item) * float(self.qty)
		per_kg_rate_in_invoice = self.actual_amount / qty_in_kg
		landed_rate, transportation_rate = get_landed_rate_for_customer(self.customer, self.transaction_date)

		discount = 0
		credit_note = None

		# Customers purchase - landed rate
		rate_diff = per_kg_rate_in_invoice + transportation_rate - landed_rate
		rate_diff = round(rate_diff, 2)

		if rate_diff < float(indent_invoice_settings.min_rate_diff_for_discount):
			rate_diff = 0

		# Discount & Credit Note
		# Credit Note Only
		algo = frappe.db.get_value("Customer", self.customer, "rate_match_algorithm")
		algo = algo if algo else 'Discount & Credit Note'

		if rate_diff < 0:
			# Bump up transportation Rate
			transportation_rate += (-1 * rate_diff)
		elif rate_diff > 0 and algo == 'Discount & Credit Note':
			discount = transportation_rate if rate_diff >= transportation_rate else rate_diff
			rate_diff -= discount

		logistics_company_object = frappe.get_doc("Company", self.logistics_partner)

		if rate_diff > 0 and rate_diff * qty_in_kg > float(indent_invoice_settings.min_amount_for_credit_note) \
				and cint(indent_invoice_settings.auto_raise_credit_note) == 1:
			# Raise a credit note
			credit_note = self.raise_credit_note(
				logistics_company_object.name, rate_diff * qty_in_kg, indent_invoice_settings
			)

		transportation_invoice = self.raise_consignment_note(
			qty_in_kg, transportation_rate, indent_invoice_settings, discount_per_kg=discount
		)

		# Update terms of Consignment Note
		transportation_invoice.terms = self.get_terms_for_commercial_invoice(
			transportation_invoice, indent_invoice_settings,
			credit_note=credit_note,
			invoice=self,
		)

		# Save and Submit Credit Note and Consignment Note
		if credit_note:
			credit_note.user_remark = "Against Invoice no. {} and Consignment Note {}".format(
				self.invoice_number, transportation_invoice.name
			)
			credit_note.docstatus = 1
			credit_note.save()
			self.credit_note = credit_note.name

		transportation_invoice.docstatus = 1
		transportation_invoice.save()

		self.transportation_invoice = transportation_invoice.name
		self.transportation_invoice_rate = transportation_rate
		self.applicable_transportation_invoice_rate = transportation_rate - discount
		self.transportation_invoice_amount = self.applicable_transportation_invoice_rate * qty_in_kg

	def get_terms_for_commercial_invoice(self, commercial_invoice, settings, *args, **kwargs):

		credit_note = kwargs['credit_note'] if 'credit_note' in kwargs else None
		credit_amount = kwargs['credit_note'].total_credit if 'credit_note' in kwargs and kwargs['credit_note'] else 0

		if not ("terms_and_condition" in settings and settings['terms_and_condition'] != ''):
			return ""

		terms_template = frappe.get_doc('Terms and Conditions', settings['terms_and_condition']).terms

		if not terms_template:
			return ""

		customer_object = frappe.get_doc("Customer", self.customer)

		payable_amount = self.actual_amount + commercial_invoice.grand_total_export - credit_amount \
			if self.payment_type == 'Indirect' else commercial_invoice.grand_total_export - credit_amount

		from frappe.utils.jinja import render_template

		context = {
		'customer': customer_object,
		'total_payable_amount': payable_amount,
		'indent_invoice': self,
		'crn_raised': True if credit_note else False,
		'credit_note': credit_note,
		}

		return render_template(terms_template, context)


	def raise_credit_note(self, from_company, amount, indent_invoice_settings):
		credit_note_doc = {
		"docstatus": 0,
		"doctype": "Journal Voucher",
		"naming_series": "SCRN-",
		"voucher_type": "Credit Note",
		"is_opening": "No",
		"write_off_based_on": "Accounts Receivable",
		"company": from_company,
		"posting_date": self.transaction_date,
		"entries": [
			{
			"docstatus": 0,
			"doctype": "Journal Voucher Detail",
			"is_advance": "No",
			"idx": 1,
			"account": get_party_account(from_company, self.customer, "Customer"),
			"credit": amount
			},
			{
			"docstatus": 0,
			"doctype": "Journal Voucher Detail",
			"is_advance": "No",
			"idx": 2,
			"account": indent_invoice_settings.credit_note_write_off_account,
			"cost_center": indent_invoice_settings.credit_note_write_off_cost_center,
			"debit": amount,
			"user_remark": "Credit Note Against Bill No: {bill_no} Dt: {invoice_date}".format(
				bill_no=self.invoice_number, invoice_date=self.transaction_date, item=self.item, qty=self.qty,
				amt=self.actual_amount
			),
			"letter_head": "Arun Logistics"
			}
		],
		}

		data_bank = self.get_data_bank()
		if 'credit_note' in data_bank:
			credit_note_doc["amended_from"] = data_bank.credit_note

		credit_note = frappe.get_doc(credit_note_doc)
		credit_note.save()
		return credit_note

	def raise_consignment_note(self, qty_in_kg, transportation_rate_per_kg, indent_invoice_settings,
							   discount_per_kg=0):

		customer_object = frappe.get_doc("Customer", self.customer)

		description = ''

		if discount_per_kg > 0:
			description += "Rate: {} - {} (Paid By Consignor) per KG\n".format(transportation_rate_per_kg,
																			   discount_per_kg)

		description += """(Bill No: {bill_no} Dt: {invoice_date} Item: {item} Qty: {qty} Amt: {amt})""".format(
			bill_no=self.invoice_number, invoice_date=self.transaction_date, item=self.item, qty=self.qty,
			amt=self.actual_amount
		)

		consignment_note_json_doc = {
		"doctype": "Sales Invoice",
		"customer": self.customer,
		"customer_name": self.customer.strip(),
		"posting_date": self.transaction_date if today() < '2015-06-01' else self.posting_date,
		"posting_time": self.posting_time,
		"fiscal_year": self.fiscal_year,
		"entries": [
			{
			"qty": qty_in_kg,
			"rate": transportation_rate_per_kg - discount_per_kg,
			"item_code": "LPG Transport",
			"item_name": "LPG Transport",
			"description": description,
			"stock_uom": "Kg",
			"doctype": "Sales Invoice Item",
			"idx": 1,
			"income_account": "Service - AL",
			"cost_center": "Main - AL",
			"parenttype": "Sales Invoice",
			"parentfield": "entries",
			}
		],
		"against_income_account": "Service - AL",
		"select_print_heading": "Consignment Note",
		"company": "Arun Logistics",
		"letter_head": "Arun Logistics",
		"is_opening": "No",
		"naming_series": "SCN-",
		"price_list_currency": "INR",
		"currency": "INR",
		"plc_conversion_rate": 1,
		"tc_name": "Consignment Note",
		"consignor": self.supplier,
		"territory": customer_object.territory if customer_object.territory else
		indent_invoice_settings.default_territory,
		"remarks": "Against Bill No. {}""".format(self.invoice_number)
		}

		if frappe.db.exists("Address", "{}-Billing".format(self.customer.strip())):
			consignment_note_json_doc["customer_address"] = "{}-Billing".format(self.customer.strip())

		if consignment_note_json_doc['posting_date'] < '2015-06-01':
			consignment_note_json_doc["taxes_and_charges"] = "Road Transport"
		else:
			consignment_note_json_doc["taxes_and_charges"] = "Road Transport_June_1_15"

		consignment_note_json_doc[
			"tax_paid_by_supplier"
		] = 1 if customer_object.service_tax_liability == "Transporter" else 0

		data_bank = self.get_data_bank()
		if 'transportation_invoice' in data_bank:
			consignment_note_json_doc["amended_from"] = data_bank.transportation_invoice

		transportation_invoice = frappe.get_doc(consignment_note_json_doc)

		transportation_invoice.save()

		return transportation_invoice

	def update_data_bank(self, args):
		try:
			dbank = json.loads(self.data_bank)
		except:
			dbank = {}

		dbank.update(args)
		self.data_bank = json.dumps(dbank)

	def get_data_bank(self):
		try:
			dbank = frappe._dict(json.loads(self.data_bank))
		except:
			dbank = {}

		return dbank


def get_indent_for_vehicle(doctype, txt, searchfield, start, page_len, filters):
	indent_items_sql = """
        SELECT name, customer
        FROM `tabIndent Item`
		WHERE parent IN (SELECT name FROM tabIndent WHERE vehicle = "{vehicle}" AND docstatus = 1)
		AND {search_key} LIKE "{search_val}%"
		AND name NOT IN (SELECT ifnull(indent_item, '') FROM `tabIndent Invoice` WHERE docstatus = 1)
		ORDER BY customer ASC limit {start}, {page_len}
		""".format(
		vehicle=filters.get("vehicle"),
		start=start,
		page_len=page_len,
		search_key=searchfield,
		search_val=txt
	)

	return frappe.db.sql(indent_items_sql)


def get_conversion_factor(item):
	conversion_factor_query = """
        SELECT conversion_factor
        FROM `tabItem Conversion`
        WHERE item="{item}";
        """.format(item=item)

	val = frappe.db.sql(conversion_factor_query)[0][0]

	root.debug(val)

	return float(val) if val else 0


def get_landed_rate_for_customer(customer, date):
	month_start = get_first_day(date).strftime('%Y-%m-%d')

	rs = frappe.db.sql("""
    SELECT landed_rate, local_transport_rate
    FROM `tabCustomer Landed Rate`
    WHERE customer="{customer}" AND
    with_effect_from<="{date}" AND
    with_effect_from>="{month_start_date}"
    ORDER BY with_effect_from DESC LIMIT 1;
    """.format(customer=customer, date=date, month_start_date=month_start))
	if rs:
		return rs[0]
	frappe.throw('Landed Rate Not Found For Customer {} for date {}'.format(customer, date))


