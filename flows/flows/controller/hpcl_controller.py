# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

import json

import frappe
import frappe.defaults
from flows.flows.hpcl_interface import HPCLCustomerPortal, LoginError, ServerBusy
from frappe.utils import today, add_days
import random
import time
import logging as logbook
from utils import reconcile_omc_txns_with_indents
from utils import skip_run, strip_vehicle, get_portal_user_password


def update_invoice_status_for_pending_indents(date=None, force_run=False):

	if not force_run:
		if skip_run():
			return

	customer_account_list = frappe.db.sql("""
		select distinct iitm.customer, iitm.credit_account
		from `tabIndent Item` iitm left join `tabIndent` ind on iitm.parent = ind.name
		where plant like 'hpcl%' and iitm.name not in (
			select indent_item
			from `tabIndent Invoice`
			where docstatus != 2
			and ifnull(indent_item, '')!=''
		) and ifnull(iitm.invoice_reference, '') = ''
	""", as_dict=True)

	date = date if date else today()

	fetch_and_record_hpcl_transactions(customer_account_list, date)

	reconcile_omc_txns_with_indents()


def fetch_and_record_hpcl_transactions(customer_account_list, for_date):
	logbook.basicConfig(
		filename="/tmp/logreport.out",
		level=logbook.DEBUG,
		format='%(asctime)s %(levelname)s  %(message)s'
	)

	for customer_account in customer_account_list:
		try:
			customer = customer_account.customer
			account_type = customer_account.credit_account
			user, passwd = get_portal_user_password(customer, 'HPCL', account_type)

			# We can not get transaction without password
			if not passwd:
				continue

			portal = HPCLCustomerPortal(user, passwd)

			portal.login()

			invoice_data = portal.get_invoice_data(for_date, for_date)
			deduplicate_and_save_invoice_txns(invoice_data['txns'], customer)

			account_data = portal.get_account_data(for_date, for_date, mode='dict')['txns']
			deduplicate_and_save_accounts_txns([
				txn for txn in account_data if abs(float(txn['Cr Amount'].replace(',', ''))) > 0
			], customer)

			sleep_time = random.choice([0.4, 0.2, 0.8, 1])
			print "Sleeping for {} sec".format(sleep_time)
			time.sleep(sleep_time)

		except Exception as e:
			print((customer, e))
			print e


def fetch_and_record_hpcl_balance(for_date=None):
	from flows.stdlogger import root

	for_date = for_date if for_date else add_days(today(), -1)
	run = 0
	max_run = 2

	exception_list = []
	# from frappe.utils import now_datetime

	customer_list = frappe.db.sql("""
	SELECT master_name as name, username, password
	FROM `tabAccount`
	WHERE name like "Hpcl a/c %"
	and ifnull(password) != ''
	""", as_dict=True)

	customer_defer_list = []

	while run < max_run:
		root.debug("Run Level {}".format(run))
		for customer in customer_list:
			portal = HPCLCustomerPortal(customer.username, customer.password)
			total_debit = total_credit = 0
			msg = error = ''

			try:
				portal.login()

				account_data = portal.get_account_data(for_date, for_date, mode='dict')
				invoices_map = portal.get_invoice_data(for_date, for_date)

				deduplicate_and_save_accounts_txns([
					txn for txn in account_data['txns'] if abs(float(txn['Cr Amount'].replace(',', ''))) > 0
				], customer)

				deduplicate_and_save_invoice_txns(invoices_map['txns'], customer)

				total_debit = invoices_map['total_price']
				total_credit = account_data['total_credit']

			except LoginError as e:
				error = 'LoginError'
				msg = e
			except ServerBusy as e:
				customer_defer_list.append(customer)
				error = 'TimeOut'
				if run < max_run - 1:
					continue
			except Exception as e:
				msg = e

			try:
				doc = frappe.get_doc({
				'customer': customer.name,
				'date': for_date,
				'balance': portal.get_current_balance_as_on_date(),
				'doctype': 'HPCL Customer Balance',
				'total_debit': total_debit,
				'total_credit': total_credit,
				'msg': msg,
				})

				if error:
					doc.error_type = error

				doc.ignore_permissions = True
				doc.save()
				frappe.db.commit()

			except Exception as e:
				print (customer.name, customer.username, e)

			sleep_time = random.choice([0.4, 0.2, 0.8, 1])
			print "Sleeping for {} sec".format(sleep_time)
			time.sleep(sleep_time)


		if customer_defer_list:
			customer_list = customer_defer_list
			customer_defer_list = []
			run += 1
		else:
			run = max_run


def item_map(item):
	if item == '0948064':
		return 'FC19'
	if item == '0948122':
		return 'FC35'
	if item == '0948042':
		return 'FC47.5'


def deduplicate_and_save_invoice_txns(txns, customer_obj_db):
	for txn in txns:
		invoice_no = txn['Invoice Reference'].split('/')[0].strip()

		if frappe.db.sql('SELECT name FROM `tabOMC Transactions` WHERE document_no="{}"'.format(invoice_no)):
			continue

		doc = frappe.get_doc({
		'customer': customer_obj_db.name if customer_obj_db else '',
		'date': '20' + '-'.join(reversed(txn['Invoice Date'].split('/'))),
		'doctype': 'OMC Transactions',
		'document_no': invoice_no,
		'debit': float(txn['Total Pricein INR'].replace(',', '')),
		'credit': 0,
		'item': item_map(txn['Item No.']),
		'quantity': txn['ShippedQuantity'],
		'vehicle_no': strip_vehicle(txn['Vehicle No.']),
		'plant': txn['Shipping Location'],
		'supplier': 'HPCL',
		'dump': json.dumps(txn),
		'account_number': customer_obj_db.username
		})

		doc.ignore_permissions = True
		doc.save()
		frappe.db.commit()


def deduplicate_and_save_accounts_txns(txns, customer_obj_db):
	for txn in txns:
		ref = txn['C.R / InvoiceReference'].split('/')[0].strip()
		if frappe.db.sql('SELECT name FROM `tabOMC Transactions` WHERE document_no="{}"'.format(ref)):
			continue

		doc = frappe.get_doc({
		'customer': customer_obj_db.name if customer_obj_db else '',
		'date': '20' + '-'.join(reversed(txn['C.R/InvoiceDate'].split('/'))),
		'doctype': 'OMC Transactions',
		'document_no': ref,
		'debit': abs(float(txn['Dr Amount'].replace(',', ''))),
		'credit': abs(float(txn['Cr Amount'].replace(',', ''))),
		'item': '',
		'quantity': '',
		'vehicle_no': txn['Bank Name'],
		'plant': txn['Supply Location'],
		'supplier': 'HPCL',
		'dump': json.dumps(txn),
		'account_number': customer_obj_db.username
		})

		doc.ignore_permissions = True
		doc.save()
		frappe.db.commit()




