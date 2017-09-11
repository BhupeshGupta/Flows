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
	# posting_date >= '2015-05-01'
	return frappe.db.sql("""
		SELECT * FROM
		`tabIndent` WHERE
		docstatus != 2 AND
		posting_date >= '2017-04-01'
		order by creation desc;
		""", as_dict=True)

def get_indent_linked_gp_map():
	map = frappe._dict({})
	data = frappe.db.sql(
		"SELECT * FROM `tabGatepass` WHERE docstatus = 1 and indent != '' and posting_date >= '2017-03-01';",
		as_dict=True
	)
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

	all_indents = [indent.name for indent in indents]
	all_indents_names = ', '.join(['"{}"'.format(x) for x in all_indents])

	expected_bill_count_map = frappe.db.sql("""
	select parent, count(name)
	from `tabIndent Item`
	where parent in ({})
	group by parent
	""".format(all_indents_names))

	expected_bill_count_map = {row[0]: row[1] for row in expected_bill_count_map}

	entered_bill_count_map = frappe.db.sql("""
	select indent, count(name)
	from `tabIndent Invoice`
	where indent in ({})
	and docstatus != 2
	""".format(all_indents_names))

	entered_bill_count_map = {row[0]: row[1] for row in entered_bill_count_map}

	invoice_date_map = frappe.db.sql("""
	select indent, transaction_date
	from `tabIndent Invoice`
	where docstatus != 2
	and indent in ({})
	group by indent""".format(all_indents_names))

	invoice_date_map = {row[0]: row[1] for row in invoice_date_map}


	for indent in indents:
		row_dict = frappe._dict(default_row_dict)

		row_dict.indent = indent

		out_key = '{}#{}'.format(indent.name, 'Out')
		if out_key in gatepass_map:
			row_dict.gatepass_out = gatepass_map[out_key]

		in_key = '{}#{}'.format(indent.name, 'In')
		if in_key in gatepass_map:
			row_dict.gatepass_in = gatepass_map[in_key]

		expected_bill_count = expected_bill_count_map.get(indent.name, 0)
		entered_bill_count = entered_bill_count_map.get(indent.name, 0)

		row_dict.expected_bill_count = expected_bill_count
		row_dict.entered_bill_count = entered_bill_count

		if row_dict.entered_bill_count > 0:
			row_dict.bill_date = invoice_date_map[indent.name]

		# State Algo
		if row_dict.gatepass_out:
			row_dict.physical_state = "Dispatched"
			if row_dict.gatepass_in:
				row_dict.physical_state = "Received"

		if row_dict.expected_bill_count - row_dict.entered_bill_count == 0:
			row_dict.bill_state = "Completed"

		rows.append(row_dict)

	return rows
