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
		"Date 1:Date:100",
		"Voucher Type 1::120",
		"Voucher No 1:Dynamic Link/Voucher Type:160",

		"Qty Delivered:Float:100",
		"Empty Received:Float:100",
		"Empty Pending:Float:",

		"::200",

		"Date:Date:100",
		"Voucher Type::120",
		"Voucher No:Dynamic Link/Voucher Type:160",
		"Billed Qty:Float:100",
		"Filled Balance:Float:",
		"Remarks::400",
	]


def get_data(filters):
	data = []

	stock_ledger_entries = get_sl_entries(filters)
	indent_invoices = get_invoices_entries(filters)
	opening_grs = get_opening_gr(filters)
	cross_sale = get_cross_sale_vouchers(filters)
	stv = get_stock_transfer_vouchers(filters)
	sci = get_subcontracted_invoices(filters)
	vouchers = stock_ledger_entries + indent_invoices + opening_grs + cross_sale + stv + sci
	vouchers = sorted(vouchers, key=lambda k: k['posting_date'])

	opening_map, current_map = initialize_voucher_maps(filters, vouchers)

	current_map = get_data_with_opening_closing(filters, opening_map, current_map)

	if '' in current_map:
		current_map.pop('')

	for item in sorted(current_map.keys()):
		map = current_map[item]

		data.append(get_opening_row(map))

		for voucher in map.entries:
			billed, delivered, received = bill_filled_empty_status(voucher, item, filters)
			row = []

			row.extend(
					[
						voucher.get("posting_date"),
						voucher.voucher_type if voucher.v_type == 'Stock Ledger Entry' else voucher.v_type,
						voucher.voucher_no if voucher.v_type == 'Stock Ledger Entry' else voucher.get("name"),
						delivered,
						received,
						voucher.empty
					] if delivered or received else [
						"",
						"",
						"",
						"",
						"",
						""
					]
			)

			row.extend([""])

			row.extend(
					[
						voucher.get("posting_date"),
						voucher.voucher_type if voucher.v_type == 'Stock Ledger Entry' else voucher.v_type,
						voucher.voucher_no if voucher.v_type == 'Stock Ledger Entry' else voucher.get("name"),
						billed,
						voucher.filled,
						""
					] if billed else [
						"",
						"",
						"",
						"",
						voucher.filled,
						""
					]
			)

			data.append(row)

		data.extend(get_closing_row_with_totals(map))

		data.append(["", "", "", "", "", ""])

	return data


