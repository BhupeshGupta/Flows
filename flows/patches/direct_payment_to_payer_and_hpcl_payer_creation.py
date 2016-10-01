from __future__ import unicode_literals

import frappe
from erpnext.accounts.general_ledger import make_gl_entries


def execute():
	for invoice_id in frappe.db.sql("""
		select name
		from `tabIndent Invoice`
		where docstatus=1 and
		transaction_date >= '2015-04-01' and
		(
			supplier like 'hpcl%'
			or
			(
				payment_type = "Direct" and
				(
					supplier like "ioc%"
				)
			)
		)
		"""):
		invoice_id = invoice_id[0]
		doc = frappe.get_doc("Indent Invoice", invoice_id)
		gl_entries = doc.get_gl_entries()
		make_gl_entries(gl_entries, cancel=True, update_outstanding='Yes', merge_entries=False)
		make_gl_entries(gl_entries, cancel=False, update_outstanding='Yes', merge_entries=False)