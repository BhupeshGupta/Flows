import json

import frappe

@frappe.whitelist(allow_guest=True)
def get_customers(phone):
	return json.dumps(frappe.db.get_values("Contact", filters={"phone":phone}, fieldname="customer", as_dict=True))