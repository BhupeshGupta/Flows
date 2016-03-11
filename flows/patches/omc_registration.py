from __future__ import unicode_literals

from __future__ import unicode_literals

import frappe
import frappe.defaults

from erpnext.accounts.party import get_party_account
from flows.flows import payer
from frappe.exceptions import DoesNotExistError

def execute():
	default_company = 'Arun Logistics'

	exceptions = []

	default_omc_registration = {
		'doctype': 'OMC Customer Registration',
		'with_effect_from': '2015-04-01',
		'sales_invoice_company': default_company,
		'incentive_on_investment': 0,
	}

	for customer in frappe.db.sql("""select * from `tabCustomer`""", as_dict=True):
		omc_reg = default_omc_registration.copy()
		omc_reg.update({'customer': customer.name})
		default_debit_account = get_party_account(default_company, customer.name, "Customer")

		if customer.iocl_sap_code:
			try:
				iocl_omc_reg = omc_reg.copy()

				payment_mode = get_payment_mode(customer.name, 'IOCL')
				isDirect = payment_mode == 'Direct'
				company = 'Iocl' if isDirect else 'Mosaic Enterprises Ltd.'

				iocl_omc_reg.update({
				'field_officer': customer.iocl_field_officer if customer.iocl_field_officer else 'Not Known',
				'customer_code': customer.iocl_sap_code,
				'omc': 'IOCL',
				'sales_invoice_account': default_debit_account,

				'default_credit_account': 'Customer Code' if isDirect else 'Payer Code',
				'credit_accounts': [
					{
						'type': 'Customer Code' if isDirect else 'Payer Code',
						'credit_account_company': company,
						'credit_account': payer.get_payer_account(company, 'IOCL una', customer.name, payment_mode),
						'debit_account_company': 'Iocl' if isDirect else default_company,
						'debit_account': 'Sales - ioc' if isDirect
						else get_party_account(default_company, customer.name, "Customer"),
						'payment_type': payment_mode
					}
				],
				'ba': 'Mosaic Enterprises Ltd.',
				'docstatus': 1
				})

				print (iocl_omc_reg)

				frappe.get_doc(iocl_omc_reg).save()

				if isDirect:
					try:
						acc = frappe.get_doc("Account", iocl_omc_reg['credit_accounts'][0]['credit_account'])
						acc.integration_type = 'IOCL Integration'
						acc.username = customer.iocl_sap_code
						acc.save()
					except DoesNotExistError:
						exceptions.append("IOCL Account does not exist for customer: {}, {}".format(
								customer.name, customer.iocl_sap_code
						))
					except AttributeError:
						print(iocl_omc_reg)
						raise
			except Exception as e:
				if 'Customer plant variable' in e.message:
					exceptions.append(e.message)
				else:
					raise

		if customer.hpcl_erp_number:
			try:
				hpcl_omc_reg = omc_reg.copy()
				payment_mode = get_payment_mode(customer.name, 'HPCL')
				isDirect = payment_mode == 'Direct'

				company = 'Hpcl' if isDirect else 'Alpine Energy'
				hpcl_omc_reg.update({
				'field_officer': customer.hpcl_field_officer if customer.hpcl_field_officer else 'Not Known',
				'customer_code': customer.hpcl_erp_number,
				'omc': 'HPCL',
				'sales_invoice_account': default_debit_account,

				'default_credit_account': 'Customer Code',
				'credit_accounts': [
					{
						'type': 'Customer Code',
						'credit_account_company': company,
						'credit_account': payer.get_payer_account(company, 'HPCL B', customer.name, 'Direct' if isDirect else 'Indirect'),
						'debit_account_company': 'Hpcl' if isDirect else default_company,
						'debit_account': 'Sales - hpc' if isDirect
						else get_party_account(default_company, customer.name, "Customer"),
						'payment_type': payment_mode
					}
				],
				'ba': 'Alpine Energy',
				'docstatus': 1
				})

				frappe.get_doc(hpcl_omc_reg).save()

				try:
					acc = frappe.get_doc("Account", hpcl_omc_reg['credit_accounts'][0]['credit_account'])
					acc.integration_type = 'HPCL Integration'
					acc.username = customer.hpcl_erp_number
					acc.password = customer.hpcl_payer_password.strip() if customer.hpcl_payer_password else ''
					acc.save()
				except DoesNotExistError:
					exceptions.append("HPCL Account does not exist for customer: {}, {}, {}".format(
							customer.name, customer.hpcl_erp_number, customer.hpcl_payer_password
					))
					frappe.db.sql(
						"""
						update `tabCustomer` set customer_details = "{}" where name = "{}"
						""".format('HPCL Password: {}'.format(customer.hpcl_payer_password), customer.name)
					)
				except AttributeError:
					print(hpcl_omc_reg)
					raise

			except Exception as e:
				if 'Customer plant variable' in e.message:
					exceptions.append(e.message)
				else:
					raise

		if customer.bpcl_sap_code:
			try:
				bpcl_omc_reg = omc_reg.copy()

				payment_mode = get_payment_mode(customer.name, 'BPCL')
				isDirect = payment_mode == 'Direct'
				company = 'Bpcl' if isDirect else 'Ludhiana Enterprises Ltd.'

				bpcl_omc_reg.update({
				'field_officer': customer.bpcl_field_officer if customer.bpcl_field_officer else 'Not Known',
				'customer_code': customer.bpcl_sap_code,
				'omc': 'BPCL',
				'sales_invoice_account': default_debit_account,
				'default_credit_account': 'Customer Code' if isDirect else 'Payer Code',
				'credit_accounts': [
					{
						'type': 'Customer Code' if isDirect else 'Payer Code',
						'credit_account_company': company,
						'credit_account': payer.get_payer_account(company, 'BPCL Loni', customer.name, payment_mode),
						'debit_account_company': 'Bpcl' if isDirect else default_company,
						'debit_account': 'Sales - bpc' if isDirect
						else get_party_account(default_company, customer.name, "Customer"),
						'payment_type': payment_mode
					}
				],
				'ba': 'Ludhiana Enterprises Ltd.',
				'docstatus': 1
				})

				frappe.get_doc(bpcl_omc_reg).save()

				if isDirect:
					try:
						acc = frappe.get_doc("Account", bpcl_omc_reg['credit_accounts'][0]['credit_account'])
						acc.username = customer.bpcl_sap_code
						acc.save()
					except DoesNotExistError:
						exceptions.append("BPCL Account does not exist for customer: {}, {}".format(
								customer.name, customer.bpcl_sap_code
						))
					except AttributeError:
						print(bpcl_omc_reg)
						raise
			except Exception as e:
				if 'Customer plant variable' in e.message:
					exceptions.append(e.message)
				else:
					raise

	import json
	print json.dumps(exceptions)


def get_payment_mode(customer, omc):
	rs = frappe.db.sql("""
	select payment_mode from `tabCustomer Plant Variables`
	where customer = "{}" and plant like '{}%'
	and docstatus = 1 order by with_effect_from desc limit 1
	""".format(customer, omc))

	if not rs:
		raise Exception("Customer plant variable not found for {}, {}".format(customer, omc))
	return rs[0][0]



