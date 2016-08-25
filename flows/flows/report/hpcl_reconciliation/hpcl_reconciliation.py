# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt

def execute(filters=None):
	def row_mapper(row):
		def row_status(row):
			diff = 1000
			if row.error_type == 'None':
				diff = (flt(row.hpcl_debit_balance) + flt(row.balance) +
				2*(flt(row.hpcl_debit) - flt(row.total_credit)) +
				3*(flt(row.hpcl_credit) - flt(row.total_debit)))
			else:
				diff = flt(row.hpcl_debit_balance) + flt(row.balance)

			match = abs(diff) < 1

			if match and row.error_type == 'None': return 'Ok', abs(diff)
			if match and row.error_type != 'None': return 'Maybe', abs(diff)
			if not match and row.error_type == 'None': return 'Mismatch', abs(diff)
			if not match and row.error_type != 'None': return 'Suspicion', abs(diff)


		status, diff = row_status(row)
		return [
			row.customer,
			row.hpcl_debit_balance,
			row.hpcl_debit,
			row.hpcl_credit,
			row.balance,
			row.total_debit,
			row.total_credit,
			status,
			diff,
			row.balance_link
		]
	data_map = get_data(filters)

	return get_columns(), [row_mapper(i) for i in data_map.values()]


def get_data(filters):
	total_debit_credit_rs = frappe.db.sql("""
	select a.master_name as customer,
    round(sum(gl.debit), 2) as total_debit,
    round(sum(gl.credit), 2) as total_credit
    from `tabGL Entry` gl
    join `tabAccount` a
    on gl.account=a.name
    where gl.posting_date between "{date}" and "{date}"
    and gl.account like 'hpcl a/c %' and a.account_type='Payer'
    group by customer
	""".format(**filters), as_dict=True)

	total_balance_rs = frappe.db.sql("""
	select a.master_name as customer,
    round(sum(gl.debit) - sum(gl.credit), 2) as balance
    from `tabGL Entry` gl
    join `tabAccount` a
    on gl.account=a.name
    where gl.posting_date <= "{date}"
    and gl.account like 'hpcl a/c %' and a.account_type='Payer'
    group by customer
	""".format(**filters), as_dict=True)

	hpcl_rs = frappe.db.sql("""
	SELECT customer AS `customer`,
	balance AS `hpcl_debit_balance`,
	total_debit AS `hpcl_debit`,
	total_credit AS `hpcl_credit`,
	error_type,
	name as balance_link
	FROM `tabHPCL Customer Balance`
	WHERE date between '{date}' and '{date}'
	""".format(**filters), as_dict=True)

	rs_map = {hpcl_rs_i.customer: hpcl_rs_i for hpcl_rs_i in hpcl_rs}

	for i in total_debit_credit_rs:
		rs_map.get(i.customer, frappe._dict({})).update(i)

	for i in total_balance_rs:
		rs_map.get(i.customer, frappe._dict({})).update(i)

	return rs_map


def get_columns():
	return [
		"Customer:Link/Customer:250",
		"HPCL Dr Bal:Currency:100",
		"HPCL Dr:Currency:100",
		"HPCL Cr:Currency:100",
		"Our Dr Bal:Currency:100",
		"Our Dr:Currency:100",
		"Our Cr:Currency:100",
		"Status:Data:",
		"Diff:Currency:",
		"Balance:Link/HPCL Customer Balance:100"
	]