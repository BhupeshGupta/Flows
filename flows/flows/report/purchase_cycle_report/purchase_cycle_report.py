# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import utils

def execute(filters=None):
	data_dict_list = get_data(filters)
	data = []
	for entry in data_dict_list:
		data.append([
			utils.formatdate(entry.indent.posting_date),
			entry.indent.name,
			entry.indent.vehicle,
			utils.formatdate(entry.gatepass_out.posting_date) if entry.gatepass_out else "",
			entry.gatepass_out.name if entry.gatepass_out else "",
			utils.formatdate(entry.gatepass_in.posting_date) if entry.gatepass_in else "",
			entry.gatepass_in.name if entry.gatepass_in else "",
			utils.formatdate(entry.bill_date) if entry.bill_date else "",
			entry.expected_bill_count,
			entry.entered_bill_count,
			entry.physical_state,
			entry.bill_state
		])
	return get_columns(), data


def get_columns():
	return [
		"Indent Date",
		"Indent:Link/Indent:100",
		"Vehicle:Link/Transportation Vehicle:100",
		"GP Out Date",
		"GP Out:Link/Gatepass:100",
		"GP In Date",
		"GP In:Link/Gatepass:100",
		"Bill Date",
		"Total Bills",
		"Bills Entered",
		"Phy State",
		"Bill Status"
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

	default_row_dict = {
	"indent": "",
	"gatepass_in": "",
	"gatepass_out": "",
	"bill_date": "",
	"expected_bill_count": "",
	"entered_bill_count": "",
	"physical_state": "Pending",
	"bill_state": "Pending",
	}

	indents = get_indents()
	gatepass_map = get_indent_linked_gp_map()

	for indent in indents:
		row_dict = frappe._dict(default_row_dict)

		row_dict.indent = indent

		out_key = '{}#{}'.format(indent.name, 'Out')
		if out_key in gatepass_map:
			row_dict.gatepass_out = gatepass_map[out_key]

		in_key = '{}#{}'.format(indent.name, 'In')
		if in_key in gatepass_map:
			row_dict.gatepass_in = gatepass_map[in_key]

		expected_bill_count = frappe.db.sql("""
		select count(name) from `tabIndent Item`
		where parent = \"{}\" """.format(indent.name))
		entered_bill_count = frappe.db.sql("""
		select count(name) from `tabIndent Invoice`
		where indent = \"{}\" and docstatus != 2""".format(indent.name))

		row_dict.expected_bill_count = int(expected_bill_count[0][0]) if len(expected_bill_count) > 0 else 0
		row_dict.entered_bill_count = int(entered_bill_count[0][0]) if len(entered_bill_count) > 0 else 0

		frappe.msgprint("Bill Count: %s" % row_dict.entered_bill_count)
		if row_dict.entered_bill_count > 0:
			row_dict.bill_date = frappe.db.sql(
				"""select transaction_date from `tabIndent Invoice` where
				docstatus != 2 and indent='{}' limit 1""".format(indent.name))[0][0]
		frappe.msgprint("Bill Date: %s" % row_dict.bill_date)

		# State Algo
		if row_dict.gatepass_out:
			row_dict.physical_state = "Dispatched"
			if row_dict.gatepass_in:
				row_dict.physical_state = "Received"

		if row_dict.expected_bill_count - row_dict.entered_bill_count == 0:
			row_dict.bill_state = "Completed"

		rows.append(row_dict)

	return rows
