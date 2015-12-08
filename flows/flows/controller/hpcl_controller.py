# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

import json

import frappe
import frappe.defaults
from flows.flows.hpcl_interface import HPCLCustomerPortal
from frappe.utils import today


def skip_run():
	import datetime
	t = datetime.datetime.now()
	# if time between 10 pm and 8 am skip runs = True
	return 22 <= t.hour <= 8


def update_invoice_status_for_pending_indents():

	if skip_run():
		return

	customer_list = [c[0] for c in frappe.db.sql("""
	select distinct iitm.customer
	from `tabIndent Item` iitm left join `tabIndent` ind on iitm.parent = ind.name
	where plant like 'hpcl%' and iitm.name not in (
		select indent_item
		from `tabIndent Invoice`
		where docstatus != 2
		and ifnull(indent_item, '')!=''
	) and ifnull(iitm.invoice_reference, '') = '';
	""")]

	date = today()

	fetch_and_record_hpcl_transactions(customer_list, date)


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
		if len(indent_list) == 1:
			frappe.db.sql("update `tabIndent Item` set invoice_reference='{ref}' where name = '{name}'".format(
				ref=txn.document_no, name=indent_list[0].name
			))
			frappe.db.commit()



def fetch_and_record_hpcl_transactions(customer_list, for_date):
	def get_item(item):
		if item == '0948064':
			return 'FC19'
		if item == '0948122':
			return 'FC35'
		if item == '0948042':
			return 'FC47.5'

	customer_list_db = frappe.db.sql("""
	SELECT name, hpcl_erp_number, hpcl_payer_password
	FROM `tabCustomer`
	WHERE name IN ({})
	""".format('"' + '", "'.join(customer_list) + '"'), as_dict=True)

	for customer in customer_list_db:
		portal = HPCLCustomerPortal(customer.hpcl_erp_number, customer.hpcl_payer_password)

		try:
			portal.login()
			invoice_data = portal.get_invoice_data(for_date, for_date)

			for txn in invoice_data['txns']:
				invoice_no = txn['Invoice Reference'].split('/')[0].strip()
				if frappe.db.sql('SELECT name FROM `tabOMC Transactions` WHERE document_no="{}"'.format(invoice_no)):
					continue

				doc = frappe.get_doc({
				'customer': customer.name if customer else '',
				'date': for_date,
				'doctype': 'OMC Transactions',
				'document_no': invoice_no,
				'debit': float(txn['Total Pricein INR'].replace(',', '')),
				'credit': 0,
				'item': get_item(txn['Item No.']),
				'quantity': txn['ShippedQuantity'],
				'vehicle_no': txn['Vehicle No.'],
				'plant': txn['Shipping Location'],
				'supplier': 'HPCL',
				'dump': json.dumps(txn),
				'account_number': customer.hpcl_erp_number
				})

				doc.ignore_permissions = True
				doc.save()
				frappe.db.commit()
		except Exception:
			pass

		# account_data = portal.get_account_data(for_date, for_date, mode='dict')
		#
		# for txn in account_data:
		# 	if abs(float(txn['Cr Amount'].replace(',', ''))) > 0:
		# 		ref = txn['C.R / InvoiceReference'].split('/')[0].strip()
		# 		if frappe.db.sql('SELECT name FROM `tabOMC Transactions` WHERE document_no="{}"'.format(ref)):
		# 			continue
		#
		# 		doc = frappe.get_doc({
		# 		'customer': customer.name if customer else '',
		# 		'date': for_date,
		# 		'doctype': 'OMC Transactions',
		# 		'document_no': ref,
		# 		'debit': 0,
		# 		'credit': abs(float(txn['Cr Amount'].replace(',', ''))),
		# 		'item': '',
		# 		'quantity': '',
		# 		'vehicle_no': txn['Bank Name'],
		# 		'plant': txn['Supply Location'],
		# 		'supplier': 'HPCL',
		# 		'dump': json.dumps(txn),
		# 		'account_number': customer.hpcl_erp_number
		# 		})
		#
		# 		doc.ignore_permissions = True
		# 		doc.save()
		# 		frappe.db.commit()