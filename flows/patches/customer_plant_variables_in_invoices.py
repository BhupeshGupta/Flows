from __future__ import unicode_literals

import frappe

def execute():
	for i in frappe.db.sql("""
	select transaction_date, name, customer, supplier
	from `tabIndent Invoice`
	where posting_date >= '2015-07-01'
	and docstatus = 1
	and customer_plant_variables is Null
	and customer not like 'VK%'"""):



