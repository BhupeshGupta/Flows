from frappe import throw

def journal_voucher_autoname(doc, method=None, *args, **kwargs):
	if doc.voucher_type == "Cash Receipt(CR)":
		doc.name = doc.id

def journal_voucher_validate(doc, method=None, *args, **kwargs):
	if doc.voucher_type == "Cash Receipt(CR)":
		if not doc.id:
			throw("ID is required for cash receipt")
		elif doc.name and doc.id != doc.name.split("-")[0]:
			throw("Cannot change type to Cash Receipt(CR) or id after saving voucher")