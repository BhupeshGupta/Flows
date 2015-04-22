from __future__ import unicode_literals

import frappe

def execute():
	for cp_id in frappe.db.sql("""
		SELECT name
		FROM `tabCross Purchase`
		WHERE docstatus != 2;
		"""):
		cp = frappe.get_doc("Cross Purchase", cp_id[0])
		cp.append("customer_list", {"customer": cp.customer})
		cp.ignore_validate = True
		cp.ignore_validate_update_after_submit = True
		cp.ignore_permissions = True
		cp.save()