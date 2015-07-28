# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, flt


def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data


def get_columns(filters):
	return [
		"Date:Date:100",
		"Voucher Type::120",
		"Voucher No:Dynamic Link/Voucher Type:160",
		"Billed Qty:Float:100",
		"Qty Delivered:Float:100",
		"Empty Received:Float:100",
		"Filled Balance:Float:",
		"Empty Pending:Float:",
		"Remarks::400"
	]


def get_data(filters):
	data = []

	stock_ledger_entries = get_sl_entries(filters)
	indent_invoices = get_invoices_entries(filters)
	opening_grs = get_opening_gr(filters)
	vouchers = stock_ledger_entries + indent_invoices + opening_grs
	vouchers = sorted(vouchers, key=lambda k: k['posting_date'])

	opening_map, current_map = initialize_voucher_maps(filters, vouchers)

	current_map = get_data_with_opening_closing(filters, opening_map, current_map)

	for item in sorted(current_map.keys()):
		map = current_map[item]

		data.append(get_opening_row(map))

		for voucher in map.entries:
			billed, delivered, received = bill_filled_empty_status(voucher, item, filters)
			data.append([
				voucher.get("posting_date"),
				voucher.voucher_type if voucher.v_type == 'Stock Ledger Entry' else voucher.v_type,
				voucher.voucher_no if voucher.v_type == 'Stock Ledger Entry' else voucher.get("name"),
				billed,
				delivered,
				received,
				voucher.filled,
				voucher.empty,
				""
			])
		data.extend(get_closing_row_with_totals(map))

		data.append(["", "", "", "", "", ""])

	return data


def get_sle_conditions(filters):
	conditions = []
	# item_conditions = get_item_conditions(filters)
	# if item_conditions:
	# conditions.append("""item_code in (select name from tabItem
	# {item_conditions})""".format(item_conditions=item_conditions))
	# if filters.get("warehouse"):
	# conditions.append("warehouse=%(warehouse)s")

	conditions.append('warehouse like "{}%%"'.format(filters.customer))

	if filters.get("voucher_no"):
		conditions.append("voucher_no=%(voucher_no)s")

	return "and {}".format(" and ".join(conditions)) if conditions else ""


