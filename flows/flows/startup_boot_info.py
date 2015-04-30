import frappe


def boot_session(bootinfo):
	"""boot session - send website info if guest"""

	# from flows.utils import get_stock_owner_via_sales_person_tree
	# if frappe.session['user'] != 'Guest':
	# 	stock_owner = get_stock_owner_via_sales_person_tree(frappe.session['user'])
	# 	bootinfo['payment_receipt'] = {
	# 		"stock_owner": stock_owner
	# 	}

	# from flows.stdlogger import root
	#
	# root.debug('bootup ran')

def get_startup_js():
	return frappe.read_file(frappe.get_app_path('flows', *['asserts', 'js', 'flows.js']))