def get_sle_conditions(filters):
	conditions = []
	conditions.append('warehouse like "{}%%"'.format(filters.customer))
	return "and {}".format(" and ".join(conditions)) if conditions else ""


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
			SELECT name, transaction_date as posting_date, customer, ship_to, item, qty
			FROM `tabIndent Invoice`
			WHERE docstatus = 1 AND
			(customer="{0}" or ship_to="{0}") AND
			cross_sold = 0 AND
			transaction_date <= %(to_date)s
			ORDER BY transaction_date desc, posting_time desc, name desc;""".format(filters['customer']),
			filters,
			as_dict=True
	)

	vouchers = []

	for i in indent_invoices:
		i.v_type = 'Indent Invoice'
		method = 'opening_computation_method' if i.posting_date < filters['from_date'] else 'current_computation_method'
		if filters[method] == 'Ship To':
			i.customer = i.ship_to
		if i.customer == filters['customer']:
			vouchers.append(i)

	return vouchers


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


def get_cross_sale_vouchers(filters):
	# posting_date
	cross_sale = frappe.db.sql(
			"""
			SELECT name, posting_date, customer, item, qty
			FROM `tabCross Sale`
			WHERE docstatus = 1 AND
			customer="{}" AND
			posting_date <= %(to_date)s
			ORDER BY posting_date desc, name desc;""".format(filters['customer']),
			filters,
			as_dict=True
	)
	for i in cross_sale:
		i.v_type = 'Cross Sale'

	return cross_sale


def get_stock_transfer_vouchers(filters):
	# posting_date
	st = frappe.db.sql(
			"""
			SELECT name, posting_date, from_customer, to_customer, item, qty
			FROM `tabStock Transfer Voucher`
			WHERE docstatus = 1 AND
			(from_customer="{0}" OR to_customer="{0}") AND
			posting_date <= %(to_date)s
			ORDER BY posting_date desc, name desc;""".format(filters['customer']),
			filters,
			as_dict=True
	)
	for i in st:
		i.v_type = 'Stock Transfer Voucher'

		i.customer = filters['customer']
		if i.from_customer == filters['customer']:
			i.qty *= -1

	return st


def get_subcontracted_invoices(filters):
	# posting_date
	sci = frappe.db.sql(
			"""
			SELECT name, posting_date, customer, item, quantity as qty
			FROM `tabSubcontracted Invoice`
			WHERE docstatus = 1 AND
			customer="{0}" AND
			posting_date <= %(to_date)s
			ORDER BY posting_date desc, name desc;""".format(filters['customer']),
			filters,
			as_dict=True
	)
	for i in sci:
		i.v_type = 'Subcontracted Invoice'

	return sci


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

			if get_base_item(voucher.item_delivered, filters) != get_base_item(voucher.item_received, filters):
				active_map.setdefault(get_item(voucher.item_received, filters), get_default_map(voucher.item_received))
				active_map[get_item(voucher.item_received, filters)].entries.append(voucher)
		else:
			active_map.setdefault(get_item(voucher.item, filters), get_default_map(voucher.item))
			active_map[get_item(voucher.item, filters)].entries.append(voucher)

	frappe.msgprint(active_map)

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
		if voucher.item_delivered and 'FC' + item_base == get_lot_vot_strip(voucher.item_delivered,
																			filters) and voucher.delivered_quantity:
			filled = voucher.delivered_quantity
		elif voucher.item_delivered and 'EC' + item_base == get_lot_vot_strip(voucher.item_delivered,
																			  filters) and voucher.delivered_quantity:
			empty = -1 * voucher.delivered_quantity

		if voucher.item_received and 'FC' + item_base == get_lot_vot_strip(voucher.item_received,
																		   filters) and voucher.received_quantity:
			filled = -1 * voucher.received_quantity
		elif voucher.item_received and 'EC' + item_base == get_lot_vot_strip(voucher.item_received,
																			 filters) and voucher.received_quantity:
			empty = voucher.received_quantity
		return 0, filled, empty

	elif voucher.v_type == 'Stock Ledger Entry':
		filled = empty = 0
		if 'FC' + item_base == get_lot_vot_strip(voucher.item, filters) and voucher.qty:
			filled = voucher.qty
		elif 'EC' + item_base == get_lot_vot_strip(voucher.item, filters) and voucher.qty:
			empty = -1 * voucher.qty

		return 0, filled, empty

	elif voucher.v_type == 'Cross Sale':
		return voucher.qty, 0, 0

	elif voucher.v_type == 'Stock Transfer Voucher':
		return voucher.qty, 0, 0

	elif voucher.v_type == 'Subcontracted Invoice':
		return voucher.qty, 0, 0


def get_opening_row(active_map):
	row = ["", active_map.item, "Opening"]

	row.append(abs(active_map.opening) if active_map.opening < 0 else 0)
	row.append("")
	row.append(active_map.empty_opening)
	row.append("")

	row.append("")
	row.extend([active_map.item, "Opening"])
	row.append(active_map.opening if active_map.opening > 0 else 0)
	row.extend(["", ""])

	return row


def get_closing_row_with_totals(active_map):
	rows = []
	rows.append([
		"", "", "Totals", active_map.total_delivered, active_map.total_returned, "", "",
		"", "", "Totals", active_map.total_billed, "", "", ""
	])

	row = [
		"",
		active_map.item,
		"Closing (Opening + Totals)",
		# Qty Delivered
		abs(active_map.closing) if active_map.closing < 0 else 0,
		"",
		active_map.empty_closing,

		"",

		"",
		active_map.item,
		"Closing (Opening + Totals)",
		active_map.closing if active_map.closing > 0 else 0,
		"",
		"",
	]

	rows.append(row)

	return rows


def get_item(item, filters):
	if not item:
		return ''

	if cint(filters.lot_vot_bifurcate) == 0:
		item = item.replace('L', '')

	return item.replace('EC', 'FC')


def get_base_item(item, filters):
	if not item:
		return ''

	if cint(filters.lot_vot_bifurcate) == 0:
		item = item.replace('L', '')

	return item.replace('EC', '').replace('FC', '')


def get_lot_vot_strip(item, filters):
	if cint(filters.lot_vot_bifurcate) == 0:
		item = item.replace('L', '')
	return item
