from __future__ import unicode_literals

from dateutil import parser

import frappe


def execute():
	for cp_id in frappe.db.sql("""
		SELECT name
		FROM `tabIndent Invoice`
		WHERE docstatus = 1;
		"""):
		cp = frappe.get_doc("Indent Invoice", cp_id[0])
		if cp.creation:
			frappe.db.sql("""
			UPDATE `tabIndent Invoice` SET
			invoice_receive_date = "{}"
			WHERE name = "{}";
			""".format(parser.parse(cp.creation).strftime("%Y-%m-%d"), cp.name))