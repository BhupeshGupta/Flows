# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from flows.stdlogger import root

import frappe
import frappe.defaults
from flows import utils as flow_utils
from erpnext.controllers.selling_controller import StockController
from erpnext.accounts import utils as account_utils

from erpnext.accounts.party import get_party_account

from erpnext.accounts.general_ledger import make_gl_entries

from erpnext.stock.stock_ledger import make_sl_entries
from frappe.utils import today, now


class IndentInvoice(StockController):
	def __init__(self, *args, **kwargs):
		super(IndentInvoice, self).__init__(*args, **kwargs)

	def on_submit(self):
		self.set_missing_values()
		super(IndentInvoice, self).on_submit()
		self.check_previous_doc()
		self.make_gl_entries()
		self.make_stock_refill_entry()
		self.raise_transportation_bill()


	def check_previous_doc(self):
		indent = frappe.db.sql("""
        SELECT name FROM `tabIndent` WHERE docstatus = 1 AND name = '{}'
        """.format(self.indent))

		if not indent:
			frappe.throw("Indent {} not found. check if is canceled, amended or deleted".format(
				self.indent
			))

	def cancel(self):
		super(IndentInvoice, self).cancel()
		self.set_missing_values()
		self.make_gl_entries()
		root.debug("Canceled {}".format(self.name))
		self.make_stock_refill_entry()
		self.cancel_transport_bill()

	def validate(self):
		if self.docstatus == 0:
			self.transportation_invoice = ''
		return super(IndentInvoice, self).validate()

	def make_gl_entries(self, repost_future_gle=True):
		gl_entries = self.get_gl_entries()

		root.debug("Gl Entry Map: {}".format(gl_entries))

		if gl_entries:
			make_gl_entries(gl_entries, cancel=(self.docstatus == 2),
			                update_outstanding='Yes', merge_entries=False)

	def set_missing_values(self, *args, **kwargs):

		super(IndentInvoice, self).set_missing_values(*args, **kwargs)

		self.indent_object = frappe.get_doc("Indent", self.indent)

		root.debug(str((self.indent, self.indent_item)))

		self.company, self.plant = self.indent_object.company, self.indent_object.plant

		root.debug({
		"indent_item_name": self.indent_item,
		"indent_name": self.indent,
		"customer": self.customer,
		"company": self.company,
		"plant": self.plant
		})

		if not self.posting_date:
			self.posting_date = today()
		if not self.posting_time:
			self.posting_time = now()
		if not self.fiscal_year:
			self.fiscal_year = account_utils.get_fiscal_year(date=self.posting_date)[0]

	def make_stock_refill_entry(self):
		plant_warehouse_account = flow_utils.get_suppliers_warehouse_account(self.plant, self.company)
		stock_refill_entries = self.convert_stock_in_place(
			plant_warehouse_account,
			self.item.replace('F', 'E'),
			self.qty,
			self.item,
			self.qty,
			process='Refill'
		)
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

	def make_customer_gl_entry(self, gl_entries):

		self.set_missing_values()

		plant_account = flow_utils.get_supplier_account(self.company, self.plant)
		logistics_partner_account = flow_utils.get_supplier_account(self.company, self.indent_object.logistics_partner)

		logistics_company_object = frappe.get_doc("Company", self.indent_object.logistics_partner)
		if logistics_company_object:
			customer_account = get_party_account(self.indent_object.logistics_partner, self.customer, "Customer")
			ba_account = get_party_account(self.indent_object.logistics_partner, self.company, "Customer")

		payment_type = frappe.db.sql("""
            SELECT payment_type
            FROM `tabIndent Item`
            WHERE name = '{}'""".format(self.indent_item)
		)[0][0]

		root.debug({
		"self.company": self.company,
		"self.plant": self.plant,
		"supplier_account": plant_account,
		"logistics_partner_account": logistics_partner_account,

		"customer_account": customer_account,
		"ba_account": ba_account,

		"payment_type": payment_type
		})

		if self.actual_amount and payment_type == "Indirect":

			# BA paid on behalf of Customer, but asks logistics partner to collect amount from customer
			# and pay him the same

			gl_entries.append(
				self.get_gl_dict({
				"account": logistics_partner_account,
				"against": plant_account,
				"debit": self.actual_amount,
				"remarks": "Against Invoice Id {}".format(self.name),
				"against_voucher": self.name,
				"against_voucher_type": self.doctype,
				})
			)

			gl_entries.append(
				self.get_gl_dict({
				"account": plant_account,
				"against": logistics_partner_account,
				"credit": self.actual_amount,
				"remarks": "Against Invoice Id {}".format(self.name),
				"against_voucher": self.name,
				"against_voucher_type": self.doctype,
				})
			)

			if logistics_company_object:
				# Entry in logistics partner account to get money form customer
				gl_entries.append(
					self.get_gl_dict({
					"account": customer_account,
					"against": ba_account,
					"debit": self.actual_amount,
					"remarks": "Against Invoice no. {}".format(self.name),
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"company": self.indent_object.logistics_partner
					})
				)

				gl_entries.append(
					self.get_gl_dict({
					"account": ba_account,
					"against": customer_account,
					"credit": self.actual_amount,
					"remarks": "Against Invoice no. {}".format(self.name),
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"company": self.indent_object.logistics_partner
					})
				)

	def get_gl_dict(self, args):
		"""this method populates the common properties of a gl entry record"""
		gl_dict = frappe._dict({
		'company': self.company,
		'posting_date': self.posting_date,
		'voucher_type': self.doctype,
		'voucher_no': self.name,
		'aging_date': self.get("aging_date") or self.posting_date,
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
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"actual_qty": 0,
			"incoming_rate": 0,
			"company": self.company,
			"fiscal_year": self.fiscal_year,
			"is_cancelled": self.docstatus == 2 and "Yes" or "No"
			})

		sl_dict.update(args)

		return sl_dict

	def cancel_transport_bill(self):
		sales_invoice = frappe.get_doc("Sales Invoice", self.transportation_invoice)
		if sales_invoice.docstatus != 2:
			sales_invoice.docstatus = 2
			sales_invoice.save()

	def raise_transportation_bill(self):

		qty_in_kg = get_conversion_factor(self.item) * float(self.qty)
		per_kg_rate_in_invoice = self.actual_amount / qty_in_kg

		landed_rate, transportation_rate = get_landed_rate_for_customer(self.customer, self.posting_date)
		rate_diff = landed_rate - per_kg_rate_in_invoice

		actual_transportation_rate = rate_diff if rate_diff > 0 else 0

		visible_transportation_rate = max(transportation_rate, rate_diff)

		discount = visible_transportation_rate - actual_transportation_rate

		credit_note_amount = -1 * rate_diff if rate_diff < 0 else 0
		if credit_note_amount > 0:
			# TODO: Raise a CN
			pass


		# Invoice Description
		invoice_description = ''
		if discount > 0:
			invoice_description += "Rate per KG: {rate} Discount per KG: {discount}\n".format(
				rate=visible_transportation_rate, discount=discount
			)
		invoice_description += """(Bill No: {bill_no} Dt: {invoice_date} Item: {item} Qty: {qty} Amt: {amt})""".format(
			bill_no=self.name, invoice_date=self.posting_date, item=self.item, qty=self.qty, amt=self.actual_amount
		)

		consignment_note_json_doc = {
		"doctype": "Sales Invoice",
		"customer": self.customer,
		"customer_name": self.customer.strip(),
		"customer_address": "{}-Billing".format(self.customer.strip()),
		"posting_date": today(),
		"posting_time": now(),
		"entries": [
			{
			"qty": qty_in_kg,
			"rate": actual_transportation_rate,
			"item_code": "LPG Transport",
			"item_name": "LPG Transport",
			"stock_uom": "Kg",
			"doctype": "Sales Invoice Item",
			"description": invoice_description,
			"idx": 1,
			"income_account": "Service - AL",
			"parenttype": "Sales Invoice",
			"parentfield": "entries",
			}
		],
		"against_income_account": "Service - AL",
		"select_print_heading": "Consignment Note",
		"company": "Arun Logistics",
		"letter_head": "Arun Logistics",
		"is_opening": "No",
		"naming_series": "CN-",
		"price_list_currency": "INR",
		"currency": "INR",
		"plc_conversion_rate": 1,
		"tc_name": "Consignment Note",
		"consignor": self.indent_object.plant,
		"remarks": "Consignment Note Against Invoice no. {}".format(self.name)
		}

		customer_object = frappe.get_doc("Customer", self.customer)

		if customer_object.service_tax_liability == "Transporter":
			consignment_note_json_doc["taxes_and_charges"] = "Road Transport"

		transportation_invoice = frappe.get_doc(consignment_note_json_doc)

		transportation_invoice.save()

		transportation_invoice.terms = self.get_terms_for_commercial_invoice(transportation_invoice, customer_object)

		transportation_invoice.docstatus = 1

		transportation_invoice.save()

		frappe.db.sql("UPDATE `tabIndent Invoice` SET transportation_invoice='{}'".format(
			transportation_invoice.name
		))

	def get_terms_for_commercial_invoice(self, commercial_invoice, customer_object):
		payment_type = frappe.db.sql("""
                SELECT payment_type
                FROM `tabIndent Item`
                WHERE name = '{}'""".format(self.indent_item)
		)[0][0]

		terms_template = frappe.get_doc('Terms and Conditions', 'Consignment Note').terms

		payable_amount = '{} ({} + {})'.format(
			self.actual_amount + commercial_invoice.grand_total_export,
			self.actual_amount,
			commercial_invoice.grand_total_export,
		) if payment_type == 'Indirect' else commercial_invoice.grand_total_export

		return terms_template.format(
			service_tax_paid_by=customer_object.service_tax_liability,
			total_payable_amount=payable_amount
		)


