from __future__ import unicode_literals

import frappe

def execute():
	for (invoice_id, transportation_invoice_id) in frappe.db.sql("""
		SELECT name, transportation_invoice
		FROM `tabIndent Invoice`
		WHERE docstatus = 1;
		"""):

		if transportation_invoice_id and transportation_invoice_id != '':
			doc = frappe.get_doc("Sales Invoice", transportation_invoice_id)
			frappe.db.sql("""
			UPDATE `tabIndent Invoice` SET transportation_invoice_rate='{}', transportation_invoice_amount='{}'
			WHERE name = '{}'""".format(doc.entries[0].rate, doc.grand_total_export, invoice_id)
			)


