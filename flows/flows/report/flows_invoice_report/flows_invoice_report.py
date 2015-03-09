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
				qty_dict.i_requested,
			    qty_dict.m_purchased,
				qty_dict.i_issued,
				qty_dict.m_delivered,
			    qty_dict.m_sold,
				qty_dict.i_to_issue,
				qty_dict.m_to_deliver
			])

	return get_columns(), data


def get_columns():
	return [
		"Customer:Link/Customer:200",
		"Item:Link/Item:100",
		"Indent Placed::",
		"Purchase:Float:",
		"Invoices Issued:Float:150",
		"Material Delivered:Float:150",
		"Sale:Float:",
		"Invoices To Issue:Float:150",
		"Material To Deliver:Float:150"
	]


def get_invoices(filters):
	return frappe.db.sql(
		"""
		select customer, item, qty
		from `tabIndent Invoice`
		where docstatus = 1
		and posting_date <= '{to_date}'
		order by posting_date, posting_time, name""".format(**filters),
		as_dict=1,
	    debug=True
	)


def get_indents_which_are_not_invoiced_yet(filters):
	return frappe.db.sql(
		"""
		select indent_item.customer, indent_item.item, indent_item.qty
		from `tabIndent Item` indent_item,
		`tabIndent` indent
		where indent_item.parent = indent.name
		and indent_item.docstatus != 2
		and indent.docstatus != 2
		and indent.posting_date <= '{to_date}'
		and indent_item.name not in (
			select indent_item
			from `tabIndent Invoice`
			where docstatus = 1
		)""".format(**filters),
		as_dict=1,
	    debug=True
	)


def get_goods_receipts(filters):
	return frappe.db.sql(
		"""
		select customer, item_delivered as item, ifnull(delivered_quantity, 0) as qty
		from `tabGoods Receipt`
		where item_delivered != ''
		and docstatus = 1
		and posting_date <= '{to_date}';""".format(**filters),
		as_dict=1,
	    debug=True
	)


def get_sale_purchase_entries(filters):
	return frappe.db.sql(
		"""
		select item, qty, from_customer, to_customer
		from `tabCross Sale Purchase`
		where docstatus != 2
		and posting_date <= '{to_date}';""".format(**filters),
		as_dict=1,
	    debug=True
	)


def get_data_map(filters):
	default = {
	"i_requested": 0,
	"i_issued": 0,
	"m_purchased": 0,

	"m_delivered": 0,
	"m_sold": 0,

	"i_to_issue": 0,
	"m_to_deliver": 0
	}

	map = {}

	invoices = get_invoices(filters)
	indents = get_indents_which_are_not_invoiced_yet(filters)
	gr = get_goods_receipts(filters)
	csps = get_sale_purchase_entries(filters)

	for i in indents:
		map.setdefault(i.customer, {}).setdefault(i.item, frappe._dict(default))
		qty_dict = map[i.customer][i.item]
		qty_dict.i_requested += flt(i.qty)

	for i in invoices:
		map.setdefault(i.customer, {}).setdefault(i.item, frappe._dict(default))
		qty_dict = map[i.customer][i.item]
		qty_dict.i_issued += flt(i.qty)

	for i in csps:
		map.setdefault(i.from_customer, {}).setdefault(i.item, frappe._dict(default))
		map.setdefault(i.to_customer, {}).setdefault(i.item, frappe._dict(default))

		qty_dict = map[i.from_customer][i.item]
		qty_dict.m_sold += i.qty

		qty_dict = map[i.to_customer][i.item]
		qty_dict.m_purchased += i.qty

	for i in gr:
		map.setdefault(i.customer, {}).setdefault(i.item, frappe._dict(default))
		qty_dict = map[i.customer][i.item]
		qty_dict.m_delivered += flt(i.qty)

	for customer in sorted(map):
		for item in sorted(map[customer]):
			qty_dict = map[customer][item]
			diff = qty_dict.i_requested + qty_dict.i_issued + qty_dict.m_purchased - qty_dict.m_delivered - qty_dict.m_sold
			qty_dict['m_to_deliver' if diff > 0 else 'i_to_issue'] = abs(diff)

	return map