def get_indent_for_vehicle(doctype, txt, searchfield, start, page_len, filters):
	indent_items_sql = """
        SELECT name, customer
        FROM `tabIndent Item`
		WHERE parent IN (SELECT name FROM tabIndent WHERE vehicle = "{vehicle}" AND docstatus = 1)
		AND {search_key} LIKE "{search_val}%"
		AND name NOT IN (SELECT indent_item FROM `tabIndent Invoice` WHERE docstatus = 1)
		ORDER BY customer ASC limit {start}, {page_len}
		""".format(
		vehicle=filters["vehicle"],
		start=start,
		page_len=page_len,
		search_key=searchfield,
		search_val=txt
	)

	return frappe.db.sql(indent_items_sql)


def get_conversion_factor(item):
	conversion_factor_query = """
        select conversion_factor
        from `tabItem Conversion`
        where item='{item}';
        """.format(item=item)

	val = frappe.db.sql(conversion_factor_query)[0][0]

	root.debug(val)

	return float(val) if val else 0


def get_landed_rate_for_customer(customer, date):
	return frappe.db.sql("""
    SELECT landed_rate, local_transport_rate
    FROM `tabCustomer Landed Rate`
    WHERE customer='{customer}' AND
    with_effect_from<='{date}'
    ORDER BY with_effect_from DESC LIMIT 1;
    """.format(customer=customer, date=date))[0]
