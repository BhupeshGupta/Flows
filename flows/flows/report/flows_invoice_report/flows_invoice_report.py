# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cint


## Need report via transaction_date

def execute(filters=None):
	# Pull out config
	indent_invoice_settings = frappe.db.get_values_from_single(
		'*', None, 'Cross Sale Purchase Settings', as_dict=True)[0]
	filters.indent_invoice_settings = indent_invoice_settings

	data_map = get_data_map(filters)
	customer_map = get_customer_map()

	data = []

	for customer in sorted(data_map):
		for item in sorted(data_map[customer]):
			qty_dict = data_map[customer][item]
			data.append([
				customer_map.get(customer.strip(), frappe._dict({'customer_group': 'CNF'})).customer_group,
				customer,
				item,
			    int(qty_dict.opening),
				int(qty_dict.i_requested),
			    int(qty_dict.m_purchased),
				int(qty_dict.i_issued),
				int(qty_dict.m_delivered),
			    int(qty_dict.m_sold),
				int(qty_dict.closing),
			])

	data = sorted(data, key = lambda x: (x[0], x[1]))

	return get_columns(), data


def get_columns():
	return [
		"Group:Link/Customer Group:100",
		"Customer:Link/Customer:250",
		"Item:Link/Item:75",
	    "Opening:Float:85",
		"Indent Placed:Float:85",
		"Purchase:Float:85",
		"Invoices Issued:Float:85",
		"Material Delivered:Float:85",
		"Sale:Float:85",
		"Closing:Float:85",
	]


def get_invoices(filters):
	rs = frappe.db.sql(
		"""
		select transaction_date as posting_date, customer, item, qty,
		sub_contracted, supplier, cross_sold
		from `tabIndent Invoice`
		where docstatus = 1
		and transaction_date <= '{to_date}'
		order by transaction_date, posting_time, name""".format(**filters),
		as_dict=1,
	)

	# TODO find bug and remove hack
	for r in rs:
		r.posting_date = frappe.db.convert_to_simple_type(r.posting_date)

	return rs


