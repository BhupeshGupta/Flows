# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from flows.flows.doctype.indent_invoice.indent_invoice import get_conversion_factor
from erpnext.accounts import utils as account_utils
from frappe.utils.jinja import render_template


pricing_dict = {
	'2017-07': {
		'Advance': 37.00,
		'Credit': 40
	},
}


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
			naming_series = "{}{}/.".format(company_abbr, fiscal_year[2:])

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


	def compute_cost(self, target_billing_rate=None):
		plant_rate = frappe.db.sql("""
		SELECT *
		FROM `tabPlant Rate`
		WHERE plant="{plant}"
			AND with_effect_from <= DATE("{posting_date}")
		ORDER BY with_effect_from DESC
		LIMIT 1;
		""".format(plant=self.gst_bill_from, posting_date=self.posting_date), as_dict=True)[0]


		customer_obj = frappe.get_doc("Customer", self.customer)

		for_rate = plant_rate.for_rate
		if not target_billing_rate:
			target_billing_rate = pricing_dict[self.posting_date[:-3]][customer_obj.billing_slab]
		discount = for_rate-target_billing_rate

		if discount < 0:
			for_rate += abs(discount)
			discount = 0

		return for_rate, discount


	def raise_sales_invoice(self):
		item_c_factor = get_conversion_factor(self.item)
		qty_in_kg = item_c_factor * float(self.quantity)

		customer_object = frappe.get_doc("Customer", self.customer)
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")

		discount = 0
		cf = get_conversion_factor(self.item)

		if self.company == 'Aggarwal Enterprises':
			rate_per_kg = self.amount_per_item / item_c_factor

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
			select_print_heading = "Vat Invoice" if self.bill_type == 'VAT' else "Retail Invoice"
		elif self.company == 'Arun Logistics':

			amt = None
			if self.amount_per_item:
				amt = self.amount_per_item / cf

			rate_per_kg, discount = self.compute_cost(amt)

			item = {
				"qty": self.quantity,
				"rate": rate_per_kg * cf,
				"item_code": self.item,
				"item_name": self.item,
				"stock_uom": "Nos",
				"doctype": "Sales Invoice Item",
				"idx": 1,
				"income_account": "Sales - {}".format(company_abbr),
				"cost_center": "Main - {}".format(company_abbr),
				"parenttype": "Sales Invoice",
				"parentfield": "entries",
				# "amount": float(self.amount_per_item) * float(self.quantity)
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
			"docstatus": 0,
			"discount_amount": discount * cf * self.quantity
			# "tc_name": "Arun Logistics Tax Invoice Product",
			# "terms": frappe.get_doc('Terms and Conditions', "Aggarwal LPG Invoice").terms
			# "remarks": "Against Bill No. {}""".format(self.invoice_number)
		}

		if self.description:
			consignment_note_json_doc['entries'][0]['description'] = self.description

		c_addr = get_address(self.customer)
		if c_addr:
			consignment_note_json_doc["customer_address"] = c_addr

		if self.posting_date >= '2017-07-01':
			self.sales_tax = get_gst_sales_tax(consignment_note_json_doc["customer_address"])

		if not self.sales_tax:
			frappe.throw("Enter sales tax")

		consignment_note_json_doc['taxes_and_charges'] = self.sales_tax
		transportation_invoice = frappe.get_doc(consignment_note_json_doc)
		transportation_invoice.save()

		total_kgs = cf * self.quantity
		transportation_invoice.terms = self.get_terms_and_conditions(transportation_invoice, total_kgs)
		transportation_invoice.docstatus = 1
		transportation_invoice.save()

		self.sales_invoice = transportation_invoice.name

		return transportation_invoice

	def cancel_sales_invoice(self):
		sales_invoice = frappe.get_doc("Sales Invoice", self.name)
		if sales_invoice.docstatus != 2:
			sales_invoice.docstatus = 2
			sales_invoice.save()

	def get_terms_and_conditions(self, transportation_invoice, total_kgs):
		if self.company != 'Arun Logistics':
			return ""

		terms_template = frappe.get_doc('Terms and Conditions', 'Arun Logistics Tax Invoice Product').terms

		if not terms_template:
			return ""

		payable_amount = transportation_invoice.grand_total_export

		context = {
			'total_payable_amount': payable_amount,
			'indent_invoice': self,
			'ti': transportation_invoice,
			'total_kgs': total_kgs
		}
		return render_template(terms_template, context)


def get_conversion_factor(item):
	conversion_factor_query = """
		SELECT conversion_factor
		FROM `tabItem Conversion`
		WHERE item="{item}";
		""".format(item=item)

	val = frappe.db.sql(conversion_factor_query)[0][0]

	return float(val) if val else 0



def get_gst_sales_tax(address):
	gst_number, gst_status = frappe.db.get_value(
		"Address",
		address,
		['gst_number', 'gst_status']
	)

	if gst_status == 'Not Updated':
		frappe.throw("GST Not Found. Enter GST in customer Portal")
	elif gst_status == 'Unregistered':
		pass
	else:
		if not gst_number:
			frappe.throw("GST Not Found. Enter GST in customer Portal. Contact 7888691920.")


	if gst_number and gst_number[:2] == '03':
		return "In State GST"
	elif gst_number:
		return "Out State GST"
	else:
		# Unregistered customer
		return None


def get_address(customer):
	addr = frappe.db.sql(
		"""
		select name from `tabAddress` where customer = "{}" and is_primary_address = 1
		""".format(customer)
	)
	if addr:
		return addr[0][0]

	frappe.throw("Customer Address Not Found. Please add customer address and then update GST from portal. Contact 7888691920.")

	return None