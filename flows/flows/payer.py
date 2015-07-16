import frappe
from erpnext.accounts.party import get_party_account


def get_payer_account(company, supplier, customer, payment_type):
	if 'hpcl' in supplier.lower() or payment_type.lower() == "direct":
		acc_head = frappe.db.get_value("Account", {
		"master_type": "Customer",
		"master_name": customer,
		"company": company,
		"account_type": "Payer"
		})

		if not acc_head:
			# create
			company_details = frappe.db.get_value("Company", company,
												  ["abbr", "receivables_group", "payables_group"], as_dict=True)
			account = frappe.get_doc({
			'doctype': 'Account',
			'account_name': '{} a/c {}'.format(supplier.split(' ')[0].title(), customer),
			'parent_account': company_details.payables_group,
			'group_or_ledger': 'Ledger',
			'company': company,
			'master_type': "Customer",
			'master_name': customer,
			"freeze_account": "No",
			"report_type": "Balance Sheet",
			"account_type": "Payer"
			}).insert(ignore_permissions=True)
			acc_head = account.name

		return acc_head

	acc_head = get_party_account(company, supplier, "Supplier")

	return acc_head