# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	columns = [
		"Consumer Number::",
		"Consumer Name::",
		"STATE of Customer::",
		"Supply Location::",
		"No of days Credit extended to customer::",
		"Annual Committed Volume MT::",
		"Volume uplifted till date in 2016-17::",
		"No.of Deposit Free Cylinders given::",
		"Type of Deposit Free Cyl: 19 / 35 / 47.5 / 19L / 35L / 47.5 L::",
		"C FORM COLLECTED UPTO(QR / YY)::",
		"C Form Pending After That::",
		"Handling Charges / MT:Currency:",
		"Proposed Discount / MT:Currency:",
		"F.Officer"
	]

	return columns, get_data(filters)


def get_c_form_stats(pair):
	c_form_data = frappe.db.sql(
		"""
		select fiscal_year,
			quarter,
			docstatus
		from `tabC Form Indent Invoice`
		where docstatus != 2
			and customer = "{}"
			and supplier like 'hpcl%'
		order by creation desc
		limit 10;
		""".format(pair.customer), as_dict=True
	)
	pending_count = 0
	last_c_form_collected = None
	for c_form in c_form_data:
		if c_form.docstatus == 0:
			pending_count += 1
		else:
			last_c_form_collected = c_form
			break

	return pending_count, last_c_form_collected


def get_data(filters):
	rows = []

	for pair in frappe.db.sql(
		"""
		select DISTINCT customer,
			supplier,
			omc_customer_registration,
			customer_plant_variables
		from `tabIndent Invoice`
		where supplier like "HPCL%"
			and docstatus = 1
			and transaction_date between "{}" and "{}"
		order by customer
		""".format(filters.from_date, filters.to_date),
		as_dict=True
	):
		omc = frappe.get_doc("OMC Customer Registration", pair.omc_customer_registration)
		cpv = frappe.get_doc("Customer Plant Variables", pair.customer_plant_variables)
		state = frappe.db.get_value("Address", {'customer': pair.customer, 'is_primary_address': 1}, 'state')
		cf_pending_count, last_cf_collected = get_c_form_stats(pair)


		rows.append([
			omc.customer_code,
			pair.customer,
			state.upper() if state else "",
			pair.supplier,
			"",
			"",
			"",
			"",
			"",
			"{} / {}".format(last_cf_collected.quarter, last_cf_collected.fiscal_year) if last_cf_collected else "-",
			cf_pending_count,
			cpv.transportation * 1000,
			cpv.discount * 1000,
			omc.field_officer
		])
	return rows
