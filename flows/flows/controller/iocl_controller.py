from __future__ import unicode_literals

import json

import frappe
import frappe.defaults
from flows.flows.iocl_interface import IOCLPortal
from frappe.utils import today
from utils import reconcile_omc_txns_with_indents
from utils import skip_run, strip_vehicle
from utils import get_portal_user_password


IOCL_PLANT_CODE_MAP = {
	'1217': 'IOCL Jalandhar',
	'1274': 'IOCL NABHA',
	'1277': 'IOCL una',
	'1171': 'IOCL TIKRI',
	'3148': 'IOCL Dahej'
}


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
			return 'FC47.5'
		return item_code

	def get_plant(plant_code):
		return IOCL_PLANT_CODE_MAP[plant_code] if plant_code in IOCL_PLANT_CODE_MAP else plant_code

	for customer in customer_list:
		portal = IOCLPortal(customer.id, customer.passwd)
		portal.login()
		txns = portal.transactions_since_yesterday(for_date, for_date, mode=dict)

		for txn in txns['txns']:
			if frappe.db.sql(
					'SELECT name FROM `tabOMC Transactions` WHERE document_no="{}"'.format(int(txn['Doc. No']))
			):
				continue

			registration = None
			if txn['Ship to Party'].strip():
				registration = frappe.db.get_value(
					"OMC Customer Registration",
					{'customer_code': int(txn['Ship to Party'].strip())}, ["customer"],
					as_dict=True
				)

			doc = frappe.get_doc({
				'customer': registration.customer if registration else '',
				'date': '-'.join(reversed(txn['Tran. Date'].split('.'))),
				'doctype': 'OMC Transactions',
				'document_no': int(txn['Doc. No']),
				'debit': txn['Bill Amt'] if txn['Db/Cr'] == 'D' else 0,
				'credit': txn['Bill Amt'] if txn['Db/Cr'] == 'C' else 0,
				'item': get_item(txn['Material']),
				'quantity': txn['Bill Qty'],
				'vehicle_no': strip_vehicle(txn['TTNO']),
				'plant': get_plant(txn['Plant']),
				'supplier': 'IOCL',
				'dump': json.dumps(txn),
				'account_number': customer.id
			})

			doc.ignore_permissions = True
			doc.save()
			frappe.db.commit()


def fetch_and_record_iocl_transactions_controller(date=None):
	iocl_account_map = {}

	for customer in frappe.db.sql("""
	select distinct iitm.customer, iitm.credit_account
	from `tabIndent Item` iitm left join `tabIndent` ind on iitm.parent = ind.name
	where plant like 'iocl%' and iitm.name not in (
			select indent_item
			from `tabIndent Invoice`
			where docstatus != 2
			and ifnull(indent_item, '')!=''
		) and ifnull(iitm.invoice_reference, '') = ''
	and iitm.docstatus != 2
	""", as_dict=True):

		user, passwd = get_portal_user_password(customer.customer, 'IOCL', customer.credit_account)
		if passwd and user not in iocl_account_map:
			iocl_account_map[user] = frappe._dict({'id': user, 'passwd': passwd})

	fetch_and_record_iocl_transactions(iocl_account_map.values())
	reconcile_omc_txns_with_indents()

	print(iocl_account_map.values())
