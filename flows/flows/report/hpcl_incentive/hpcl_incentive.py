# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt

incentive_per_cylinder = {
	'FC19': 28,
	'FC35': 52,
	'FC47.5': 70,
	'FC47.5L': 70,
	'FC450': 663
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
		"FC19::",
		"FC35::",
		"FC47.5::",
		"Qty in Kg:Float:",
		"LPG Handling Charges:Currency:",
		"Incentive Amt.:Currency:",
		"Field Officer:Link/Field Officer:"
	]


def get_data(filters):
	invoices = get_invoices(filters)
	rows = []

	for invoice in invoices:
		net_incentive = incentive_per_cylinder[invoice.item] * invoice.qty
		qty_in_kg = float(invoice.qty) * flt(invoice.item.replace('FC', '').replace('L', ''))

		rows.append([
			invoice.customer,
			invoice.customer_code,
			invoice.transaction_date,
			invoice.invoice_number,
			invoice.actual_amount,
			invoice.actual_amount/qty_in_kg,
			invoice.handling_charges/invoice.qty,
			invoice.qty if 'FC19' in invoice.item else "",
			invoice.qty if 'FC35' in invoice.item else "",
			invoice.qty if 'FC47.5' in invoice.item else "",
			qty_in_kg,
			invoice.handling_charges,
			net_incentive,
			invoice.field_officer
		])

	return rows


def get_invoices(filters):

	cond = ' and r.field_officer = "{}" '.format(filters.field_officer) \
	if filters.field_officer else ''

	sql = """
	Select i.*, r.field_officer, r.customer_code
	from `tabIndent Invoice` i left join `tabOMC Customer Registration` r
	on i.omc_customer_registration = r.name
	where i.docstatus = 1
	and i.supplier like '%hpc%'
	and i.item != 'FCBK'
	and i.transaction_date between "{from_date}" and "{to_date}"
	{cond}
	order by i.customer, i.transaction_date, i.invoice_number
	""".format(cond=cond, **filters)

	return frappe.db.sql(sql, as_dict=True)