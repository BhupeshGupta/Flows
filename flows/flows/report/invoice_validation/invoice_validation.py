# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
	return get_columns(filters), get_data(filters)


def get_columns(filters):
	return [
		"Date:Date:",
		"Invoice:Link/Indent Invoice:",
		"Customer:Link/Customer:250",
		"Item:Data:",
		"Qty:Int:",
		"Handling:Currency:",
		"Bill Amount:Currency:",
		"Transport:Currency:",
		"Landed:Currency:",
		"Supplier:Link/Supplier:150"
	]

def get_data(filters):
	def get_conversion_factor(item):
		return float(item.replace('FC', '').replace('L', ''))

	rows = []

	for data in frappe.db.sql("""
	SELECT name, transaction_date,
	supplier, customer,
	item, qty,
	payment_type, load_type,
	ifnull(handling_charges, 0) as handling_charges,
	ifnull(actual_amount, 0) as actual_amount,
	ifnull(cst, 0) as cst,
	ifnull(excise, 0) as excise,
	ifnull(transportation_invoice_amount, 0) as transportation_invoice_amount
	FROM `tabIndent Invoice`
	WHERE transaction_Date BETWEEN "{from_date}" AND "{to_date}"
	AND docstatus = 1
	AND item like 'FC%' and item not like '%BK%'
	order by customer, supplier, transaction_date;
	""".format(**filters), as_dict=True):

		c_factor = get_conversion_factor(data.item) * data.qty

		rows.append([
			data.transaction_date,
			data.name,
			data.customer,
			data.item,
			data.qty,
			data.handling_charges / c_factor,
			data.actual_amount / c_factor,
			data.transportation_invoice_amount / c_factor,
			(data.actual_amount + data.transportation_invoice_amount) / c_factor,
			data.supplier,
		])

	return rows