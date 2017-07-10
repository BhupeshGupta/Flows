# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from flows.flows.doctype.indent_invoice.indent_invoice import get_conversion_factor
from erpnext.accounts import utils as account_utils


class SubcontractedInvoice(Document):
	def autoname(self):
		if hasattr(self, 'force_name') and self.force_name:
			self.name = self.force_name
			return


		if self.posting_date < '2017-07-01':

			company_abbr = frappe.db.get_value("Company", self.company, "abbr")
			b_type = 'V' if self.bill_type == 'VAT' else 'R'
			naming_series = '{}#{}#'.format(company_abbr, b_type)
			self.name = make_autoname(naming_series + '.#####')

		else:
			company_abbr = frappe.db.get_value("Company", self.company, "abbr")
			fiscal_year = account_utils.get_fiscal_year(self.get("posting_date"))[0]
			naming_series = "{}/{}/.".format(company_abbr, fiscal_year)

			suffix_count = 16 - len(naming_series) + 1
			suffix = '#' * suffix_count
			self.name = make_autoname(naming_series + suffix)

	def before_submit(self):
		if not self.posting_date:
			self.fiscal_year = account_utils.get_fiscal_year(self.get("posting_date"))[0]

		self.raise_sales_invoice()

	def cancel(self):
		super(SubcontractedInvoice, self).cancel()
		self.cancel_sales_invoice()
		self.sales_invoice = ''

	def raise_sales_invoice(self):
		item_c_factor = get_conversion_factor(self.item)
		qty_in_kg = item_c_factor * float(self.quantity)
		rate_per_kg = self.amount_per_item / item_c_factor

		customer_object = frappe.get_doc("Customer", self.customer)
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")

		if self.company == 'Aggarwal Enterprises':
			item = {
				"qty": qty_in_kg,
				"rate": rate_per_kg,
				"item_code": "CLP",
				"item_name": "CLP",
				"stock_uom": "Kg",
				"doctype": "Sales Invoice Item",
				"idx": 1,
				"income_account": "Sales - {}".format(company_abbr),
				"cost_center": "Main - {}".format(company_abbr),
				"parenttype": "Sales Invoice",
				"parentfield": "entries",
			}
			select_print_heading = "Vat Invoice" if self.bill_type == 'VAT' else "Retail Invoice",
		elif self.company == 'Arun Logistics':
			item = {
				"qty": self.item,
				"rate": self.amount_per_item,
				"item_code": self.item,
				"item_name": self.item,
				"stock_uom": "Nos",
				"doctype": "Sales Invoice Item",
				"idx": 1,
				"income_account": "Sales - {}".format(company_abbr),
				"cost_center": "Main - {}".format(company_abbr),
				"parenttype": "Sales Invoice",
				"parentfield": "entries",
			}
			if self.posting_date < '2017-07-01':
				frappe.throw("Company enabled for billing only after GST.")
		else:
			frappe.throw("System not configured for this company invoicing.")

		if self.posting_date >= '2017-07-01':
			select_print_heading = 'Tax Invoice'

		consignment_note_json_doc = {
			"doctype": "Sales Invoice",
			"customer": self.customer,
			"customer_name": self.customer.strip(),
			"posting_date": self.posting_date,
			"fiscal_year": self.fiscal_year,
			"entries": [
				item
			],
			"against_income_account": "Sales - {}".format(company_abbr),
			"select_print_heading": select_print_heading,
			"company": self.company,
			"letter_head": self.company,
			"is_opening": "No",
			"name": self.name,
			"amended_from": self.amended_from,
			"price_list_currency": "INR",
			"currency": "INR",
			"plc_conversion_rate": 1,
			"territory": customer_object.territory if customer_object.territory else 'All Territories',
			"__islocal": True,
			"docstatus": 1,
			# "tc_name": "Arun Logistics Tax Invoice Product",
			# "terms": frappe.get_doc('Terms and Conditions', "Aggarwal LPG Invoice").terms
			# "remarks": "Against Bill No. {}""".format(self.invoice_number)
		}

		if self.description:
			consignment_note_json_doc['entries'][0]['description'] = self.description

		if frappe.db.exists("Address", "{}-Billing".format(self.customer.strip())):
			consignment_note_json_doc["customer_address"] = "{}-Billing".format(self.customer.strip())


		if self.posting_date >= '2017-07-01':
			consignment_note_json_doc["taxes_and_charges"] = "In State GST"

		transportation_invoice = frappe.get_doc(consignment_note_json_doc)

		transportation_invoice.save()

		self.sales_invoice = transportation_invoice.name

		return transportation_invoice

	def cancel_sales_invoice(self):
		sales_invoice = frappe.get_doc("Sales Invoice", self.name)
		if sales_invoice.docstatus != 2:
			sales_invoice.docstatus = 2
			sales_invoice.save()


def get_conversion_factor(item):
	conversion_factor_query = """
		SELECT conversion_factor
		FROM `tabItem Conversion`
		WHERE item="{item}";
		""".format(item=item)

	val = frappe.db.sql(conversion_factor_query)[0][0]

	return float(val) if val else 0