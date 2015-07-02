from __future__ import unicode_literals

from __future__ import unicode_literals

import frappe
import frappe.defaults


def execute():
	for i in frappe.db.sql("""
		SELECT name, posting_date
		FROM `tabGoods Receipt`
		WHERE docstatus = 1;
		""", as_dict=True):

		frappe.db.sql("""
		update `tabGoods Receipt` set transaction_date= '{}'
		WHERE name = '{}';
		""".format(i.posting_date, i.name))