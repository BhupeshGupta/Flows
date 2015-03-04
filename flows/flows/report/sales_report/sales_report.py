# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	columns, data = [
		{
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Data",
			"options": "",
			"width": 300,
		    "is_tree": True
		},
	    {
			"fieldname": "total",
			"label": _("Total"),
			"fieldtype": "Float",
			"options": "",
			"width": 300
		},
	], get_data(filters)
	return columns, data


def get_data(filters):
	map = {}
	gatepass_to_salesperson = gatepass_issued_to_sales_person(filters)
	gr_to_customers = gr_issued(filters)

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
			rows.append({
			'account': ' '.join((item, transit_type)),
			'account_name': ' '.join((item, transit_type)),
			'total': result_dict[transit_type].total,
			'parent_account': None
			})
			for gr in result_dict[transit_type].gr:
				rows.append({
				'account': gr.customer,
				'account_name': gr.customer,
				'total': gr['delivered_quantity' if gr.item_delivered and filters['item_code'] in gr.item_delivered else 'item_received'],
				'parent_account': ' '.join((item, transit_type))
				})

	return rows


def gatepass_issued_to_sales_person(filters=None):
	sql = """
	SELECT g.driver AS driver,
	g.gatepass_type AS gatepass_type,
	i.item AS item,
	i.quantity AS qty
	FROM `tabGatepass` g, `tabGatepass Item` i
	WHERE g.docstatus = 1 AND
	g.driver IN (SELECT name FROM `tabSales Person`)
	AND i.parent = g.name
	AND i.item like '%{item_code}'
	AND posting_date between '{from_date}' and '{to_date}'
	""".format(**filters)

	return frappe.db.sql(sql, as_dict=True, debug=True)


def gr_issued(filters=None):
	sql = """
	SELECT warehouse, customer, item_delivered, delivered_quantity, item_received, received_quantity
	FROM `tabGoods Receipt`
	WHERE docstatus = 1 AND
	posting_date between '{from_date}' and '{to_date}'
	AND (item_delivered like '%{item_code}' OR item_received like '%{item_code}')
	ORDER BY warehouse;
	""".format(**filters)
	return frappe.db.sql(sql, as_dict=True, debug=True)