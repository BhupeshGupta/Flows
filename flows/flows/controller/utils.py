from __future__ import unicode_literals

import frappe
import frappe.defaults
from frappe.utils import today


def skip_run():
	import datetime
	t = datetime.datetime.now()
	# if time between 11 pm and 8 am skip runs = True
	return 23 <= t.hour <= 24 or 0 <= t.hour <= 8

def strip_vehicle(vehicle):
	try:
		return vehicle[[i.isalpha() for i in vehicle].index(True):]
	except:
		return vehicle


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


def get_portal_user_password(customer, omc, account_type=None, date=None):
	date = date if date else today()

	registration_record = frappe.db.sql("""
	select name, default_credit_account from `tabOMC Customer Registration`
	where customer = "{customer}"
	and omc = "{omc}"
	and with_effect_from <= "{date}"
	and docstatus = 1
	order by with_effect_from desc limit 1
	""".format(customer=customer, omc=omc, date=date), as_dict=True)

	if not registration_record:
		frappe.throw("OMC Registration missing for customer")
	registration_record = registration_record[0]

	accounts = frappe.db.sql(
		"""
		select * from `tabOMC Customer Registration Credit Account`
		where parent = "{}"
		""".format(registration_record.name), as_dict=True
	)

	account_type = account_type if account_type else registration_record.default_credit_account

	valid_account = [account.account for account in accounts if account.type == account_type]

	if len(valid_account) > 1:
		frappe.throw("Multiple accounts with same account type are linked")


	rs = frappe.db.get_values(
		"Account",
		{'name': valid_account[0]},
		['integration_type', 'username', 'password'],
		as_dict=True
	)[0]

	print(rs)

	return (rs.username, rs.password)
