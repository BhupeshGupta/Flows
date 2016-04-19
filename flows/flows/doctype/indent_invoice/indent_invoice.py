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
from frappe.utils import cint, now
from frappe.utils import get_first_day
from flows.flows.doctype.indent.indent import validate_bill_to_ship_to
from flows.flows.pricing_controller import compute_base_rate_for_a_customer, get_customer_payment_info
from frappe.utils.formatters import format_value
import collections


class IndentInvoice(StockController):
	def __init__(self, *args, **kwargs):
		super(IndentInvoice, self).__init__(*args, **kwargs)

	def before_submit(self):
		if not self.posting_date:
			self.posting_date = today()
		self.fiscal_year = account_utils.get_fiscal_year(self.get("transaction_date"))[0]

		self.validate_purchase_rate()
		self.check_previous_doc()
		self.make_gl_entries()
		self.make_stock_refill_entry()
		self.raise_transportation_bill()

	def update_status(self):
		# Data Logging
		self.checked_by = frappe.session.user
		self.checked_on = now()

		old_workflow_state = self.workflow_state

		# State Logic
		if cint(self.cenvat) == 1:
			if self.excise:
				self.workflow_state = 'Ok'
			else:
				self.workflow_state = 'Missing Values'
		else:
			self.workflow_state = 'Ok'

		if old_workflow_state != self.workflow_state:
			self.add_comment('Log', "State Changed From {} to {}".format(old_workflow_state, self.workflow_state))

		# Printable Logic
		if self.workflow_state != 'Unchecked':
			self.printable = 1


	def populate_reports(self, tax=None):
		cpv = frappe.get_doc("Customer Plant Variables", self.customer_plant_variables)
		handling_per_kg = cpv.transportation + (self.handling if cint(self.adjusted) == 1 else 0)

		material_in_kg = self.qty * float(self.item.replace('FC', '').replace('L', ''))

		expected_handling = handling_per_kg * material_in_kg

		if not self.handling_charges:
			self.handling_charges = expected_handling
		else:
			handling_diff = abs(float(self.handling_charges - expected_handling))
			if round(handling_diff/material_in_kg, 2) > 0:
				frappe.throw("Handling mismatch! Handling should be around {}. Current is {}. Diff is {}".format(
					expected_handling, self.handling_charges, handling_diff
				))

		if tax:
			expected_cst = tax * material_in_kg
			if not self.cst:
				self.cst = expected_cst
			else:
				if round(abs(float(self.cst/material_in_kg - expected_cst/material_in_kg)), 2) > .10:
					frappe.throw("CST mismatch! CST should be around {}".format(expected_cst))


	def check_previous_doc(self):
		if self.indent:
			indent = frappe.db.sql("""
	        SELECT name FROM `tabIndent` WHERE docstatus = 1 AND name = '{}'
	        """.format(self.indent))

			if not indent:
				frappe.throw("Indent {} not found. check if is canceled, amended or deleted".format(
					self.indent
				))

		cpv = frappe.get_doc("Customer Plant Variables", self.customer_plant_variables)

		if cpv.docstatus != 1:
			frappe.throw("Customer Plant Variable {} need to be submitted.".format(cpv.name))

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

		validate_bill_to_ship_to(self.customer, self.ship_to, self.transaction_date)

	def cancel(self):
		super(IndentInvoice, self).cancel()
		self.set_missing_values()
		self.make_gl_entries()
		self.make_stock_refill_entry()
		self.cancel_transport_bill()

	def validate(self):
		self.invoice_number = self.invoice_number
		self.set_missing_values()
		self.validate_branch_out_for_special_cases()


		if not self.credit_account:
			self.credit_account = frappe.db.get_value("Indent Item", self.indent_item, "credit_account")

		if not self.service_tax_liability:
			self.service_tax_liability = frappe.db.get_value("Customer", self.customer, "service_tax_liability")



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

			payment_info = get_customer_payment_info(self.customer, self.supplier, self.transaction_date)
			self.customer_plant_variables = payment_info['cpv']
			self.omc_customer_registration = payment_info['registration']

			if not self.sales_tax:
				self.sales_tax = indent_item.sales_tax


			# IF ship to is defined in indent and not defined in invoice, copy value over to invoice
			if indent_item.ship_to and indent_item.ship_to.strip() != '':
				if not (self.ship_to and self.ship_to.strip() != ''):
					self.ship_to = indent_item.ship_to

			validate_bill_to_ship_to(self.customer, self.ship_to, self.transaction_date)
			self.cenvat = frappe.db.get_value("Customer", {'name': indent_item.customer}, 'cenvat')

		if not cint(self.adjusted) == 1:
			self.discount = 0
			self.handling = 0

		if not self.ship_to:
			self.ship_to = self.customer

		if 'Aggarwal' in self.supplier:
			frappe.throw("Use of Indent Invoice for `Aggarwal Enterprises` bills is deprecated. Please use Subcontracted Invoice from the same.")

		return super(IndentInvoice, self).validate()

	def validate_purchase_rate(self):

		if cint(self.indent_linked) != 1:
			return

		if self.customer == 'VK Logistics':
			return

		adjustment = {
		'discount': self.discount if self.discount else 0,
		'transportation': self.handling if self.handling else 0
		} if self.adjusted else {}

		pricing_detail = {}

		expected = compute_base_rate_for_a_customer(
			self.customer, self.supplier,
			self.item, self.sales_tax,
			self.transaction_date, extra_precision=1,
			adjustment=adjustment,
			details=pricing_detail,
			force_check_for_this_month_plant_rate=True
		) / float(self.item.replace('FC', '').replace('L', ''))

		qty_in_kg, per_kg_rate_in_invoice = self.get_invoice_rate()
		rate_diff = abs(round(expected - per_kg_rate_in_invoice, 2))

		if rate_diff > .10:
			frappe.throw(
				"""
				Rates do not agree with master, please check invoice (date, amount, handling, cst),
				there is a diff of {diff}, rate in master is {master} and in invoice is {invoice}
				""".format(diff=rate_diff, invoice=per_kg_rate_in_invoice, master=expected)
			)

		self.populate_reports(tax=pricing_detail['tax']+pricing_detail['surcharge'])

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

		if not self.actual_amount:
			return

		registration = frappe.get_doc("OMC Customer Registration", self.omc_customer_registration)
		material_account = frappe.db.get_value("OMC Customer Registration Credit Account", {
			'parent': registration.name,
			'type': self.credit_account
		}, '*', as_dict=True)

		gl_entries.append(
			self.get_gl_dict({
			"account": material_account.credit_account,
			"company": material_account.credit_account_company,
			"credit": self.actual_amount,
			"remarks": "Against Invoice Id {}".format(self.invoice_number),
			})
		)

		gl_entries.append(
			self.get_gl_dict({
			"account": material_account.debit_account,
			"company": material_account.debit_account_company,
			"debit": self.actual_amount,
			"remarks": "Against Invoice Id {}".format(self.invoice_number),
			})
		)

		if material_account.debit_account_company != material_account.credit_account_company:
			gl_entries.append(
				self.get_gl_dict({
				"account": self._get_account_(material_account.debit_account_company, material_account.credit_account_company),
				"company": material_account.debit_account_company,
				"credit": self.actual_amount,
				"remarks": "Against Invoice Id {}".format(self.invoice_number),
				})
			)

			gl_entries.append(
				self.get_gl_dict({
				"account": self._get_account_(material_account.credit_account_company, material_account.debit_account_company),
				"company": material_account.credit_account_company,
				"debit": self.actual_amount,
				"remarks": "Against Invoice Id {}".format(self.invoice_number),
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

	def load_transport_bill_variables(self):
		if not hasattr(self, 'transport_vars'):
			self.transport_vars = frappe.db.sql(
				"""
				SELECT *
				FROM `tabCustomer Sale`
				WHERE customer="{customer}"
				AND with_effect_from <= "{invoice_date}"
				AND ifnull(valid_up_to, "{invoice_date}") <= "{invoice_date}"
				AND docstatus = 1
				ORDER BY with_effect_from DESC LIMIT 1
				""".format(invoice_date=self.transaction_date, customer=self.customer),
				as_dict=True
			)
			if not self.transport_vars:
				frappe.throw("Customer Sale Variables Not Found")
			self.transport_vars = self.transport_vars[0]

	def transport_bill_variables(self):
		self.load_transport_bill_variables()
		transport_vars = self.transport_vars
		discount = transport_vars.display_rate - transport_vars.applicable_transport_rate
		return transport_vars.display_rate, discount, 0

	def raise_transportation_bill(self):

		# Hard code skip for now, will fix this later
		if self.supplier == 'Aggarwal Enterprises' or \
						self.customer == 'VK Logistics':
			return

		# Pull out config
		indent_invoice_settings = frappe.db.get_values_from_single(
			'*', None, 'Indent Invoice Settings', as_dict=True)[0]

		# Check if we are instructed to raise bills
		if not indent_invoice_settings.auto_raise_consignment_notes == '1':
			return

		qty_in_kg, per_kg_rate_in_invoice = self.get_invoice_rate()

		transportation_rate, discount, credit_note_per_kg = self.transport_bill_variables()

		if cint(self.adjusted) == 1 and self.handling != 0 and self.consignment_note_adjustment == 'Adjust Rate':
			adjustment_value = -1 * self.handling * (1 + self.cst / (self.actual_amount - self.cst))
			transportation_rate += adjustment_value
			transportation_rate = round(transportation_rate, 2)

		logistics_company_object = frappe.get_doc("Company", self.logistics_partner)

		credit_note = None
		# If there is min credit note amount and credit notes are enabled
		if credit_note_per_kg > 0 and credit_note_per_kg * qty_in_kg > float(
				indent_invoice_settings.min_amount_for_credit_note) \
				and cint(indent_invoice_settings.auto_raise_credit_note) == 1:
			# Raise a credit note
			credit_note = self.raise_credit_note(
				logistics_company_object.name, credit_note_per_kg * qty_in_kg, indent_invoice_settings
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

		if not commercial_invoice.tc_name:
			return ""

		terms_template = frappe.get_doc('Terms and Conditions', commercial_invoice.tc_name).terms

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
		'commercial_invoice': commercial_invoice,
		'doc': frappe._dict(self.as_dict()),
		'crn_raised': True if credit_note else False,
		'credit_note': credit_note,
		}

		self.load_transport_bill_variables()

		return render_template(terms_template, context) + '\n' + (
		self.transport_vars.terms if self.transport_vars.terms else '')

	def raise_consignment_note(
		self, qty_in_kg, transportation_rate_per_kg,
		indent_invoice_settings, discount_per_kg=0
	):

		registration = frappe.get_doc("OMC Customer Registration", self.omc_customer_registration)

		fiscal_year = account_utils.get_fiscal_year(self.get("posting_date"))[0]
		sales_invoice_conf = get_sales_invoice_config(registration.sales_invoice_company, fiscal_year)
		if not sales_invoice_conf:
			frappe.throw("Sales Invoice Config Not Found For Year {}, Company {}".format(sales_invoice_conf,
																						 registration.sales_invoice_company))

		customer_object = frappe.get_doc("Customer", self.customer)

		description = ''

		if discount_per_kg > 0:
			description += "Rate: {} - {} (Paid By Consignor) per KG\n".\
				format(transportation_rate_per_kg, discount_per_kg)

		d_m = collections.OrderedDict()
		d_m['Dt.'] = format_value(self.transaction_date, {"fieldtype": "Date"})
		d_m['Bill No.'] = self.invoice_number
		d_m['Amt.'] = '<strong>\u20b9{}</strong>'.format(format_value(self.actual_amount, {"fieldtype": "Currency"}))
		d_m['Qty in KG'] = '<strong>{} x {}: <em>{}</em></strong>'.format(self.item, self.qty, qty_in_kg)

		description += """({})""".format(', '.join(['{}: {}'.format(k, v) for k, v in d_m.items()]))

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
			"income_account": sales_invoice_conf.credit_account,
			"cost_center": sales_invoice_conf.cost_center,
			"parenttype": "Sales Invoice",
			"parentfield": "entries",
			}
		],
		"against_income_account": sales_invoice_conf.credit_account,
		"select_print_heading": "Transportation Invoice / Consignment Note",
		"company": registration.sales_invoice_company,
		"letter_head": registration.sales_invoice_company,
		"is_opening": "No",
		"naming_series": sales_invoice_conf.naming_series,
		"price_list_currency": "INR",
		"currency": "INR",
		"plc_conversion_rate": 1,
		"tc_name": sales_invoice_conf.tc_name,
		"consignor": self.supplier,
		"territory": customer_object.territory if customer_object.territory else
		indent_invoice_settings.default_territory,
		"remarks": "Against Bill No. {}""".format(self.invoice_number)
		}

		if frappe.db.exists("Address", "{}-Billing".format(self.customer.strip())):
			consignment_note_json_doc["customer_address"] = "{}-Billing".format(self.customer.strip())

		if consignment_note_json_doc['posting_date'] < '2015-06-01':
			consignment_note_json_doc["taxes_and_charges"] = "Road Transport"
		elif consignment_note_json_doc['posting_date'] < '2015-11-15':
			consignment_note_json_doc["taxes_and_charges"] = "Road Transport_June_1_15"
		else:
			consignment_note_json_doc["taxes_and_charges"] = "Road Transport_Nov_15_15"

		consignment_note_json_doc[
			"tax_paid_by_supplier"
		] = 1 if self.service_tax_liability == "Transporter" else 0

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

	def get_invoice_rate(self):
		qty_in_kg = get_conversion_factor(self.item) * float(self.qty)
		per_kg_rate_in_invoice = self.actual_amount / qty_in_kg

		return qty_in_kg, per_kg_rate_in_invoice

	def _get_account_(self, company, account):
		"""
		Hack to get account, will be refactored when erp will get ability.
		:param company:
		:param account:
		:return:
		"""
		acc = get_party_account(company, account, "Supplier")
		if not acc:
			acc = get_party_account(company, account, "Customer")
		return acc

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


def get_sales_invoice_config(company, fiscal_year):
	config_map = [
		frappe._dict({
		'company': 'Arun Logistics', 'fiscal_year': '2015-16', 'naming_series': 'SCN-',
		'credit_account': 'Service - AL', "cost_center": "Main - AL", "tc_name": "Consignment Note"
		}),
		frappe._dict({
		'company': 'Arun Logistics', 'fiscal_year': '2016-17', 'naming_series': 'SCN-16-',
		'credit_account': 'Service - AL', "cost_center": "Main - AL", "tc_name": "Consignment Note"
		}),
		frappe._dict({
		'company': 'Mosaic Enterprises Ltd.', 'fiscal_year': '2016-17', 'naming_series': 'SCN-MO-16-',
		'credit_account': 'Service - MO', "cost_center": "Main - MO", "tc_name": "Consignment Note Mosaic"
		})
	]

	for conf in config_map:
		if conf['company'] == company and conf['fiscal_year'] == fiscal_year:
			return conf

	return None