def get_indents_which_are_not_invoiced_yet(filters):
	return frappe.db.sql(
		"""
		select indent.posting_date as posting_date, indent_item.customer, indent_item.item, indent_item.qty,
		indent_item.cross_sold
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
	)


def get_sale_entries(filters):
	return frappe.db.sql(
		"""
		select posting_date, customer, item, qty
		from `tabCross Sale`
		where docstatus = 1
		and posting_date <= '{to_date}';""".format(**filters),
		as_dict=1,
	)

def get_payment_receipts(filters):
	return frappe.db.sql(
		"""
		select posting_date, item, qty
		from `tabPayment Receipt`
		where docstatus = 1 and
	    transaction_type in ("Refill", "New Connection") and
	    posting_date <= '{to_date}';
		""".format(**filters),
	    as_dict=True
	)

def get_patch_vouchers(filters):
	return frappe.db.sql(
		"""
		select pv.posting_date as posting_date, pi.item as item, pi.qty as qty,
		pi.to_customer as to_customer, pi.invoice_customer as invoice_customer
		from `tabPatch Item` pi, `tabPatch Voucher` pv
		where pv.docstatus = 1 and
		pv.name = pi.parent and
	    pv.posting_date <= '{to_date}';
		""".format(**filters),
	    as_dict=True
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
	cs = get_sale_entries(filters)
	pr = get_payment_receipts(filters)
	pv = get_patch_vouchers(filters)

	# a/c as suggested by cross sale purchase settings, used to balance VK sale/purchase
	balance_customer_account = filters.indent_invoice_settings.customer_account

	for i in indents:
		active_map = opening_map if i.posting_date < filters['from_date'] else current_map
		if cint(i.cross_sold) == 0:
			active_map.setdefault(i.customer, {}).setdefault(get_item(i.item, filters), frappe._dict(default))
			qty_dict = active_map[i.customer][get_item(i.item, filters)]
		else:
			active_map.setdefault(balance_customer_account, {}).setdefault(get_item(i.item, filters), frappe._dict(default))
			qty_dict = active_map[balance_customer_account][get_item(i.item, filters)]
		qty_dict.i_requested += flt(i.qty)

	for i in invoices:
		active_map = opening_map if i.posting_date < filters['from_date'] else current_map
		active_map.setdefault(i.customer, {}).setdefault(get_item(i.item, filters), frappe._dict(default))
		qty_dict = active_map[i.customer][get_item(i.item, filters)]
		qty_dict.i_issued += flt(i.qty)

		# Subcontracted, add to supplier's sale
		if cint(i.sub_contracted) == 1:
			active_map.setdefault(i.supplier, {}).setdefault(get_item(i.item, filters), frappe._dict(default))
			qty_dict = active_map[i.supplier][get_item(i.item, filters)]
			qty_dict.m_sold += i.qty

		# Cross Sold
		if cint(i.cross_sold) == 1:
			# Sold by customer
			active_map.setdefault(i.customer, {}).setdefault(get_item(i.item, filters), frappe._dict(default))
			qty_dict = active_map[i.customer][get_item(i.item, filters)]
			qty_dict.m_sold += flt(i.qty)

			# Purchased by Cross Sale Purchase balance account
			active_map.setdefault(balance_customer_account, {}).setdefault(get_item(i.item, filters), frappe._dict(default))
			qty_dict = active_map[balance_customer_account][get_item(i.item, filters)]
			qty_dict.m_purchased += i.qty

	for i in cs:
		active_map = opening_map if i.posting_date < filters['from_date'] else current_map
		# Sold by Cross Sale Purchase balance account
		active_map.setdefault(balance_customer_account, {}).setdefault(get_item(i.item, filters), frappe._dict(default))
		qty_dict = active_map[balance_customer_account][get_item(i.item, filters)]
		qty_dict.m_sold += i.qty

		# Purchased by customer
		active_map.setdefault(i.customer, {}).setdefault(get_item(i.item, filters), frappe._dict(default))
		qty_dict = active_map[i.customer][get_item(i.item, filters)]
		qty_dict.m_purchased += flt(i.qty)

	for i in gr:
		active_map = opening_map if i.posting_date < filters['from_date'] else current_map
		active_map.setdefault(i.customer, {}).setdefault(get_item(i.item, filters), frappe._dict(default))
		qty_dict = active_map[i.customer][get_item(i.item, filters)]
		qty_dict.m_delivered += flt(i.qty)

	for i in pr:
		active_map = opening_map if i.posting_date < filters['from_date'] else current_map
		active_map.setdefault(balance_customer_account, {}).setdefault(get_item(i.item, filters), frappe._dict(default))
		qty_dict = active_map[balance_customer_account][get_item(i.item, filters)]
		qty_dict.m_delivered += flt(i.qty)

	for i in pv:
		active_map = opening_map if i.posting_date < filters['from_date'] else current_map
		active_map.setdefault(i.invoice_customer, {}).setdefault(get_item(i.item, filters), frappe._dict(default))
		active_map.setdefault(i.to_customer, {}).setdefault(get_item(i.item, filters), frappe._dict(default))

		qty_dict = active_map[i.to_customer][get_item(i.item, filters)]
		qty_dict.i_issued += flt(i.qty)

		qty_dict = active_map[i.invoice_customer][get_item(i.item, filters)]
		qty_dict.i_issued -= flt(i.qty)

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


def get_customer_map():
	result_map = frappe._dict({})

	list_of_map = frappe.db.sql("""
	SELECT name, customer_group from `tabCustomer`;
	""", as_dict=True);

	for instance in list_of_map:
		result_map[instance.name.strip()] = instance

	return result_map

def get_item(item, filters):
	if cint(filters.lot_vot_bifurcate) == 0:
		return item.replace('L','')
	return item