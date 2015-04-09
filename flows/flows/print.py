import frappe
from frappe.utils.pdf import get_pdf

import json

@frappe.whitelist()
def download_pdf(doctype, name, format=None):
	from flows.stdlogger import root
	root.debug((doctype, name, format))

	if "[" not in name:
		name = '["{}"]'.format(name)

	pages = []
	name_list = json.loads(name)

	for id in name_list:
		pages.append(frappe.get_print_format(doctype, id, format))

	html = """<div class="page-break"></div>""".join(pages)

	frappe.local.response.filename = "{name}.pdf".format(name=name_list[0].replace(" ", "-").replace("/", "-"))
	frappe.local.response.filecontent = get_pdf(html)
	frappe.local.response.type = "download"