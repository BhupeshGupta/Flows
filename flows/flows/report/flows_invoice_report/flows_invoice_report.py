# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt


def execute(filters=None):
	data_map = get_data_map()

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


def get_invoices():
	return frappe.db.sql(
		"""
		select customer, item, qty
		from `tabIndent Invoice`
		where docstatus = 1
		order by posting_date, posting_time, name""",
		as_dict=1
	)


def get_indents_which_are_not_invoiced_yet():
	return frappe.db.sql(
		"""
		select customer, item, qty
		from `tabIndent Item`
		where docstatus != 2
		and name not in (
			select indent_item
			from `tabIndent Invoice`
			where docstatus = 1
		)""",
		as_dict=1
	)


def get_goods_receipts():
	return frappe.db.sql(
		"""
		select customer, item_delivered as item, ifnull(delivered_quantity, 0) as qty
		from `tabGoods Receipt`
		where item_delivered != '' and docstatus = 1;""",
		as_dict=1
	)


def get_sale_purchase_entries():
	return frappe.db.sql(
		"""
		select item, qty, from_customer, to_customer
		from `tabCross Sale Purchase`
		where docstatus != 2;""",
		as_dict=1
	)


def get_data_map():
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

	invoices = get_invoices()
	indents = get_indents_which_are_not_invoiced_yet()
	gr = get_goods_receipts()
	csps = get_sale_purchase_entries()

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