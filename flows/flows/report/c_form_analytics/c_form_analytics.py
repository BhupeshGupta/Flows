# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
	data = list(get_data(filters))
	return get_columns(filters), data


def get_columns(filters):
	return [
		"C Form:Link/C Form Indent Invoice:100",
		"Supplier:Link/Supplier:120",
		"Customer:Link/Customer:200",
		"FY::80",
		"Quarter:Data:50",
		"C Form Number:Data:120",
		"Amount:Currency:100",
		"Amount With Tax:Currency:100",
		"Status::80"
	]


def get_data(filters):
	return frappe.db.sql("""
		SELECT name,
		supplier, customer,
		fiscal_year, quarter,
		c_form_number, amount,
		amount_with_tax,
		CASE docstatus
			WHEN 0 THEN 'Pending'
			ELSE 'Done'
		END

		FROM `tabC Form Indent Invoice`
		WHERE docstatus != 2
	""")