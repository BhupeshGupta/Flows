import frappe
from frappe.utils import cint


def journal_voucher_autoname(doc, method=None, *args, **kwargs):
	doc.naming_series = doc.naming_series.strip()
	if doc.voucher_type == "Cash Receipt(CR)":
		doc.name = '{}CR-{}'.format(doc.naming_series, doc.id)


def journal_voucher_validate(doc, method=None, *args, **kwargs):
	if doc.voucher_type == "Cash Receipt(CR)":
		if not doc.id:
			frappe.throw("ID is required for cash receipt")
		elif doc.name and doc.id != doc.name.split("-")[2]:
			frappe.throw("Cannot change type to Cash Receipt(CR) or id after saving voucher")


def contact_validate_for_sms(doc, method=None, *args, **kwargs):
	if cint(doc.sms_optin) == 1:
		if "Quality Manager" not in frappe.get_user(frappe.session.user).get_roles():
			frappe.throw("Quality Manager can update sms opted in contacts")


def validate_imprest_account_gl_entry_date(doc, method=None, *args, **kwargs):
	if not doc:
		account = kwargs['account']
		posting_date = kwargs['posting_date']
	else:
		account = doc.account
		posting_date = doc.posting_date

	blocked = frappe.db.sql("""
	select count(a.name) as blocked
	from `tabSingles` s, `tabAccount` a
	where a.name="{}"
	and a.account_type='Imprest'
	and s.doctype = 'Flow Settings'
	and s.field = 'imprest_closing_date'
	and s.value >= '{}'
	""".format(account, posting_date))

	if blocked:
		if frappe.session.user == "Administrator":
			frappe.msgprint("FYI. Date for entry in imprest is closed")
		else:
			frappe.throw("Date for entry in imprest is closed for amendment/posting")
