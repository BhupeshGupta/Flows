# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns(filters)
	filled_iwb_map = get_item_warehouse_map(filters)

	filters.item_code = filters.item_code.replace('FC', 'EC')
	empty_iwb_map = get_item_warehouse_map(filters)

	data = []
	empty_dict = frappe._dict({
	"opening_qty": "",
	"in_qty": "",
	"out_qty": "",
	"bal_qty": ""
	})

	posting_date = filters.from_date
	while posting_date <= filters.to_date:
		filled_qty_dict = filled_iwb_map.get(posting_date)
		empty_qty_dict = empty_iwb_map.get(posting_date)
		if not filled_qty_dict: filled_qty_dict = empty_dict
		if not empty_qty_dict: empty_qty_dict = empty_dict

		data.append([
			posting_date,
			filled_qty_dict.opening_qty,
			filled_qty_dict.in_qty,
			filled_qty_dict.out_qty,
			filled_qty_dict.bal_qty,
			"",
			empty_qty_dict.opening_qty,
			empty_qty_dict.in_qty,
			empty_qty_dict.out_qty,
			empty_qty_dict.bal_qty,
		])

		posting_date = get_next_date(posting_date)

	return columns, data


def get_columns(filters):
	"""return columns based on filters"""

	columns = [
		"Date:Date:100",
		"Filled Opening Qty:Float:100",
		"Filled In Qty:Float:80",
		"Filled Out Qty:Float:80",
		"Filled Closing Qty:Float:100",
		"::100",
		"Empty Opening Qty:Float:100",
		"Empty In Qty:Float:80",
		"Empty Out Qty:Float:80",
		"Empty Closing Qty:Float:100"
	]

	return columns


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
	return frappe.db.sql("""select item_code, posting_date, actual_qty,
		voucher_type, qty_after_transaction
		from `tabStock Ledger Entry`
		where docstatus < 2 %s order by posting_date, posting_time, name""" %
						 conditions, as_dict=1)


def get_item_warehouse_map(filters):
	sle = get_stock_ledger_entries(filters)
	opening_iwb_map = {}
	iwb_map = {}

	# Init Map To At least Show Opening
	iwb_map.setdefault(filters.from_date, frappe._dict({
	"opening_qty": 0.0, "in_qty": 0.0,
	"out_qty": 0.0, "bal_qty": 0.0
	}))

	for d in sle:
		active_map = opening_iwb_map if d.posting_date < filters["from_date"] else iwb_map

		active_map.setdefault(d.posting_date, frappe._dict({
		"opening_qty": 0.0, "in_qty": 0.0,
		"out_qty": 0.0, "bal_qty": 0.0
		}))

		qty_dict = active_map[d.posting_date]

		if d.voucher_type == "Stock Reconciliation":
			qty_diff = flt(d.qty_after_transaction) - qty_dict.bal_qty
		else:
			qty_diff = flt(d.actual_qty)

		if d.posting_date <= filters["to_date"]:
			if qty_diff > 0:
				qty_dict.in_qty += qty_diff
			else:
				qty_dict.out_qty += abs(qty_diff)

	last_balance = compute_openings_and_closings(opening_iwb_map)
	compute_openings_and_closings(iwb_map, last_balance=last_balance)

	return iwb_map


def compute_openings_and_closings(iwb_map, last_balance=None):
	last_balance = last_balance if last_balance else 0
	for posting_date in sorted(iwb_map):
		qty_dict = iwb_map[posting_date]
		qty_dict.opening_qty = last_balance
		qty_dict.bal_qty = qty_dict.opening_qty + qty_dict.in_qty - qty_dict.out_qty
		last_balance = qty_dict.bal_qty

	return last_balance


import datetime


def get_next_date(cur_date):
	return (datetime.datetime.strptime(cur_date, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime('%Y-%m-%d')