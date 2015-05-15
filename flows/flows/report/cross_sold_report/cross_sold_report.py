# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cint


def execute(filters=None):
	cleared_list = cleared_map(filters)
	filters.cleared_list = cleared_list

	data = []
	data_map = get_data(filters)

	global_aggr = frappe._dict({
	'items': {},
	'uncleared_op': 0,
	'cleared_amount': 0,
	'uncleared_amount': 0
	})

	for customer, data_dict in data_map.items():
		op_uncleared_balance = get_uncleared_balance_before(customer, filters.from_date)
		data.append(["", "Opening Uncleared", flt(op_uncleared_balance), "", "", "", "", ""])
		for invoice in data_dict.invoices:
			row = [
				invoice.transaction_date,
				customer,
				invoice.actual_amount,
				invoice.transportation_invoice_amount,
				invoice.item,
				invoice.qty,
				invoice.name,
				"Indent Invoice",
				cleared_list[invoice.name] if invoice.name in cleared_list else ''
			]
			data.append(row)

		for indent in data_dict.indents:
			row = [
				indent.posting_date,
				customer,
				0,
				0,
				indent.item,
				indent.qty,
				indent.name,
				"Indent",
				""
			]
			data.append(row)

		data.append([])
		data.extend(get_total_rows_list(data_dict, op_uncleared_balance))
		data.extend([[], []])

		# Aggr for global totals
		for item, qty in data_dict['items'].items():
			global_aggr['items'].setdefault(item, 0)
			global_aggr['items'][item] += qty

		global_aggr.uncleared_op += op_uncleared_balance
		global_aggr.cleared_amount += data_dict.cleared_amount
		global_aggr.uncleared_amount += flt(data_dict.uncleared_amount)

	data.extend(get_grand_total_rows_list(global_aggr))

	from flows.stdlogger import root

	root.debug(data)

	return get_columns(filters), data


def get_columns(filters):
	return [
		"Date:Date:100",
		"Customer:Data:250",
		"Invoice Amount:Currency:100",
		"CN Amount:Currency:100",
		"Item:data:",
		"Quantity:Int:",
		"Voucher:Dynamic Link/Voucher Type:100",
		"Voucher Type::",
		"Clearance Date:Date:150"
	]


def get_data(filters):
	indents, invoices = get_indents_and_invoices(filters)

	data_map = frappe._dict({})

	for invoice in invoices:
		data_map.setdefault(invoice.customer, frappe._dict({
		'invoices': [],
		'indents': [],
		'cleared_amount': 0,
		'uncleared_amount': 0,
		'invoice_total': 0,
		'transportation_invoice_amount': 0,
		'items': {}
		}))

		active_dict = data_map[invoice.customer]

		active_dict[
			'cleared_amount' if invoice.name in filters.cleared_list else 'uncleared_amount'
		] += (flt(invoice.actual_amount) + flt(invoice.transportation_invoice_amount))

		active_dict.invoice_total += flt(invoice.actual_amount)
		active_dict.transportation_invoice_amount += flt(invoice.transportation_invoice_amount)

		active_dict['items'].setdefault(invoice.item, 0)
		active_dict['items'][invoice.item] += invoice.qty

		active_dict.invoices.append(invoice)

	for indent in indents:
		data_map.setdefault(indent.customer, frappe._dict({
		'invoices': [],
		'indents': [],
		'cleared_amount': 0,
		'uncleared_amount': 0,
		'invoice_total': 0,
		'transportation_invoice_amount': 0,
		'items': {}
		}))

		active_dict = data_map[indent.customer]

		active_dict['items'].setdefault(indent.item, 0)
		active_dict['items'][indent.item] += indent.qty

		active_dict.indents.append(indent)

	return data_map


def cleared_map(filters):
	clearing_map = {}

	cleared = frappe.db.sql(
		"""
		SELECT cpi.invoice AS invoice, cp.posting_date AS posting_date FROM `tabCross Purchase` cp,
		`tabCross Purchase Item` cpi
		WHERE cp.docstatus = 1
		AND cpi.parent = cp.name
		""", as_dict=True
	)

	for c in cleared:
		clearing_map[c.invoice] = c.posting_date

	return clearing_map