def get_item_conditions(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("name=%(item_code)s")
	if filters.get("brand"):
		conditions.append("brand=%(brand)s")

	return "where {}".format(" and ".join(conditions)) if conditions else ""


def get_sl_entries(filters):
	stock_ledger_entries = frappe.db.sql(
		"""
		SELECT posting_date, item_code as item, actual_qty as qty,
	           process, voucher_type, voucher_no
		FROM `tabStock Ledger Entry`
		WHERE
	      posting_date <= %(to_date)s AND
	      ifnull(process, '') = '' AND
	      voucher_type != "Goods Receipt"
		  {sle_conditions}
		ORDER BY posting_date desc, posting_time desc, name desc""".format(
			sle_conditions=get_sle_conditions(filters)),
		filters,
		as_dict=1,
		debug=True
	)

	for sle in stock_ledger_entries:
		sle.v_type = 'Stock Ledger Entry'

	return stock_ledger_entries


def get_invoices_entries(filters):
	# posting_date
	indent_invoices = frappe.db.sql(
		"""
		SELECT name, transaction_date as posting_date, customer, item, qty
		FROM `tabIndent Invoice`
		WHERE docstatus = 1 AND
		customer="{}" AND
		cross_sold = 0 AND
		transaction_date <= %(to_date)s
		ORDER BY transaction_date desc, posting_time desc, name desc;""".format(filters['customer']),
		filters,
		as_dict=True
	)
	for i in indent_invoices:
		i.v_type = 'Indent Invoice'

	return indent_invoices


def get_opening_gr(filters):
	# posting_date
	grs = frappe.db.sql(
		"""
		SELECT is_opening, name,
		posting_date, customer,
		item_delivered, delivered_quantity,
		item_received, received_quantity
		FROM `tabGoods Receipt`
		WHERE docstatus = 1 AND
		cancelled = 0 AND
		customer="{}" AND
		posting_date <= %(to_date)s
		ORDER BY posting_date desc, posting_time desc, name desc;""".format(filters['customer']),
		filters,
		as_dict=True
	)
	for i in grs:
		i.v_type = 'Goods Receipt'

	return grs


def get_default_map(item):
	return frappe._dict({
	"opening": 0,
	"empty_opening": 0,
	"entries": [],
	"total_billed": 0,
	"total_delivered": 0,
	"total_returned": 0,
	"closing": 0,
	"empty_closing": 0,
	"item": item
	})


def initialize_voucher_maps(filters, vouchers):
	opening_map = frappe._dict()
	current_map = frappe._dict()

	for voucher in vouchers:
		active_map = opening_map if voucher.posting_date < filters['from_date'] else current_map

		if voucher.v_type == "Goods Receipt":
			if voucher.item_delivered:
				active_map.setdefault(get_item(voucher.item_delivered, filters),
									  get_default_map(voucher.item_delivered))
				active_map[get_item(voucher.item_delivered, filters)].entries.append(voucher)

			if (not voucher.item_delivered) or (
					voucher.item_delivered and voucher.item_received and
					get_base_item(voucher.item_delivered, filters) != get_base_item(voucher.item_received, filters)
			):
				active_map.setdefault(get_item(voucher.item_received, filters), get_default_map(voucher.item_received))
				active_map[get_item(voucher.item_received, filters)].entries.append(voucher)
		else:
			active_map.setdefault(get_item(voucher.item, filters), get_default_map(voucher.item))
			active_map[get_item(voucher.item, filters)].entries.append(voucher)

	return opening_map, current_map


def get_data_with_opening_closing(filters, opening_map, current_map):
	compute_closing(opening_map, filters)
	copy_closing_over_to_opening(opening_map, current_map)
	compute_closing(current_map, filters)

	return current_map


def compute_closing(active_map, filters):
	for item, voucher_map in active_map.items():
		last_entry_filled = flt(voucher_map.opening)
		last_entry_empty = flt(voucher_map.empty_opening)

		for entry in voucher_map.entries:
			billed, filled, empty = bill_filled_empty_status(entry, item, filters)

			billed = flt(billed)
			filled = flt(filled)
			empty = flt(empty)

			entry.filled = last_entry_filled + billed - filled
			entry.empty = last_entry_empty + filled - empty
			last_entry_filled = entry.filled
			last_entry_empty = entry.empty

			voucher_map.total_billed += billed
			voucher_map.total_delivered += filled
			voucher_map.total_returned += empty

		voucher_map.closing = voucher_map.opening + voucher_map.total_billed - voucher_map.total_delivered
		voucher_map.empty_closing = voucher_map.empty_opening + voucher_map.total_delivered - \
									voucher_map.total_returned


def copy_closing_over_to_opening(opening_map, current_map):
	for item, voucher_map in opening_map.items():
		current_map.setdefault(item, get_default_map(item))
		active_map_instance = current_map[item]
		active_map_instance.opening = voucher_map.closing
		active_map_instance.empty_opening = voucher_map.empty_closing


def bill_filled_empty_status(voucher, item, filters):
	item_base = get_base_item(item, filters)

	if voucher.v_type == 'Indent Invoice':
		return voucher.qty, 0, 0

	elif voucher.v_type == 'Goods Receipt':
		filled = empty = 0
		if voucher.item_delivered and\
			'FC' + item_base == normalize_lot_vot(voucher.item_delivered, filters) and\
			voucher.delivered_quantity:
			filled = voucher.delivered_quantity
		elif voucher.item_delivered and\
			'EC' + item_base == normalize_lot_vot(voucher.item_delivered, filters) and\
			 voucher.delivered_quantity:
			empty = -1 * voucher.delivered_quantity

		if voucher.item_received and\
			'FC' + item_base == normalize_lot_vot(voucher.item_received, filters)\
			and voucher.received_quantity:
			filled = -1 * voucher.received_quantity
		elif voucher.item_received and\
			'EC' + item_base == normalize_lot_vot(voucher.item_received, filters)\
			and voucher.received_quantity:
			empty = voucher.received_quantity
		return 0, filled, empty

	elif voucher.v_type == 'Stock Ledger Entry':
		filled = empty = 0
		if 'FC' + item_base == voucher.item and voucher.qty:
			filled = voucher.qty
		elif 'EC' + item_base == voucher.item and voucher.qty:
			empty = -1 * voucher.qty

		return 0, filled, empty


def get_opening_row(active_map):
	row = ["", active_map.item, "Opening"]
	row.append(active_map.opening if active_map.opening > 0 else 0)
	row.append(abs(active_map.opening) if active_map.opening < 0 else 0)
	row.extend(["", ""])
	row.append(active_map.empty_opening)
	return row


def get_closing_row_with_totals(active_map):
	rows = []
	rows.append(["", "", "Totals", active_map.total_billed, active_map.total_delivered, active_map.total_returned])

	row = [
		"",
		active_map.item,
		"Closing (Opening + Totals)",
		active_map.closing if active_map.closing > 0 else 0,
		abs(active_map.closing) if active_map.closing < 0 else 0,
		"",
		"",
		active_map.empty_closing
	]

	rows.append(row)

	return rows


def get_item(item, filters):
	return normalize_lot_vot(item, filters).replace('EC', 'FC')


def get_base_item(item, filters):
	return normalize_lot_vot(item, filters).replace('EC', '').replace('FC', '')


def normalize_lot_vot(item, filters):
	if cint(filters.lot_vot_bifurcate) == 0:
		item = item.replace('L', '')
	return item