# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


incentive_per_cylinder = {
'FC19': 50,
'FC47.5': 125,
'FC47.5L': 125
}

SERVICE_TAX = 12.36


def execute(filters=None):
	data = get_data(filters)
	return get_columns(filters), data


def get_columns(filters):
	return [
		"Customer::200",
		"SAP::",
		"Date:Date:",
		"Bill No.:Link/Indent Invoice:",
		"Qty 19Kg::",
		"Qty 47.5Kg::",
		"Incentive per cyl.:Currency:",
		"Net Incentive Claim:Currency:",
		"Assessable Value:Currency:",
		"Service Tax:Currency:"
	]


def get_data(filters):
	invoices = get_invoices(filters)
	rows = []

	from flows.stdlogger import root

	root.debug(invoices)

	for invoice in invoices:
		net_incentive = incentive_per_cylinder[invoice.item] * invoice.qty
		assessable_value = round((net_incentive / (100 + SERVICE_TAX)) * 100, 2)
		service_tax = round(net_incentive - assessable_value, 2)
		rows.append([
			invoice.customer,
			get_sap_code(invoice.customer),
			invoice.transaction_date,
			invoice.invoice_number,
			invoice.qty if 'FC19' in invoice.item else "",
			invoice.qty if 'FC47.5' in invoice.item else "",
			incentive_per_cylinder[invoice.item],
			net_incentive,
			assessable_value,
			service_tax
		])

	return rows


def get_invoices(filters):

	cond = ' and customer in (select name from `tabCustomer` where iocl_field_officer = "{}")'.format(filters.field_officer) \
	if filters.field_officer else ''

	return frappe.db.sql("""
	Select * from `tabIndent Invoice`
	where docstatus = 1
	and supplier like '%ioc%'
	and item != 'FCBK'
	and transaction_date between "{from_date}" and "{to_date}"
	{cond}
	order by transaction_date asc
	""".format(cond=cond, **filters), as_dict=True)


sap_code_map = {}


def get_sap_code(customer):
	if customer not in sap_code_map:
		sap_code_map[customer] = frappe.db.get_value("Customer", customer, fieldname="iocl_sap_code")
	return sap_code_map[customer]
