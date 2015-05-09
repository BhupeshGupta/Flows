# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import utils

def execute(filters=None):
	data = get_data(filters)
	return get_columns(), data


def get_columns():
	return [
		"Indent Date",
		"Indent",
		"GP Out Date",
		"GP Out",
		"GP In Date",
		"GP In",
		"Total Bills",
		"Bills Entered",
		"State"
	]


def get_indents():
	return frappe.db.sql("""
		SELECT * FROM
		`tabIndent` WHERE
		docstatus != 2 AND
		posting_date >= '2015-05-01'
		order by posting_date desc;
		""", as_dict=True)

def get_indent_linked_gp_map():
	map = frappe._dict({})
	data = frappe.db.sql("SELECT * FROM `tabGatepass` WHERE docstatus = 1 and indent != '';", as_dict=True)
	for gp in data:
		map['{}#{}'.format(gp.indent, gp.gatepass_type)] = gp
	return map


def get_data(filters):
	rows = []
	indents = get_indents()
	gatepass_map = get_indent_linked_gp_map()

	for indent in indents:
		row = [utils.formatdate(indent.posting_date), indent.name]

		in_key = '{}#{}'.format(indent.name, 'In')
		out_key = '{}#{}'.format(indent.name, 'Out')
		out_gp_subarray = ["", ""]
		if out_key in gatepass_map:
			out_gp = gatepass_map[out_key]
			out_gp_subarray = [utils.formatdate(out_gp.posting_date), out_gp.name]

		in_gp_subarray = ["", ""]
		if in_key in gatepass_map:
			in_gp = gatepass_map[in_key]
			in_gp_subarray = [utils.formatdate(in_gp.posting_date), in_gp.name]

		no_of_bills_expected = frappe.db.sql("""
		select count(name) from `tabIndent Item`
		where parent = \"{}\" """.format(indent.name))

		no_of_bills_entered = frappe.db.sql("""
		select count(name) from `tabIndent Invoice`
		where indent = \"{}\" and docstatus != 2""".format(indent.name))

		row.extend(out_gp_subarray)
		row.extend(in_gp_subarray)
		row.append(no_of_bills_expected)
		row.append(no_of_bills_entered)

		rows.append(row)

	return rows
