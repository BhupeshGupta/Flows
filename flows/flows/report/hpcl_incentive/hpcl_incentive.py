# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt

incentive_per_cylinder = {
'FC19': 28,
'FC35': 52,
'FC47.5': 70,
'FC47.5L': 70
}


def execute(filters=None):
	data = get_data(filters)
	return get_columns(filters), data


def get_columns(filters):
	return [
		"Customer::200",
		"ERO::",
		"Date:Date:",
		"Bill No.::",
		"Bill Amt.:Currency:",
		"Rate per Kg.:Currency:",
		"DA per Cylinder:Currency:",
		"FC 19::",
		"FC 35::",
		"FC 47.5::",
		"Qty in Kg:Int:",
		"LPG Handling Charges:Currency:",
		"Incentive Amt.:Currency:"
	]


def get_data(filters):
	invoices = get_invoices(filters)
	rows = []

	for invoice in invoices:
		net_incentive = incentive_per_cylinder[invoice.item] * invoice.qty
		qty_in_kg = invoice.qty * flt(invoice.item.replace('FC', '').replace('L', ''))

		rows.append([
			invoice.customer,
			get_sap_code(invoice.customer),
			invoice.transaction_date,
			invoice.invoice_number,
			invoice.actual_amount,
			invoice.actual_amount/qty_in_kg,
			invoice.handling_charges/invoice.qty,
			invoice.qty if 'FC19' in invoice.item else 0,
			invoice.qty if 'FC35' in invoice.item else 0,
			invoice.qty if 'FC47.5' in invoice.item else 0,
			qty_in_kg,
			invoice.handling_charges,
			net_incentive,
		])

	return rows


def get_invoices(filters):
	return frappe.db.sql("""
	Select * from `tabIndent Invoice`
	where docstatus = 1
	and supplier like '%hpc%'
	and item not like 'BK%'
	and transaction_date between "{from_date}" and "{to_date}"
	order by customer, transaction_date, invoice_number
	""".format(**filters), as_dict=True)


sap_code_map = {}


def get_sap_code(customer):
	if customer not in sap_code_map:
		sap_code_map[customer] = frappe.db.get_value("Customer", customer, fieldname="hpcl_erp_number")
	return sap_code_map[customer]
