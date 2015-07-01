# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt

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
		"Uplift In M.T:Float:",
		"Discount Per KG.:Currency:",
		"Total Discount:Currency:",
	]


def get_data(filters):
	invoices = get_invoices(filters)
	uplift = get_uplift_in_mt(filters)
	rows = []

	for invoice in invoices:
		rows.append([
			invoice.customer,
			get_sap_code(invoice.customer),
			invoice.transaction_date,
			invoice.invoice_number,
			invoice.qty if 'FC19' in invoice.item else "",
			invoice.qty if 'FC47.5' in invoice.item else "",
			uplift[invoice.customer],
			get_discount(uplift[invoice.customer]),
			get_discount(uplift[invoice.customer]) * invoice.qty * flt(invoice.item.replace('FC', '').replace('L', ''))
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

def get_uplift_in_mt(filters):
	rs = frappe.db.sql(
		"""
		select t.customer, sum(t.multi * t.t_qty / 1000) as mt
		 from (
			 select customer,
			 CASE
			  WHEN item = 'FC19' THEN '19'
			  when item = 'FC35' then '35'
			  when item like 'FC47.5%' then '47.5'
			 end  as multi,
			 item, sum(qty) as t_qty
			 from `tabIndent Invoice`
			 where docstatus = 1
			 and supplier like 'iocl%'
			 and item like 'FC%'
			 and transaction_date between "{from_date}" and "{to_date}"
			 group by customer, item
		 ) t
		 group by t.customer;
		""".format(**filters), as_dict=True
	)

	rs_map = {}
	for r in rs:
		rs_map[r.customer] = r.mt

	return rs_map


def get_discount(uplift):
	if float(uplift) >= 19:
		return 6
	elif float(uplift) >= 9.5:
		return 5
	return 4