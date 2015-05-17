# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint

def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data


def get_columns(filters):
	return ["Date:Date:100", "Voucher Type::120", "Voucher No:Dynamic Link/Voucher Type:160",
	        "Debit:Float:100", "Credit:Float:100", "Remarks::400"]


def get_data(filters):
	data = []

	stock_ledger_entries = get_sl_entries(filters)
	indent_invoices = get_invoices_entries(filters)
	opening_grs = get_opening_gr(filters)
	vouchers = stock_ledger_entries + indent_invoices + opening_grs
	vouchers = sorted(vouchers, key=lambda k: k['posting_date'])

	opening_map, current_map = initialize_voucher_maps(filters, vouchers)

	current_map = get_data_with_opening_closing(filters, opening_map, current_map)

	for item in sorted(current_map.keys()):
		map = current_map[item]

		debit, credit = get_credit_balance_in_debit_credit_split(map.opening)
		data.append(["", item, "Opening", debit, credit, ""])

		for voucher in map.entries:
			debit, credit = debit_or_credit_voucher(voucher)
			data.append([
				voucher.get("posting_date"),
			    voucher.voucher_type if voucher.v_type == 'Stock Ledger Entry' else voucher.v_type,
			    voucher.voucher_no  if voucher.v_type == 'Stock Ledger Entry' else voucher.get("name"),
				debit,
			    credit,
			    ""
			])

		data.append(["", "", "Totals", map.total_debit, map.total_credit, ""])

		debit, credit = get_credit_balance_in_debit_credit_split(map.closing)
		data.append(["", item, "Closing (Opening + Totals)", debit, credit, ""])

		data.append(["", "", "", "", "", ""])
		data.append(["", "", "", "", "", ""])

	return data


def get_sle_conditions(filters):
	conditions = []
	# item_conditions = get_item_conditions(filters)
	# if item_conditions:
	# 	conditions.append("""item_code in (select name from tabItem
	# 		{item_conditions})""".format(item_conditions=item_conditions))
	# if filters.get("warehouse"):
	# 	conditions.append("warehouse=%(warehouse)s")

	conditions.append('warehouse like "{}%%"'.format(filters.customer))

	if filters.get("voucher_no"):
		conditions.append("voucher_no=%(voucher_no)s")

	return "and {}".format(" and ".join(conditions)) if conditions else ""


def get_item_conditions(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("name=%(item_code)s")
	if filters.get("brand"):
		conditions.append("brand=%(brand)s")

	return "where {}".format(" and ".join(conditions)) if conditions else ""


def get_sl_entries(filters):
	stock_ledger_entries = frappe.db.sql(
		"""
		SELECT posting_date, item_code as item, actual_qty as qty,
	           process, voucher_type, voucher_no
		FROM `tabStock Ledger Entry`
		WHERE
	      posting_date <= %(to_date)s AND
	      ifnull(process, '') = '' AND
	      item_code like 'FC%%'
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
		SELECT name, transaction_date as posting_date, customer, item, qty
		FROM `tabIndent Invoice`
		WHERE docstatus = 1 AND
		customer="{}" AND
		cross_sold = 0 AND
		transaction_date <= %(to_date)s
		ORDER BY transaction_date desc, posting_time desc, name desc;""".format(filters['customer']),
	    filters,
		as_dict=True
	)
	for i in indent_invoices:
		i.v_type = 'Indent Invoice'

	return indent_invoices

def get_opening_gr(filters):
	# posting_date
	grs = frappe.db.sql(
		"""
		SELECT is_opening, name, posting_date, customer, item_delivered as item, delivered_quantity as qty
		FROM `tabGoods Receipt`
		WHERE docstatus = 1 AND
		is_opening = 1 AND
		customer="{}" AND
		item_delivered like 'FC%%' AND
		posting_date <= %(to_date)s
		ORDER BY posting_date desc, posting_time desc, name desc;""".format(filters['customer']),
	    filters,
		as_dict=True
	)
	for i in grs:
		i.v_type = 'Goods Receipt'

	return grs


def get_default_map():
	return frappe._dict({
	"opening": 0,
	"entries": [],
	"total_debit": 0,
	"total_credit": 0,
	"closing": 0
	})


def initialize_voucher_maps(filters, vouchers):
	opening_map = frappe._dict()
	current_map = frappe._dict()

	for voucher in vouchers:
		active_map = opening_map if voucher.posting_date < filters['from_date'] else current_map
		active_map.setdefault(get_item(voucher.item, filters), get_default_map())

		active_map[get_item(voucher.item, filters)].entries.append(voucher)

	return opening_map, current_map


def get_data_with_opening_closing(filters, opening_map, current_map):
	compute_closing(opening_map)
	copy_closing_over_to_opening(opening_map, current_map)
	compute_closing(current_map)

	return current_map

def compute_closing(active_map):
	for item, voucher_map in active_map.items():
		for entry in voucher_map.entries:
			debit, credit = debit_or_credit_voucher(entry)
			voucher_map.total_debit += debit
			voucher_map.total_credit += credit

		diff = voucher_map.opening + voucher_map.total_credit - voucher_map.total_debit
		voucher_map.closing = diff

def copy_closing_over_to_opening(opening_map, current_map):
	for item, voucher_map in opening_map.items():
		current_map.setdefault(item, get_default_map())
		active_map_instance = current_map[item]
		active_map_instance.opening = voucher_map.closing

def debit_or_credit_voucher(voucher):
	if voucher.v_type == 'Indent Invoice':
		return 0, voucher.qty
	elif voucher.v_type == 'Goods Receipt':
		return voucher.qty, 0
	elif voucher.v_type == 'Stock Ledger Entry':
		qty = abs(voucher.qty)
		if voucher.qty > 0: return qty, 0
		else: return 0, qty

def get_credit_balance_in_debit_credit_split(bal):
	if bal > 0: return 0, bal
	else: return abs(bal), 0

def get_item(item, filters):
	if cint(filters.lot_vot_bifurcate) == 0:
		return item.replace('L','')
	return item