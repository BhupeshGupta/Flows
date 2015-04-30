from frappe.model.rename_doc import rename_doc


def execute():
	rename_doc("DocType", "Cash Receipt", "Payment Receipt", force=1)