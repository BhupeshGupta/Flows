import frappe
from flows.utils import get_stock_owner_via_sales_person_tree


def boot_session(bootinfo):
	"""boot session - send website info if guest"""

	if frappe.session['user'] != 'Guest':
		stock_owner = get_stock_owner_via_sales_person_tree(frappe.session['user'])
		bootinfo['cash_receipt'] = {
			"stock_owner": stock_owner
		}