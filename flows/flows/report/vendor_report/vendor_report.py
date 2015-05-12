# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from flows.flows.report.stock_register.stock_register import execute as stock_register_exec


def execute(filters=None):
	columns, data = ["Vendor:150:"], []

	rs = frappe.db.sql("""
	SELECT * FROM `tabWarehouse`
	WHERE master_type='Sales Person'
	AND ifnull(master_name, '') != ''""",
					   as_dict=True)

	sr_columns_global = None
	for r in rs:
		sr_columns, sr_data = stock_register_exec(filters=frappe._dict({
		'from_date': filters.date,
		'to_date': filters.date,
		'item_code': filters.item_code,
		'warehouse': r.name,
		'bifurcate': filters.bifurcate
		}))
		sr_columns_global = sr_columns

		row = [r.master_name]
		row.extend(sr_data[0][1:])

		data.append(row)

	columns.extend(sr_columns_global[1:])

	return columns, data
