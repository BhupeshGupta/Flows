# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from flows.utils import get_ac_debit_balances_as_on


def execute(filters=None):
	customer_list = [x[0] for x in frappe.db.sql("""SELECT name from `tabCustomer` order by name asc""")]
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