# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt


def execute(filters=None):
	filters.setdefault('handling', False)
	data = get_data(filters)
	return get_columns(filters), data


def get_columns(filters):
	cols = [
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

	if filters['handling']:
		cols.append("Handling:Currency:")

	cols.extend([
		"Policy::",
		"Supplier::",
		"Field Officer:Link/Field Officer:"
	])

	return cols


def get_data(filters):
	invoices = get_invoices(filters)
	uplift = get_uplift_in_mt(filters)
	rows = []


	for invoice in invoices:
		if invoice.handling_charges:
			filters['handling'] = True

	for invoice in invoices:
		policy_name = frappe.db.get_value("Customer Plant Variables", invoice.customer_plant_variables, "omc_policy")
		policy = get_policy(policy_name)
		rs = policy.execute(invoice.name)

		row = [
			invoice.customer,
			invoice.customer_code,
			invoice.transaction_date,
			invoice.invoice_number,
			invoice.qty if 'FC19' in invoice.item else "",
			invoice.qty if 'FC47.5' in invoice.item else "",
			uplift[invoice.customer],
			rs['additional_discount'],
			rs['additional_discount'] * invoice.qty * flt(invoice.item.replace('FC', '').replace('L', '')),
		]

		if filters['handling']:
			row.append(invoice.handling_charges)

		row.extend([
			policy_name,
			invoice.supplier,
			invoice.field_officer
		])

		rows.append(row)

	return rows

policies = {}
def get_policy(policy):
	if policy not in policies:
		p_obj = frappe.get_doc("OMC Policies", policy)
		p_obj.init()
		policies[policy] = p_obj
	return policies[policy]

def get_invoices(filters):

	cond = ' and r.field_officer = "{}"'.format(filters.field_officer) \
	if filters.field_officer else ''

	return frappe.db.sql("""
	Select i.*,
	r.field_officer, r.customer_code
	from `tabIndent Invoice` i left join
	`tabOMC Customer Registration` r
	on i.omc_customer_registration = r.name
	where i.docstatus = 1
	and i.supplier like '%ioc%'
	and i.item != 'FCBK'
	and i.transaction_date between "{from_date}" and "{to_date}"
	{cond}
	order by transaction_date asc
	""".format(cond=cond, **filters), as_dict=True)


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