import json

from frappe.utils import cint
from flows.stdlogger import root
import frappe

@frappe.whitelist(allow_guest=True)
def get_meta(doc):
	doc = json.loads(doc)
	return json.dumps(frappe.db.get_value("Contact", filters={"phone":doc['phone']}, fieldname="customer", as_dict=False))