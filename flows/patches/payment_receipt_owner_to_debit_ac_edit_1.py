from __future__ import unicode_literals

from __future__ import unicode_literals

import frappe
import frappe.defaults

from flows import utils


def execute():
	for pr in frappe.db.sql("SELECT * FROM `tabPayment Receipt` WHERE docstatus = 1", as_dict=True):
		frappe.db.set_value(
			"Payment Receipt",
			pr.name,
			"debit_account",
			utils.get_imprest_or_get_or_create_customer_like_account(pr.company, pr.owner)
		)

	frappe.db.sql("update `tabGoods Receipt Book` set gr_enabled = 1 where warehouse is not Null")