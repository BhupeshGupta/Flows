import frappe
import json

@frappe.whitelist()
def submit(doctype=None, name=None):
	"""submit a doclist"""
	try:
		if not '[' in name:
			name = '["{}"]'.format(name)
		name_list = json.loads(name)

		for name_instance in name_list:
			doc = frappe.get_doc(doctype, name_instance)
			doc.submit()

		return 'ok'

	except Exception:
		frappe.errprint(frappe.utils.get_traceback())
		frappe.msgprint(frappe._("Did not Submit"))
		raise