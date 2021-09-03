import datetime

import frappe
from erpnext.accounts.party import get_party_account
from frappe.utils import cint


def get_or_create_vehicle_stock_account(vehicle_name, stock_owner_company_name):
	return get_or_create_warehouse(vehicle_name, stock_owner_company_name)


def get_or_create_customer_stock_account(customer_name, company_name_to_find_account_under):
	return get_or_create_warehouse(customer_name, company_name_to_find_account_under)


def get_suppliers_warehouse_account(supplier, company):
	if ',' in supplier:
		supplier = supplier.split(',')[0].strip()
	return get_or_create_warehouse(supplier, company)


def get_supplier_account(company, supplier):
	return get_party_account(company, supplier, "Supplier")


# ***************

def get_or_create_warehouse(warehouse_name, company):
	try:
		company_abbr = frappe.db.get_value(
			"Company", company, "abbr"
		)

		warehouse_account = frappe.get_doc("Warehouse", '{} - {}'.format(warehouse_name, company_abbr))
		return warehouse_account

	except frappe.DoesNotExistError as e:
		warehouse_account = frappe.get_doc(
			{
			"doctype": "Warehouse",
			"company": company,
			"warehouse_name": warehouse_name
			})
		warehouse_account.insert(ignore_permissions=True)
		return warehouse_account


# ******

from frappe import _


def get_imprest_or_get_or_create_customer_like_account(company, account_or_user):
	acc_head = frappe.db.get_value("Account", {
	"responsible_user": account_or_user,
	"company": company,
	"account_type": "Imprest"
	})
	if acc_head:
		return acc_head

	return get_or_or_create_customer_like_gl_account(company, account_or_user)


def get_or_or_create_customer_like_gl_account(company, account):
	acc_head = frappe.db.get_value("Account", {
	"master_name": account,
	"company": company
	})

	if acc_head:
		return acc_head

	company_details = frappe.db.get_value(
		"Company", company, ["abbr", "receivables_group"], as_dict=True
	)

	# create
	account = frappe.get_doc({
	"doctype": "Account",
	'account_name': account,
	'parent_account': company_details.receivables_group,
	'group_or_ledger': 'Ledger',
	'company': company,
	'master_name': account,
	"freeze_account": "No",
	"report_type": "Balance Sheet"
	}).insert(ignore_permissions=True)

	frappe.msgprint(_("Account Created: {0}").format(account))

	acc_head = account.name

	return acc_head


def get_party_account(company, party, party_type):
	acc_head = frappe.db.get_value("Account", {"master_name": party,
											   "master_type": party_type, "company": company})
	if not acc_head:
		print ("missing act head")
		from stdlogger import root

		root.debug({"master_name": party,
					"master_type": party_type,
					"company": company})
		from erpnext.accounts.party import create_party_account

		acc_head = create_party_account(party, party_type, company)
	return acc_head


def get_stock_owner_via_sales_person_tree(person):
	"""
	checks sales persons hierarchy and return group person if found. if person is not a sales person
	 returns none
	:param person:
	:return:
	"""
	if not frappe.db.exists("Sales Person", person):
		return None

	from frappe.utils import nestedset

	sales_person = frappe.get_doc("Sales Person", person)

	return sales_person.name if sales_person.is_group == 'Yes' else \
		nestedset.get_ancestors_of("Sales Person", person)[0]


def get_insight_depth_condition(depth=1, old_styp_format_escaped=False):
	depth_2_doctypes = ['Cross Sale Purchase', 'Cross Sale', 'Cross Purchase', 'Payment Receipt']

	basic_condition_for_depth_2 = \
		"""(
				voucher_type in ({}) or
				(voucher_type = "Journal Voucher" and voucher_no like "KJV-{}%")
			)
		""".format(
			','.join(['"{}"'.format(x) for x in depth_2_doctypes]),
			"%" if old_styp_format_escaped else ""
		)

	depth = cint(depth)
	if depth == 1:
		return "(not {})".format(basic_condition_for_depth_2)
	elif depth == 2:
		return basic_condition_for_depth_2
	return None


def get_next_date(cur_date, days=1):
	return (datetime.datetime.strptime(cur_date, "%Y-%m-%d") + datetime.timedelta(days=days)).strftime('%Y-%m-%d')


def get_ac_debit_balances_as_on(date):
	rs = frappe.db.sql("""
	SELECT REPLACE(account, CONCAT(' -', SUBSTRING_INDEX(account, '-',-1)), '') AS account_con,
	sum(ifnull(debit, 0)) - sum(ifnull(credit, 0)) AS debit_balance
	FROM `tabGL Entry` gle
	WHERE posting_date <= "{date}"
	GROUP BY account_con;
	""".format(date=date), as_dict=True)

	for r in rs:
		r.account = r.account_con.strip()

	return rs

