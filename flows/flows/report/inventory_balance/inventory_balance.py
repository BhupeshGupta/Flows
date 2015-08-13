# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


calc_row = {
	'op_C19': 0,
	'diff_C19': 0,
	'cl_C19': 0,
	'op_C35': 0,
	'diff_C35': 0,
	'cl_C35': 0,
	'op_C47.5': 0,
	'diff_C47.5': 0,
	'cl_C47.5': 0,
	'op_C47.5L': 0,
	'diff_C47.5L': 0,
	'cl_C47.5L': 0,
}


def execute(filters=None):
	return get_columns(filters), get_data(filters)


def get_data(filters):
	warehouses, warehouses_by_name = get_warehouses(filters)
	populate_data(filters, warehouses, warehouses_by_name)
	totals = aggregate_date_into_parents(filters, warehouses, warehouses_by_name)
	data = [warehouses_by_name[x.warehouse] for x in warehouses]
	data.extend([{}, totals])
	return data


def get_columns(filters):
	def get_op_diff_cl(obj):
		op = obj.copy()
		op['fieldname'] = 'op_' + op['fieldname']
		op['label'] = 'OP ' + op['label']

		diff = obj.copy()
		diff['fieldname'] = 'diff_' + diff['fieldname']
		diff['label'] = 'Diff ' + diff['label']

		cl = obj.copy()
		cl['fieldname'] = 'cl_' + cl['fieldname']
		cl['label'] = 'CL ' + cl['label']

		return [
			op,
			diff,
			cl
		]

	columns = [
		{
		"fieldname": "warehouse",
		"label": "Warehouse",
		"fieldtype": "Link",
		"options": "Warehouse",
		"width": 200
		}
	]

	columns.extend(get_op_diff_cl({
	"fieldname": "C19",
	"label": "19 Kg",
	"fieldtype": "Int",
	"width": 80
	}))
	columns.append({})
	columns.extend(get_op_diff_cl({
	"fieldname": "C35",
	"label": "35 Kg",
	"fieldtype": "Int",
	"width": 80
	}))
	columns.append({})
	columns.extend(get_op_diff_cl({
	"fieldname": "C47.5",
	"label": "47.5 VOT",
	"fieldtype": "Int",
	"width": 80
	}))
	columns.append({})
	columns.extend(get_op_diff_cl({
	"fieldname": "C47.5L",
	"label": "47.5 LOT",
	"fieldtype": "Int",
	"width": 80
	}))

	return columns


def aggregate_date_into_parents(filters, warehouses, warehouses_by_name):
	totals = {
	'warehouse': 'Totals',
	'parent_warehouse': None,
	'indent': 0,
	}
	totals.update(calc_row.copy())
	for warehouse_obj in reversed(warehouses):
		warehouse = warehouses_by_name[warehouse_obj.warehouse]
		for item in ['C19', 'C35', 'C47.5', 'C47.5L']:
			parent_warehouse = warehouses_by_name[warehouse.parent_warehouse] if warehouse.parent_warehouse else totals
			for x in ['op_', 'diff_', 'cl_']:
				parent_warehouse[x+item] += warehouse[x+item]
	return totals


def populate_data(filters, warehouses, warehouses_by_name):
	data = frappe.db.sql("""
	SELECT warehouse, replace(replace(item_code, 'FC', 'C'), 'EC', 'C') AS item,
	sum(actual_qty) AS qty
	FROM `tabStock Ledger Entry`
	WHERE posting_date < '{from_date}'
	GROUP BY warehouse, item;
	""".format(**filters), as_dict=True)

	for d in data:
		warehouses_by_name[d.warehouse]['op_{}'.format(d.item)] = d.qty

	data = frappe.db.sql("""
	SELECT warehouse, replace(replace(item_code, 'FC', 'C'), 'EC', 'C') AS item,
	sum(actual_qty) AS qty
	FROM `tabStock Ledger Entry`
	WHERE posting_date <= '{to_date}'
	GROUP BY warehouse, item;
	""".format(**filters), as_dict=True)

	for d in data:
		warehouses_by_name[d.warehouse]['cl_{}'.format(d.item)] = d.qty

	for w in warehouses_by_name.values():
		for item in ['C19', 'C35', 'C47.5', 'C47.5L']:
			w['diff_{}'.format(item)] = w['cl_{}'.format(item)] - w['op_{}'.format(item)]


def get_warehouses(filters):
	warehouse_list = frappe.db.sql("""
	SELECT name AS warehouse,
	parent_warehouse
	FROM `tabWarehouse`
	ORDER BY lft""", as_dict=True)


	def indent_warehouses(warehouses):
		parent_children_map = {}
		warehouses_by_name = {}
		filtered_warehouses = []
		for d in warehouses:
			warehouses_by_name[d.warehouse] = d
			parent_children_map.setdefault(d.parent_warehouse or None, []).append(d)

		def add_to_list(parent, level):
			for child in (parent_children_map.get(parent) or []):
				child.indent = level
				child.update(calc_row.copy())
				filtered_warehouses.append(child)
				add_to_list(child.warehouse, level + 1)

		add_to_list(None, 0)

		return filtered_warehouses, warehouses_by_name

	return indent_warehouses(warehouse_list)

