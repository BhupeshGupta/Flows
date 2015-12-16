from __future__ import unicode_literals

import json

import frappe
import frappe.defaults
from flows.flows.iocl_interface import IOCLPortal
from frappe.utils import today
from utils import reconcile_omc_txns_with_indents
from utils import skip_run


def get_iocl_customer_list():
	return


def fetch_and_record_iocl_transactions(customer_list, for_date=None, force_run=False):
	if not force_run:
		if skip_run():
			return

	def get_item(item_code):
		if item_code == 'M00002':
			return 'FC19'
		if item_code == 'M00065':
			return 'FC47.5'
		if item_code == 'M00069':
			return 'FC47.5L'
		return item_code

	def get_plant(plant_code):
		if plant_code == "1217":
			return "IOCL Jalandhar"
		if plant_code == "1274":
			return "IOCL NABHA"
		if plant_code == "1277":
			return "IOCL UNA"
		return plant_code

	for_date = for_date if for_date else today()

	for customer in customer_list:
		portal = IOCLPortal(customer.id, customer.passwd)
		portal.login()
		txns = portal.transactions_since_yesterday(for_date, for_date, mode=dict)

		for txn in txns['txns']:
			if frappe.db.sql(
					'SELECT name FROM `tabOMC Transactions` WHERE document_no="{}"'.format(int(txn['Doc. No']))
			):
				continue

			customer_obj = None
			if txn['Ship to Party'].strip():
				customer_obj = frappe.db.get_value(
					"Customer",
					{'iocl_sap_code': int(txn['Ship to Party'].strip())}, ["name"],
					as_dict=True
				)

			doc = frappe.get_doc({
				'customer': customer_obj.name if customer_obj else '',
				'date': for_date,
				'doctype': 'OMC Transactions',
				'document_no': int(txn['Doc. No']),
				'debit': txn['Bill Amt'] if txn['Db/Cr'] == 'D' else 0,
				'credit': txn['Bill Amt'] if txn['Db/Cr'] == 'C' else 0,
				'item': get_item(txn['Material']),
				'quantity': txn['Bill Qty'],
				'vehicle_no': txn['TTNO'],
				'plant': get_plant(txn['Plant']),
				'supplier': 'IOCL',
				'dump': json.dumps(txn),
				'account_number': customer.id
			})

			doc.ignore_permissions = True
			doc.save()
			frappe.db.commit()


def fetch_and_record_iocl_transactions(date=None):

	customer_account_map = {
		'605251': frappe._dict({'id': '605251', 'passwd': '605251'}),
		# '106474': frappe._dict({'id': '106474', 'passwd': '106474'})
	}

	iocl_account_list = [customer_account_map['605251']]

	for customer in frappe.db.sql("""
	select name, iocl_sap_code from `tabCustomer` where name in (
	select distinct iitm.customer
	from `tabIndent Item` iitm left join `tabIndent` ind on iitm.parent = ind.name
	where plant like 'iocl%' and iitm.name not in (
			select indent_item
			from `tabIndent Invoice`
			where docstatus != 2
			and ifnull(indent_item, '')!=''
		) and ifnull(iitm.invoice_reference, '') = ''
	);
	""", as_dict=True):
		if customer.iocl_sap_code in customer_account_map:
			iocl_account_list.append(customer_account_map[customer.iocl_sap_code])

	fetch_and_record_iocl_transactions(iocl_account_list, date)
	reconcile_omc_txns_with_indents()
