# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint

items = ['FC19', 'FC35', 'FC47.5', 'FC47.5L', 'EC19', 'EC35', 'EC47.5', 'EC47.5L']
data_c_length = 9


def execute(filters=None):
	data = get_data(filters)
	return get_columns(filters), data


def get_columns(filters):
	row = [
		"ID::",
		"Date:Date:",
		"Customer:Data:200",
		"Warehouse::150",
		"Item Delivered::",
		"Delivered Qty:Int:",
		"Item Received::",
		"Received Qty:Int:",
		"Cancelled::"]

	if cint(filters.show_draft_entries) == 1:
		row.append("Docstatus::")

	row.extend(
		[
			"Row Value::1",
			"Row Type::1"
		])

	return row


def get_grs(filters):
	condition = "docstatus {}".format("= 1" if cint(filters.show_draft_entries) == 0 else "!= 2")
	return frappe.db.sql("""
	SELECT * FROM `tabGoods Receipt`
	WHERE {doc_condition}
	AND posting_date BETWEEN "{from_date}" AND "{to_date}"
	ORDER BY goods_receipt_number
	""".format(doc_condition=condition, **filters), as_dict=True)


def get_data(filters):
	grs = get_grs(filters)

	rows = []
	warehouse_wise_gr = {}

	gr_book = gr_start = gr_end = 0

	for gr in grs:
		# Compute relative GR book serial for color coding, assumes book is of 50 leaves
		gr.goods_receipt_number = cint(gr.goods_receipt_number)
		if not (gr_start <= gr.goods_receipt_number <= gr_end):
			gr_book += 1
			diff = gr.goods_receipt_number % 50
			gr_start = gr.goods_receipt_number - diff + 1
			gr_end = gr_start - 1 + 50

		row = [
			gr.goods_receipt_number,
			gr.posting_date,
			gr.customer,
			gr.warehouse,
			gr.item_delivered,
			gr.delivered_quantity,
			gr.item_received,
			gr.received_quantity,
			gr.cancelled,
		]

		if cint(filters.show_draft_entries) == 1:
			row.append(gr.docstatus)

		row.extend([
			gr_book,
			"GR"
		])

		rows.append(row)

		# If cancelled, skip totals
		if cint(gr.cancelled) == 1:
			continue

		warehouse_wise_gr.setdefault(gr.warehouse, item_totals_map())

		if gr.item_delivered:
			warehouse_wise_gr[gr.warehouse]["delivered"].setdefault(gr.item_delivered, 0)
			warehouse_wise_gr[gr.warehouse]["delivered"][gr.item_delivered] += gr.delivered_quantity

		if gr.item_received:
			warehouse_wise_gr[gr.warehouse]["received"].setdefault(gr.item_received, 0)
			warehouse_wise_gr[gr.warehouse]["received"][gr.item_received] += gr.received_quantity

	rows.extend(get_total_rows(warehouse_wise_gr))
	rows.extend(get_grand_totals_rows(warehouse_wise_gr))

	return rows


def item_totals_map():
	return frappe._dict({
	"delivered": frappe._dict({}),
	"received": frappe._dict({})
	})


def get_total_rows(warehouse_wise_gr):
	rows = []

	# rd -> received delivered
	for warehouse, rd_map in warehouse_wise_gr.items():
		for item in items:
			data_append = False
			row = ["", "", "Totals", warehouse]

			if item in rd_map["delivered"]:
				row.extend([item, rd_map["delivered"][item]])
				data_append = True
			else:
				row.extend(["", ""])

			conjugate_item = item_conjugate(item)
			if conjugate_item in rd_map["received"]:
				row.extend([conjugate_item, rd_map["received"][conjugate_item]])
				data_append = True
			else:
				row.extend(["", ""])

			if data_append:
				row.extend(["", "", "Total"])
				rows.append(row)

	return rows


def get_grand_totals_rows(warehouse_wise_gr):
	grand_total_map = item_totals_map()
	rows = []

	for warehouse, rd_map in warehouse_wise_gr.items():
		for rd, item_map in rd_map.items():
			for item, qty in item_map.items():
				grand_total_map[rd].setdefault(item, 0)
				grand_total_map[rd][item] += qty

	for item in items:
		row = ["", "", "Grand Totals", ""]
		row_append = False

		if item in grand_total_map["delivered"]:
			row.extend([item, grand_total_map["delivered"][item]])
			row_append = True
		else:
			row.extend(["", ""])

		conjugate_item = item_conjugate(item)
		if conjugate_item in grand_total_map["received"]:
			row.extend([conjugate_item, grand_total_map["received"][conjugate_item]])
			row_append = True
		else:
			row.extend(["", ""])

		if row_append:
			row.extend(["", "", "Grand Total"])
			rows.append(row)

	return rows


def item_conjugate(item):
	if 'FC' in item:
		return item.replace('FC', 'EC')
	else:
		return item.replace('EC', 'FC')