def get_uncleared_balance_before(customer, date):
	previous_invoices_balance = frappe.db.sql("""
	SELECT sum(ifnull(actual_amount, 0)) + sum(ifnull(transportation_invoice_amount, 0))
	FROM `tabIndent Invoice`
	WHERE customer = '{}' AND transaction_date < '{}' AND cross_sold = 1 AND docstatus = 1;
	""".format(customer, date))

	if not previous_invoices_balance:
		return 0

	previous_invoices_balance = previous_invoices_balance[0][0]

	cleared_balance = frappe.db.sql("""
		SELECT sum(ifnull(cpi.invoice_amount, 0)) + sum(ifnull(cpi.consignment_note_amount, 0))
		FROM `tabCross Purchase` cp, `tabCross Purchase Item` cpi
		WHERE cp.docstatus = 1
		AND cpi.parent = cp.name
		AND cpi.invoice IN
		(SELECT name FROM `tabIndent Invoice`
		WHERE customer = '{}' AND transaction_date < '{}'
		AND cross_sold = 1 AND docstatus = 1);
	""".format(customer, date))

	cleared_balance = cleared_balance[0][0] if cleared_balance else 0

	return flt(previous_invoices_balance) - flt(cleared_balance)


def get_item_row(item_map, item):
	row = [item, 0]
	if item in item_map:
		row = [item, item_map[item]]
	return row


def get_total_rows_list(data_dict, op_balance):
	rows = []

	row = ["", "Total", data_dict.invoice_total, data_dict.transportation_invoice_amount, ]
	row.extend(get_item_row(data_dict['items'], 'FC19'))
	rows.append(row)

	row = ["", "T.Amount", data_dict.invoice_total + data_dict.transportation_invoice_amount, ""]
	row.extend(get_item_row(data_dict['items'], 'FC35'))
	rows.append(row)

	row = ["", "Cleared", data_dict.cleared_amount, ""]
	row.extend(get_item_row(data_dict['items'], 'FC47.5'))
	rows.append(row)

	row = ["", "Uncleared + Opening Uncleared", flt(op_balance) + flt(data_dict.uncleared_amount), ""]
	row.extend(get_item_row(data_dict['items'], 'FC47.5L'))
	rows.append(row)

	return rows


def get_grand_total_rows_list(global_aggr):
	rows = []

	row = ["", "Grand Total", global_aggr.cleared_amount + global_aggr.uncleared_amount, ""]
	row.extend(get_item_row(global_aggr['items'], 'FC19'))
	rows.append(row)

	row = ["", "Grand Cleared", global_aggr.cleared_amount, ""]
	row.extend(get_item_row(global_aggr['items'], 'FC35'))
	rows.append(row)

	row = ["", "Grand Uncleared", global_aggr.uncleared_amount, ""]
	row.extend(get_item_row(global_aggr['items'], 'FC47.5'))
	rows.append(row)

	row = ["", "Grand Uncleared Opening", global_aggr.uncleared_op, ""]
	row.extend(get_item_row(global_aggr['items'], 'FC47.5L'))
	rows.append(row)

	row = ["", "Uncleared + Opening Uncleared", global_aggr.uncleared_amount + global_aggr.uncleared_op, ""]
	rows.append(row)

	return rows


def get_indents_and_invoices(filters):
	condition = ""
	if filters.customer:
		condition = " AND customer='{}'".format(filters.customer)

	invoices = frappe.db.sql("""
		SELECT * FROM `tabIndent Invoice`
		WHERE cross_sold = 1
		AND docstatus = 1
		AND transaction_date <= '{to_date}'
		AND transaction_date >= '{from_date}'
		{CONDITION}
		ORDER BY transaction_date
		""".format(CONDITION=condition, **filters), as_dict=True)

	if cint(filters.include_indents) == 1:
		indents = frappe.db.sql("""
		SELECT i.name, i.posting_date, it.customer, it.item, it.qty FROM `tabIndent` i, `tabIndent Item` it
		WHERE cross_sold = 1 AND it.parent = i.name
		AND it.name NOT IN (SELECT ifnull(indent_item, '') FROM `tabIndent Invoice` WHERE docstatus = 1)
		""", as_dict=True)
	else:
		indents = []

	return indents, invoices
