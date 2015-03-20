import frappe
from erpnext.accounts.party import get_party_account


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
		print "missing act head"
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


class FormatDict(dict):
	def __missing__(self, k):
		return '{' + k + '}'