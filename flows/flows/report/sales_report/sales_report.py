# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
	columns, data = ["x::", "y::", "z::"], get_data()
	return columns, data


def get_data():
	map = {}
	gatepass_to_salesperson = gatepass_issued_to_sales_person()
	gr_to_customers = gr_issued()

	for gatepass in gatepass_to_salesperson:
		map.setdefault(gatepass.item, frappe._dict({}))
		gp_dict = map[gatepass.item]

		gp_dict.setdefault(gatepass.gatepass_type, frappe._dict({'total': 0, 'gatepass': [], 'gr': []}))
		gp_dict[gatepass.gatepass_type].gatepass.append(gatepass)
		gp_dict[gatepass.gatepass_type].total += gatepass.qty

	for gr in gr_to_customers:
		if gr.item_delivered and gr.delivered_quantity:
			map.setdefault(gr.item_delivered, frappe._dict({}))
			gr_dict = map[gr.item_delivered]
			gr_dict.setdefault('Out', frappe._dict({'total': 0, 'gatepass': [], 'gr': []}))
			gr_dict['Out'].gr.append(gr)
			gr_dict['Out'].total += gr.delivered_quantity

		if gr.item_received and gr.received_quantity:
			map.setdefault(gr.item_received, frappe._dict({}))
			gr_dict = map[gr.item_received]
			gr_dict.setdefault('In', frappe._dict({'total': 0, 'gatepass': [], 'gr': []}))
			gr_dict['In'].gr.append(gr)
			gr_dict['In'].total += gr.received_quantity

	rows = []
	for item in map.keys():
		result_dict = map[item]
		for transit_type in result_dict.keys():
			rows.append([item, transit_type, result_dict[transit_type].total])
	return rows


def gatepass_issued_to_sales_person():
	sql = """
	SELECT g.driver AS driver,
			g.gatepass_type AS gatepass_type,
			i.item AS item,
			i.quantity AS qty
	FROM `tabGatepass` g, `tabGatepass Item` i
	WHERE g.docstatus = 1 AND
	g.driver IN (SELECT name FROM `tabSales Person`)
	AND i.parent = g.name AND posting_date = '2015-03-01';
	"""

	return frappe.db.sql(sql, as_dict=True)


def gr_issued():
	sql = """
	SELECT warehouse, customer, item_delivered, delivered_quantity, item_received, received_quantity
	FROM `tabGoods Receipt`
	WHERE docstatus = 1 AND
	posting_date = '2015-03-01'
	ORDER BY warehouse;
	"""
	return frappe.db.sql(sql, as_dict=True)