import frappe
from frappe.model.rename_doc import rename_doc as original_rename_doc
from flows.stdlogger import root

@frappe.whitelist()
def rename_doc(doctype, old, new, force=False, merge=False, ignore_permissions=False):
	retval = original_rename_doc(doctype, old, new, force, merge, ignore_permissions)
	root.debug("Rename ran")
	if doctype == "Customer":
		root.debug("Rename customer")
		for w in frappe.db.sql("""select name from `tabWarehouse` where name like "{} -%" """.format(old)):
			old_name = w[0]
			new_name = "{} - {}".format(new, old_name.split("-")[1].strip())
			original_rename_doc("Warehouse", old_name, new_name, force, merge, ignore_permissions)

	return retval