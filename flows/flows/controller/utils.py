from __future__ import unicode_literals

import frappe
import frappe.defaults


def skip_run():
	import datetime
	t = datetime.datetime.now()
	# if time between 11 pm and 8 am skip runs = True
	return 23 <= t.hour <= 24 or 0 <= t.hour <= 8


def reconcile_omc_txns_with_indents():
	for txn in frappe.db.sql("""
	select supplier, document_no, customer, item, quantity, debit, vehicle_no
	from `tabOMC Transactions`
	where debit > 0 and document_no not in (
		select invoice_number
		from `tabIndent Invoice`
		where docstatus != 2
	) and document_no not in (
		select invoice_reference
		from `tabIndent Item`
		where ifnull(invoice_reference, '') != ''
	)
	""", as_dict=True):

		indent_list = frappe.db.sql("""
		select iitm.name
		from `tabIndent Item` iitm left join `tabIndent` ind on iitm.parent = ind.name
		where ind.plant like '{supplier}%' and iitm.name not in (
			select indent_item
			from `tabIndent Invoice`
			where docstatus != 2
			and ifnull(indent_item, '')!=''
		) and ifnull(iitm.invoice_reference, '') = ''
		and iitm.customer="{customer}" and replace(iitm.item, 'L', '')="{item}"
		and iitm.qty="{quantity}" and ind.vehicle = "{vehicle_no}";
		""".format(**txn), as_dict=True)

		# Match Found
		if len(indent_list) > 0:
			frappe.db.sql("update `tabIndent Item` set invoice_reference='{ref}' where name = '{name}'".format(
				ref=txn.document_no, name=indent_list[0].name
			))
			frappe.db.commit()
