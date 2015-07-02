from __future__ import unicode_literals

from __future__ import unicode_literals

import frappe
import frappe.defaults
from frappe.utils import cint

from erpnext.accounts.general_ledger import make_gl_entries, delete_gl_entries


def execute():
	for name in frappe.db.sql("""
		SELECT name
		FROM `tabIndent Invoice`
		WHERE docstatus = 1;
		"""):
		name = name[0]

		if cint(name) < 1000:
			continue

		invoice = frappe.get_doc("Indent Invoice", name)
		gl_entries = invoice.get_gl_entries()

		delete_gl_entries(voucher_type="Indent Invoice", voucher_no=name)
		make_gl_entries(gl_entries)