from __future__ import unicode_literals

import frappe

def execute():
	for invoice_id in frappe.db.sql("""
		select name from `tabIndent Invoice` where name like 'AG%' and docstatus = 1;
		"""):
		invoice_id = invoice_id[0]
		from flows.stdlogger import root
		root.debug(invoice_id)

		doc = frappe.get_doc("Indent Invoice", invoice_id)
		doc.cancel()
		doc.delete()
		doc.payment_type = "Direct"
		doc.name = ""
		doc.docstatus = 1
		doc.save()



