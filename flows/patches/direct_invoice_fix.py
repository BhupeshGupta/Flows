from __future__ import unicode_literals

import frappe


def execute():
	ess_invoices = frappe.db.sql("""
		select name, indent_item from `tabIndent Invoice` where customer like 'ESS ESS FORGING%' and docstatus = 1
		and transaction_date >= '2015-04-01';
		""")
	deeps_invoices = frappe.db.sql("""
		select name, indent_item from `tabIndent Invoice` where customer like 'DEEPS TOOLS%' and docstatus = 1
		and supplier like 'hpc%' and transaction_date >= '2015-04-01';
		""")
	for (invoice_id, indent_item) in deeps_invoices + ess_invoices:
		invoice_id = invoice_id
		from flows.stdlogger import root

		root.debug(invoice_id)

		doc = frappe.get_doc("Indent Invoice", invoice_id)
		doc.cancel()
		doc.delete()
		doc.payment_type = "Direct"
		doc.name = ""
		doc.__islocal = True
		doc.docstatus = 0
		doc.save()
		doc.docstatus = 1
		doc.save()

		frappe.db.sql("UPDATE `tabIndent Item` SET payment_type = 'Direct' WHERE name = '{}'".format(indent_item))