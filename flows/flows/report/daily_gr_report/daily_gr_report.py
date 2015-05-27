# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
	return get_columns(filters), get_data(filters)


def get_columns(filters):
	return [
		"Customer:Link/Customer:250",
		"19 Kg:Int:100",
		"35 Kg:Int:100",
		"47.5 Kg:Int:100"
	]


def get_data(filters):
	rows = []

	totals_map = {'FC19': 0, 'FC35': 0, 'FC47.5': 0}
	for gr in get_grs(filters):
		gr.item_delivered = map_item(gr.item_delivered)

		rows.append([
			gr.customer,
			gr.qty if 'FC19' in gr.item_delivered else '',
			gr.qty if 'FC35' in gr.item_delivered else '',
			gr.qty if 'FC47.5' in gr.item_delivered else '',
		])

		totals_map[gr.item_delivered] += gr.qty

	rows.append([
		"Totals",
		totals_map['FC19'],
		totals_map['FC35'],
		totals_map['FC47.5']
	])

	return rows


def get_grs(filters):
	return frappe.db.sql("""
	SELECT customer, item_delivered, sum(delivered_quantity) AS qty
	FROM `tabGoods Receipt`
	WHERE docstatus = 1
	AND posting_date BETWEEN "{from_date}" AND "{to_date}"
	AND cancelled = 0
	AND ifnull(item_delivered, '') != ''
	AND item_delivered like 'FC%'
	GROUP BY customer, item_delivered
	ORDER BY customer;""".format(**filters), as_dict=True)


def map_item(item):
	return item.replace('L', '')
