# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt


def execute(filters=None):
	data_map = get_data_map(filters)

	data = []

	for customer in sorted(data_map):
		for item in sorted(data_map[customer]):
			qty_dict = data_map[customer][item]
			data.append([
				customer,
				item,
			    qty_dict.opening,
				qty_dict.i_requested,
			    qty_dict.m_purchased,
				qty_dict.i_issued,
				qty_dict.m_delivered,
			    qty_dict.m_sold,
				qty_dict.closing,
			])

	return get_columns(), data


def get_columns():
	return [
		"Customer:Link/Customer:200",
		"Item:Link/Item:100",
	    "Opening:Float:150",
		"Indent Placed::",
		"Purchase:Float:",
		"Invoices Issued:Float:150",
		"Material Delivered:Float:150",
		"Sale:Float:",
		"Closing:Float:150",
	]


def get_invoices(filters):
	rs = frappe.db.sql(
		"""
		select posting_date, customer, item, qty
		from `tabIndent Invoice`
		where docstatus = 1
		and posting_date <= '{to_date}'
		order by posting_date, posting_time, name""".format(**filters),
		as_dict=1,
	    debug=True
	)

	# TODO find bug and remove hack
	for r in rs:
		r.posting_date = frappe.db.convert_to_simple_type(r.posting_date)

	return rs


def get_indents_which_are_not_invoiced_yet(filters):
	return frappe.db.sql(
		"""
		select indent.posting_date as posting_date, indent_item.customer, indent_item.item, indent_item.qty
		from `tabIndent Item` indent_item,
		`tabIndent` indent
		where indent_item.parent = indent.name
		and indent_item.docstatus != 2
		and indent.docstatus != 2
		and indent.posting_date <= '{to_date}'
		and indent_item.name not in (
			select ifnull(indent_item, '')
			from `tabIndent Invoice`
			where docstatus = 1
		)""".format(**filters),
		as_dict=1,
	    debug=True
	)


def get_goods_receipts(filters):
	return frappe.db.sql(
		"""
		select posting_date, customer, item_delivered as item, ifnull(delivered_quantity, 0) as qty
		from `tabGoods Receipt`
		where item_delivered like 'FC%'
		and docstatus = 1
		and posting_date <= '{to_date}';""".format(**filters),
		as_dict=1,
	    debug=True
	)


def get_sale_purchase_entries(filters):
	return frappe.db.sql(
		"""
		select posting_date, item, qty, from_customer, to_customer
		from `tabCross Sale Purchase`
		where docstatus != 2
		and posting_date <= '{to_date}';""".format(**filters),
		as_dict=1,
	    debug=True
	)


def get_data_map(filters):
	default = {
	"opening": 0,

	"i_requested": 0,
	"i_issued": 0,
	"m_purchased": 0,

	"m_delivered": 0,
	"m_sold": 0,

	"closing": 0,
	}

	current_map = {}
	opening_map = {}

	invoices = get_invoices(filters)
	indents = get_indents_which_are_not_invoiced_yet(filters)
	gr = get_goods_receipts(filters)
	csps = get_sale_purchase_entries(filters)

	for i in indents:
		active_map = opening_map if i.posting_date < filters['from_date'] else current_map
		active_map.setdefault(i.customer, {}).setdefault(i.item, frappe._dict(default))
		qty_dict = active_map[i.customer][i.item]
		qty_dict.i_requested += flt(i.qty)

	for i in invoices:
		active_map = opening_map if i.posting_date < filters['from_date'] else current_map
		active_map.setdefault(i.customer, {}).setdefault(i.item, frappe._dict(default))
		qty_dict = active_map[i.customer][i.item]
		qty_dict.i_issued += flt(i.qty)

	for i in csps:
		active_map = opening_map if i.posting_date < filters['from_date'] else current_map
		active_map.setdefault(i.from_customer, {}).setdefault(i.item, frappe._dict(default))
		active_map.setdefault(i.to_customer, {}).setdefault(i.item, frappe._dict(default))

		qty_dict = active_map[i.from_customer][i.item]
		qty_dict.m_sold += i.qty

		qty_dict = active_map[i.to_customer][i.item]
		qty_dict.m_purchased += i.qty

	for i in gr:
		active_map = opening_map if i.posting_date < filters['from_date'] else current_map
		active_map.setdefault(i.customer, {}).setdefault(i.item, frappe._dict(default))
		qty_dict = active_map[i.customer][i.item]
		qty_dict.m_delivered += flt(i.qty)

	active_map = opening_map
	for customer in sorted(active_map):
		for item in sorted(active_map[customer]):
			qty_dict = active_map[customer][item]
			diff = qty_dict.opening + qty_dict.i_requested + qty_dict.i_issued + qty_dict.m_purchased - qty_dict.m_delivered - qty_dict.m_sold
			qty_dict['closing'] = diff


	# Compute closing for opening map
	compute_closing(opening_map)

	# Copy over closing to opening of current map
	for customer in sorted(opening_map):
		for item in sorted(opening_map[customer]):
			qty_dict_from_opening_map = opening_map[customer][item]
			current_map.setdefault(customer, {}).setdefault(item, frappe._dict(default))
			qty_dict_from_current_map = current_map[customer][item]
			qty_dict_from_current_map.opening = qty_dict_from_opening_map.closing

	# Compute closing op current map
	compute_closing(current_map)

	return current_map



def compute_closing(active_map):
	for customer in sorted(active_map):
		for item in sorted(active_map[customer]):
			qty_dict = active_map[customer][item]
			diff = qty_dict.opening + qty_dict.i_requested + qty_dict.i_issued + qty_dict.m_purchased - qty_dict.m_delivered - qty_dict.m_sold
			qty_dict['closing'] = diff

	return active_map