import json

import frappe


@frappe.whitelist(allow_guest=True)
def get_meta(doc):
	doc = json.loads(doc)

	query = {
	'doctype': 'Sales Invoice' if doc['type'] in ('Consignment Note',) else '',
	'name': doc['id']
	}

	return_doc = {}
	if doc['type'] == 'Consignment Note':
		return_doc.update(
			frappe.db.sql("""
			select invoice_number as `Bill Number`, transaction_date as `Bill Date`, item as `Bill Item`,
			qty as `Bill Quantity`, actual_amount as `Bill Amount`, supplier as `Bill Supplier`,
			vehicle as `Vehicle`, customer as `Customer`
			from `tabIndent Invoice`
			where (
				transportation_invoice = '{name}'
				or transportation_invoice like '{name}-%'
			)
			and docstatus = 1
			""".format(**query), as_dict=True)[0]
		)

		return_doc.update(
			frappe.db.sql("""
			select name as `Consignment Name`, posting_date as `Consignment Date`,
			grand_total_export as `Consignment Amount`, company as `Consignment Company`,
			amended_from as `$amended_from`
			from `tab{doctype}`
			where (
			name = '{name}'
			or name like '{name}-%'
			) and docstatus != 2
			""".format(**query), as_dict=True)[0]
		)

	return json.dumps(return_doc)