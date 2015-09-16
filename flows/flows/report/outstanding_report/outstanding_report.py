# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from flows.utils import get_ac_debit_balances_as_on


def execute(filters=None):
	customer_list = [x[0] for x in frappe.db.sql("""SELECT name FROM `tabCustomer` ORDER BY name ASC""")]
	debit_balances_list = get_ac_debit_balances_as_on(filters.date)
	debit_balance_map = {x.account: x.debit_balance for x in debit_balances_list}

	rows = []
	for customer in customer_list:
		if customer not in debit_balance_map:
			continue
		rows.append([customer, debit_balance_map[customer]])

	return get_columns(), rows


def get_columns():
	return [
		"Customer:Link/Customer:",
		"Dr Balance:Currency:"
	]

	# def get_balances(filters=None):
	# company_list = [
	# 		'Arun Logistics', 'VK Logistics',
	# 		'Mosaic Enterprises Ltd.', 'Alpine Energy',
	# 		'Ludhiana Enterprises Ltd.'
	# 	]
	#
	# 	filters.company_list = company_list
	# 	account_ordinal_range = frappe.db.sql("select lft, rgt from `tabAccount` where name like 'Accounts Receivable
	#  - "
	# 										  "%'")
	# 	account_condition = "({})".format(
	# 		' or '.join([
	# 			'(lft > {} and rgt < {})'.format(lft, rgt) for lft, rgt in account_ordinal_range
	# 		])
	# 	)
	#
	# 	frappe.db.sql("""
	# 	SELECT REPLACE(account, CONCAT(' -', SUBSTRING_INDEX(account, '-',-1)), '') AS account_con,
	# 	sum(gl.debit) - sum(gl.credit) AS debit_balance
	# 	FROM `tabGL Entry` gl, `tabAccount` a WHERE
	# 	gl.account = a.name
	# 	AND {account_condition}
	# 	GROUP BY account_con
	# 	""".format(account_condition=account_condition))
	#
	#
	# def get_company_wise_data(filters):
	# 	company_list = [
	# 		'Arun Logistics', 'VK Logistics',
	# 		'Mosaic Enterprises Ltd.', 'Alpine Energy',
	# 		'Ludhiana Enterprises Ltd.'
	# 	]
	#
	# 	filters.company_list = company_list
	#
	# 	account_ordinal_range = frappe.db.sql("select lft, rgt from `tabAccount` where name like 'Accounts Receivable
	#  - "
	# 										  "%'")
	#
	# 	account_name = frappe.db.sql("SELECT name FROM `tabAccount` WHERE {}".format(
	# 		' or '.join([
	# 			'(lft > {} and rgt < {})'.format(lft, rgt) for lft, rgt in account_ordinal_range
	# 		])
	# 	))
	#
	# 	rs = frappe.db.sql("""
	# 	SELECT REPLACE(account, CONCAT(' -', SUBSTRING_INDEX(account, '-',-1)), '') AS account_con,
	# 	{field_list}
	# 	FROM `tabGL Entry`
	# 	WHERE {cond}
	# 	GROUP BY account_con;
	# 	""".format(
	# 		field_list=','.join(["""
	# 		(
	# 			sum(CASE WHEN company = '{company}' THEN debit ELSE 0 END) -
	# 			sum(CASE WHEN company = '{company}' THEN credit ELSE 0 END)
	# 		) as `{company}`""".format(company=company) for company in company_list]),
	# 		cond="account in ({})".format(','.join([""" "{}" """.format(x[0]) for x in account_name]))
	# 	), as_dict=True)
	#
	# 	return get_company_wise_columns(filters), rs
	#
	#
	# def get_company_wise_columns(filters):
	# 	return [
	# 		"Customer:Link/Customer:",
	# 		"Dr Balance:Currency:"
	# 	]