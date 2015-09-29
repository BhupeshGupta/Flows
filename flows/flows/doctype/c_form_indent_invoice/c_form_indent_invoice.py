# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class CFormIndentInvoice(Document):
	def before_submit(self):
		if not(self.c_form_number and self.c_form_number.strip() != ''):
			frappe.throw("Please enter C Form Number")

	def before_save(self):
		self.before_print()
		self.amount = sum([i.actual_amount for i in self.invoices[:-1]])
		self.cst = self.amount * 0.02
		self.amount_with_tax = self.amount * 1.02

	def before_print(self):
		start_date = frappe.db.get_value('Fiscal Year', self.fiscal_year, 'year_start_date')
		self.start_date, self.end_date = get_quarter_start_end(start_date, self.quarter)

		self.tin_no = frappe.db.sql(
			"SELECT tin_number FROM `tabSupplier` WHERE name = '{}'".format(self.supplier)
		)[0][0]

		self.invoices = frappe.db.sql("""
		SELECT i.transaction_date, i.invoice_number, i.qty, i.actual_amount * 100 / 102 AS actual_amount,
		i.actual_amount AS amount_with_tax
		FROM `tabIndent Invoice` i, `tabSupplier` s
		WHERE i.docstatus=1
		AND i.supplier = s.name
		AND s.tin_number = "{tin_no}"
		AND i.customer = "{customer}"
		AND i.transaction_date BETWEEN "{from_date}" AND "{to_date}";
		""".format(
			tin_no=self.tin_no,
			customer=self.customer,
			from_date=self.start_date,
			to_date=self.end_date), as_dict=True
		)

		self.invoices.append({
		'invoice_number': 'Total',
		'actual_amount': sum([i.actual_amount for i in self.invoices])
		})

	def validate(self):
		if frappe.db.sql("""
		SELECT name FROM `tabC Form Indent Invoice` WHERE docstatus != 2
		AND customer = "{customer}" AND quarter = "{quarter}"
		AND supplier = "{supplier}" AND fiscal_year = "{fiscal_year}"
		AND name != "{self_name}"
		""".format(customer=self.customer, quarter=self.quarter, supplier=self.supplier,
				   fiscal_year=self.fiscal_year, self_name=self.name)
		):
			frappe.throw("C Form Instance Already exist for this combination of customer, supplier, year and quarter")


def get_quarter_start_end(fiscal_start_date, quarter):
	from frappe.utils.data import add_months, get_last_day

	if quarter == 'I':
		offset = 0
	elif quarter == 'II':
		offset = 1
	elif quarter == 'III':
		offset = 2
	elif quarter == 'IV':
		offset = 3
	start_d = add_months(fiscal_start_date, offset * 3)
	end_d = get_last_day(add_months(fiscal_start_date, (offset * 3) + 2))
	return start_d, end_d.strftime('%Y-%m-%d')


def get_supplier_list(doctype, txt, searchfield, start, page_len, filters):
	start_date = frappe.db.get_value('Fiscal Year', filters['fiscal_year'], 'year_start_date')
	start_date, end_date = get_quarter_start_end(start_date, filters['quarter'])

	return frappe.db.sql(
		"""
		SELECT name
		FROM `tabSupplier`
		WHERE tin_number IN (
			SELECT tin_number
			FROM `tabSupplier`
			WHERE name IN (
				SELECT DISTINCT supplier
				FROM `tabIndent Invoice`
				WHERE customer = "{customer}"
				AND transaction_date BETWEEN "{start}" AND "{end}"
				)
			)
		AND supplier_type = 'OMC STATE'
		""".format(start=start_date, end=end_date, **filters)
	)
