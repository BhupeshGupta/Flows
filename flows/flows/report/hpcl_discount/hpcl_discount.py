# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt

def execute(filters=None):
	return get_columns(filters), get_data(filters)



def get_data(filters):
	rows = []

	for invoice in frappe.db.sql(
		"""
		select i.*, r.customer_code from `tabIndent Invoice` i
		left join `tabOMC Customer Registration` r
		on i.omc_customer_registration = r.name
		where i.docstatus = 1
		and i.supplier like 'HPCL%'
		and i.transaction_date between "{from_date}" and "{to_date}"
		and ifnull(i.discount, 0) != 0
		order by i.customer, i.transaction_date
		""".format(**filters), as_dict=True
	):

		policy_name = frappe.db.get_value("Customer Plant Variables", invoice.customer_plant_variables, "omc_policy")
		policy = get_policy(policy_name)
		rs = policy.execute(invoice.name)
		itm = flt(invoice.item.replace('FC', '').replace('L', ''))

		rows.append([
			invoice.transaction_date,
			invoice.invoice_number,
			invoice.customer,
			invoice.customer_code,
			itm,
			invoice.qty,
			rs['total_discount_passed'],
			rs['discount_in_invoice'],
			rs['additional_discount'],
			rs['additional_discount'] * invoice.qty * itm,
			invoice.name
		])

	return rows


def get_columns(filters):
	return [
		"Date:Date:",
		"Doc No:Data:",
		"Customer:Link/Customer:250",
		"Customer Code::",
		"Package::",
		"Qty::30",
		"Discount Passed:Currency:",
		"Discount In Invoice:Currency:",
		"Discount To Be Claimed:Currency:",
		"Claim Amount:Currency:",
		"II:Link/Indent Invoice:"
	]

policies = {}
def get_policy(policy):
	if policy not in policies:
		p_obj = frappe.get_doc("OMC Policies", policy)
		p_obj.init()
		policies[policy] = p_obj
	return policies[policy]