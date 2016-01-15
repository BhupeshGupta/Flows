# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe.utils import add_days, today
import frappe


def execute(filters=None):
	cols = get_columns(filters)
	filters.date = today()

	debit_balances_list = get_account_balances(filters)
	debit_balance_map = {x.account: x.debit_balance for x in debit_balances_list if abs(x.debit_balance) > 100}

	rows = []
	filtered_accounts, accounts_by_name, parent_children_map = get_accounts(filters)

	for account in filtered_accounts:
		if account.group_or_ledger == 'Group':
			leaf_accounts = list(set(get_leaf_nodes(account.name, parent_children_map)))
			group_acc_sum = sum([debit_balance_map.get(x, 0) for x in leaf_accounts])
			account.update({
			'debit_bal': group_acc_sum
			})
			account.update(get_aged_data_for_account(leaf_accounts, group_acc_sum, filters))
			rows.append(account)
		elif account.name in debit_balance_map:
			account.update({
			'debit_bal': debit_balance_map[account.name]
			})
			account.update(get_aged_data_for_account([account.name], debit_balance_map[account.name], filters))
			rows.append(account)

	# data = []
	# lft, rgt = frappe.db.sql("""SELECT lft, rgt FROM
	# `tabAccount` WHERE name = {name}""".format(name=filters.account))[0]
	#
	# frappe.db.sql("""
	# SELECT name FROM `tabAccount`
	# WHERE lft >= {lft} AND rgt <= {rgt}
	# """.format(lft=lft, rgt=rgt))
	#
	# for account, balance in debit_balance_map.items():
	# row = [account, balance]
	# row.extend(get_aged_data_for_account(account, balance, filters))
	# data.append(row)

	return cols, rows

def get_leaf_nodes(account, parent_child_map):
	rs = []
	if account in parent_child_map:
		for acc in parent_child_map[account]:
			rs.extend(get_leaf_nodes(acc.name, parent_child_map))
		return rs
	return [account]

def get_accounts(filters):
	def strip_account(account):
		return ' - '.join(account.split(' - ')[:-1])

	def indent_accounts(accounts):
		parent_children_map = {}
		accounts_by_name = {}
		filtered_accounts = []
		for a in accounts:
			# a.name = ' - '.join(a.name.split(' - ')[:-1])
			# a.parent_account = ' - '.join(a.parent_account.split(' - ')[:-1]) if a.parent_account else
			# a.parent_account

			accounts_by_name[a.name] = a
			parent_children_map.setdefault(a.parent_account or None, []).append(a)

		def add_to_list(parent, level):
			for child in (parent_children_map.get(parent) or []):
				child.indent = level
				filtered_accounts.append(child)
				add_to_list(child.name, level + 1)

		add_to_list(None, 0)

		return filtered_accounts, accounts_by_name, parent_children_map


	condition = ' or '.join(['(lft >= "{}" and rgt <= "{}")'.format(x[0], x[1]) for x in frappe.db.sql("""
		select lft, rgt from `tabAccount`
		where name like '{account_name} - %'
		""".format(account_name=' - '.join(filters.account.split(' - ')[:-1])))])

	all_account = frappe.db.sql("""
	SELECT DISTINCT REPLACE(name, CONCAT(' -', SUBSTRING_INDEX(name, '-',-1)), '') AS name
	FROM `tabAccount` WHERE {}
	""".format(condition), as_dict=True)

	account_extension = filters.account.split(' - ')[-1]

	parent_map = {x[0]: {'parent_account': x[1], 'group_or_ledger': x[2]} for x in frappe.db.sql("""
	SELECT REPLACE(name, CONCAT(' -', SUBSTRING_INDEX(name, '-',-1)), '') AS name,
	REPLACE(parent_account, CONCAT(' -', SUBSTRING_INDEX(parent_account, '-',-1)), '') AS parent_account,
	group_or_ledger
	FROM `tabAccount` WHERE name IN ({})
	""".format(','.join(['"{} - {}"'.format(x.name, account_extension) for x in all_account])))}

	for a in all_account:
		a.update(parent_map.get(a.name, {
		'parent_account': strip_account(filters.account),
		'group_or_ledger': 'Ledger'
		}))

	all_account.append(frappe._dict({
	'name': strip_account(filters.account),
	'parent_account': None,
	'group_or_ledger': 'Group'
	}))

	filtered_accounts, accounts_by_name, parent_map = indent_accounts(all_account)

	return filtered_accounts, accounts_by_name, parent_map


def get_account_balances(filters):
	rs = frappe.db.sql("""
	SELECT REPLACE(account, CONCAT(' -', SUBSTRING_INDEX(account, '-',-1)), '') AS account_con,
	sum(ifnull(debit, 0)) - sum(ifnull(credit, 0)) AS debit_balance
	FROM `tabGL Entry` gle
	WHERE posting_date <= "{date}"
	{account_filter}
	GROUP BY account_con;
	""".format(date=filters.date, account_filter=''), as_dict=True)


	final_list = []

	account_filter = ''
	condition = ' or '.join(['(lft >= "{}" and rgt <= "{}")'.format(x[0], x[1]) for x in frappe.db.sql("""
	select lft, rgt from `tabAccount`
	where name like '{account_name} - %'
	""".format(account_name=' - '.join(filters.account.split(' - ')[:-1])))])

	valid_accounts = set([' - '.join(x[0].split(' - ')[:-1]) for x in frappe.db.sql("""
	SELECT name FROM `tabAccount` WHERE {}
	""".format(condition))])

	for r in rs:
		r.account = r.account_con.strip()
		if r.account in valid_accounts:
			final_list.append(r)


	return final_list


def get_aged_data_for_account(account, balance, filters):
	date = filters.date

	if balance > 0:
		dr_cr = 'debit'
		running_balance = balance
	else:
		dr_cr = 'credit'
		running_balance = -1 * balance

	interval_balance_map = {}

	for (start_day, end_day) in filters.intervals:
		interval_balance = frappe.db.sql("""
		select sum({dr_cr})
		from `tabGL Entry`
		where {dr_cr} > 0
		and ({account_cond})
		and posting_date between "{end_date}" and "{start_date}"
		""".format(
			start_date=add_days(date, -1 * start_day),
			end_date=add_days(date, -1 * end_day) if end_day else "1950-01-01",
			account_cond=' or '.join(['account like "{} - %"'.format(a) for a in account]),
			dr_cr=dr_cr
		))
		interval_balance = interval_balance[0][0] if interval_balance[0][0] else 0
		running_balance -= interval_balance

		if running_balance < 0:
			interval_balance += running_balance

		interval_balance_map['{}-{}'.format(start_day, end_day)] = interval_balance if balance > 0 else -1 * interval_balance

		if running_balance < 0:
			break

	return interval_balance_map


def get_columns(filters):
	cols = [
		{
		"fieldname": "name",
		"label": "Customer",
		"fieldtype": "Data",
		"width": 200
		},
		{
		"fieldname": "debit_bal",
		"label": "Debit Bal",
		"fieldtype": "Currency",
		"width": 100
		}
	]

	intervals = []
	for i in xrange(0, filters.no_of_intervals - 1):
		intervals.append((i * filters.interval, (i + 1) * filters.interval))
	intervals.append(((filters.no_of_intervals - 1) * filters.interval, None))

	filters.intervals = intervals

	for x in intervals:
		cols.append({
		"fieldname": '{}-{}'.format(x[0], x[1]),
		"label": '{}-{}'.format(x[0], x[1]) if x[1] else '{}-Above'.format(x[0]),
		"fieldtype": "Currency",
		"width": 100
		})

	return cols