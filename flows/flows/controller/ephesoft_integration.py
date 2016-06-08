import json
from frappe.utils.file_manager import upload
import frappe
import requests
from frappe.utils import cint
from flows.stdlogger import root



if not frappe.conf.document_queue_server:
	raise Exception('document_queue_server not found in config')

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


def create_docs_in_review_server(doc, method=None, *args, **kwargs):
	docs = []

	if doc.transaction_date < '2016-06-01':
		return

	sales_invoice_amended_from = frappe.db.get_value("Sales Invoice", doc.transportation_invoice, 'amended_from')

	# Normalizations
	doc.transportation_invoice_number = '-'.join(doc.transportation_invoice.split('-')[:-1]) if (sales_invoice_amended_from and sales_invoice_amended_from.strip()) else doc.transportation_invoice

	# Material Bill / Indent Invoice
	docs.append({'cno': doc.transportation_invoice_number, 'doctype': doc.doctype, 'date': doc.transaction_date})

	# Consignment note
	docs.append({'cno': doc.transportation_invoice_number, 'doctype': "Consignment Note", 'date': doc.posting_date})

	if (doc.sales_tax == 'CST'):
		docs.append({'cno': doc.transportation_invoice_number, 'doctype': "VAT Form XII", 'date': doc.transaction_date})

	if ('hpcl' in doc.supplier.lower() and cint(doc.cenvat) == 1):
		docs.append({'cno': doc.transportation_invoice_number, 'doctype': "Excise Invoice", 'date': doc.transaction_date})

	for sails_doc in docs:
		data = requests.post('{}/currentstat/'.format(frappe.conf.document_queue_server), sails_doc)
		root.debug(sails_doc)

		if (data.status_code not in [200, 201]):
			content = json.loads(data.content)

			root.debug(content)
            #
			if 'invalidAttributes' in content and \
				len(content['invalidAttributes'].keys()) == 1 and \
				 'unique_notes' in content['invalidAttributes']:
				continue

			raise Exception(
				'Document Queue Server returned {} \n {}'.\
					format(data.status_code, data.content)
			)


@frappe.whitelist()
def get_user():
	return json.dumps({'user': frappe.session.user})


# @frappe.whitelist()
# def attach_doc():
# 	frappe.form_dict.docname = frappe.db.sql("""
# 		select name
# 		from `tab{doctype}`
# 		where (
# 			name = '{docname}'
# 			or name like '{docname}-%'
# 		)
# 		and docstatus = 1
# 	""".format(**frappe.form_dict), as_dict=True)[0].name
#
# 	upload()