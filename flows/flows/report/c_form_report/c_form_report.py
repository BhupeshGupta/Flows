# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
	data = list(get_data(filters))
	data.append(['', 'Total Amount', '', sum([x[3] for x in data]), sum([x[4] for x in data])])
	return get_columns(filters), data


def get_columns(filters):
	return [
		"Date:Date:95",
		"Invoice No:Data:95",
		"No Of Cylinders:Int:100",
		"Amount:Currency:100",
		"Amount With Tax:Currency:100",
		"Supplier::",
		"Tin No.::"
	]


def get_data(filters):
	tin_no = frappe.db.sql("SELECT tin_number FROM `tabSupplier` WHERE name = '{supplier}'".format(**filters))[0][0]
	return frappe.db.sql("""
		SELECT i.transaction_date, i.invoice_number, i.qty, i.actual_amount * 0.98 AS actual_amount,
		i.actual_amount AS amount_with_tax, s.name, s.tin_number
		FROM `tabIndent Invoice` i, `tabSupplier` s
		WHERE i.docstatus=1
		AND i.supplier = s.name
		AND s.tin_number = "{tin_no}"
		AND i.customer = "{customer}"
		AND i.transaction_date BETWEEN "{from_date}" AND "{to_date}";
		""".format(tin_no=tin_no, **filters))
