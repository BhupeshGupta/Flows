from __future__ import unicode_literals

from __future__ import unicode_literals

import frappe
import frappe.defaults


def execute():
	for i in frappe.db.sql("""
		select name
		from `tabIndent Invoice`
		where transaction_date >= '2015-04-01'
		and docstatus =1
		and supplier like 'Aggarwal%'
		and customer not like 'HARRY%'"""
	):
		oi = frappe.get_doc('Indent Invoice', i[0])
		nd = frappe.get_doc({
		'company': 'Aggarwal Enterprises', 'posting_date': oi.transaction_date,
		'customer': oi.customer, 'item': oi.item, 'quantity': oi.qty,
		'amount_per_item': oi.actual_amount / oi.qty, 'doctype': 'Subcontracted Invoice',
		'force_name': oi.invoice_number
		})

		oi.cancel()
		oi.delete()
		nd.save()
		nd.submit()