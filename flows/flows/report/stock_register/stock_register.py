# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint
from flows.utils import get_next_date

def execute(filters=None):
	if filters.bifurcate:
		filters.bifurcate = cint(filters.bifurcate)

	columns = get_columns(filters)
	filled_iwb_map = get_item_warehouse_map(filters)

	filters.item_code = filters.item_code.replace('FC', 'EC')
	empty_iwb_map = get_item_warehouse_map(filters)

	import json
	from flows.stdlogger import root

	root.debug(json.dumps(filled_iwb_map))

	data = []
	empty_dict = frappe._dict({
		"opening_qty": 0.0,
		"in": {'GR': 0, 'PR': 0, 'GP': 0, 'OTHER': 0},
		"out": {'GR': 0, 'PR': 0, 'GP': 0, 'OTHER': 0},
		"bal_qty": 0.0
	})

	posting_date = filters.from_date
	while posting_date <= filters.to_date:
		filled_qty_dict = filled_iwb_map.get(posting_date)
		empty_qty_dict = empty_iwb_map.get(posting_date)
		if not filled_qty_dict:
			filled_qty_dict = empty_dict
		if not empty_qty_dict:
			empty_qty_dict = empty_dict

		data.append(get_row(posting_date, filled_qty_dict, empty_qty_dict, filters))

		posting_date = get_next_date(posting_date)

	return columns, data


def get_columns(filters):
	"""return columns based on filters"""

	columns = [
		"Date:Date:100",
		"Opening(F):Float:100",
	]

	columns.extend([
		"GR IN(F):Float:80",
		"PR IN(F):Float:80",
		"GP IN(F):Float:80",
		"OTHER IN(F):Float:80",
	] if filters.bifurcate else ["IN(F):Float:80"])

	columns.extend([
		"GR OUT(F):Float:80",
		"PR OUT(F):Float:80",
		"GP OUT(F):Float:80",
		"OTHER OUT(F):Float:80",
	] if filters.bifurcate else ["OUT(F):Float:80"])

	columns.extend([
		"Closing(F):Float:100",
		"::50",
		"Opening(E):Float:100",
	])

	columns.extend([
		"GR IN(E):Float:80",
		"PR IN(E):Float:80",
		"GP IN(E):Float:80",
		"OTHER IN(E):Float:80",
	] if filters.bifurcate else ["IN(E):Float:80"])

	columns.extend([
		"GR OUT(E):Float:80",
		"PR OUT(E):Float:80",
		"GP OUT(E):Float:80",
		"OTHER OUT(E):Float:80",
	] if filters.bifurcate else ["OUT(E):Float:80"])

	columns.extend(["Closing(E):Float:100"])

	return columns

def get_row(posting_date, filled_qty_dict, empty_qty_dict, filters):
	row = [
		posting_date,
		filled_qty_dict.opening_qty,
	]

	row.extend(
		[
			filled_qty_dict['in']['GR'],
			filled_qty_dict['in']['PR'],
			filled_qty_dict['in']['GP'],
			filled_qty_dict['in']['OTHER']
		] if filters.bifurcate else
		[sum(filled_qty_dict['in'].values())]
	)

	row.extend(
		[
			filled_qty_dict['out']['GR'],
			filled_qty_dict['out']['PR'],
			filled_qty_dict['out']['GP'],
			filled_qty_dict['out']['OTHER'],
		] if filters.bifurcate else
		[sum(filled_qty_dict['out'].values())]
	)

	row.extend([
		filled_qty_dict.bal_qty,
		"",
		empty_qty_dict.opening_qty,
	])

	row.extend(
		[
			empty_qty_dict['in']['GR'],
			empty_qty_dict['in']['PR'],
			empty_qty_dict['in']['GP'],
			empty_qty_dict['in']['OTHER'],
		] if filters.bifurcate else
		[sum(empty_qty_dict['in'].values())]
	)

	row.extend(
		[
			empty_qty_dict['out']['GR'],
			empty_qty_dict['out']['PR'],
			empty_qty_dict['out']['GP'],
			empty_qty_dict['out']['OTHER'],
		] if filters.bifurcate else
		[sum(empty_qty_dict['out'].values())]
	)

	row.extend([empty_qty_dict.bal_qty])

	return row


def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and posting_date <= '%s'" % filters["to_date"]
	else:
		frappe.throw(_("'To Date' is required"))

	if filters.get("warehouse"):
		conditions += " and warehouse = '%s'" % filters["warehouse"]
	else:
		frappe.throw(_("'Warehouse' is required"))

	if filters.get("item_code"):
		conditions += " and item_code = '%s'" % filters["item_code"]
	else:
		frappe.throw(_("'Item' is required"))

	return conditions


# get all details
def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	# and ifnull(process, '') not in ('Consumption')
	return frappe.db.sql(
	"""
		select item_code, posting_date, actual_qty,
		voucher_type, qty_after_transaction
		from `tabStock Ledger Entry`
		where docstatus < 2
		%s
		order by posting_date, posting_time, name
	""" % conditions, as_dict=1)


def get_item_warehouse_map(filters):
	sle = get_stock_ledger_entries(filters)
	opening_iwb_map = {}
	iwb_map = {}

	# Init Map To At least Show Opening
	iwb_map.setdefault(filters.from_date, frappe._dict({
		"opening_qty": 0.0,
		"in": {'GR': 0, 'PR': 0, 'GP': 0, 'OTHER': 0},
		"out": {'GR': 0, 'PR': 0, 'GP': 0, 'OTHER': 0},
		"bal_qty": 0.0
	}))

	for d in sle:
		active_map = opening_iwb_map if d.posting_date < filters["from_date"] else iwb_map

		active_map.setdefault(d.posting_date, frappe._dict({
			"opening_qty": 0.0,
			"in": {'GR': 0, 'PR': 0, 'GP': 0, 'OTHER': 0},
			"out": {'GR': 0, 'PR': 0, 'GP': 0, 'OTHER': 0},
			"bal_qty": 0.0
		}))

		qty_dict = active_map[d.posting_date]

		if d.voucher_type == "Stock Reconciliation":
			qty_diff = flt(d.qty_after_transaction) - qty_dict.bal_qty
		else:
			qty_diff = flt(d.actual_qty)

		if d.posting_date <= filters["to_date"]:
			if qty_diff > 0:
				qty_dict['in'].setdefault(get_voucher_key(d), 0)
				qty_dict['in'][get_voucher_key(d)] += qty_diff
			else:
				qty_dict['out'].setdefault(get_voucher_key(d), 0)
				qty_dict['out'][get_voucher_key(d)] += abs(qty_diff)

	last_balance = compute_openings_and_closings(opening_iwb_map)
	compute_openings_and_closings(iwb_map, last_balance=last_balance)

	return iwb_map


def compute_openings_and_closings(iwb_map, last_balance=None):
	last_balance = last_balance if last_balance else 0
	for posting_date in sorted(iwb_map):
		qty_dict = iwb_map[posting_date]
		qty_dict.opening_qty = last_balance
		qty_dict.bal_qty = qty_dict.opening_qty + sum(qty_dict['in'].values()) - sum(qty_dict['out'].values())
		last_balance = qty_dict.bal_qty

	return last_balance


def get_voucher_key(voucher):
	if voucher.voucher_type == "Payment Receipt":
		return "PR"
	elif voucher.voucher_type == "Goods Receipt":
		return "GR"
	elif voucher.voucher_type == "Gatepass":
		return "GP"
	else:
		return "OTHER"