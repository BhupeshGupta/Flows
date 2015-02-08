# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns(filters)
    item_map = get_item_details(filters)
    iwb_map = get_item_warehouse_map(filters)

    data = []
    for company in sorted(iwb_map):
        for item in sorted(iwb_map[company]):
            for wh in sorted(iwb_map[company][item]):
                qty_dict = iwb_map[company][item][wh]
                data.append([
                    item, wh, qty_dict.bal_qty,
                    qty_dict.opening_qty, qty_dict.in_qty,
                    qty_dict.out_qty, company
                ])

    return columns, data


def get_columns(filters):
    """return columns based on filters"""

    columns = [
        "Item:Link/Item:100", "Warehouse:Link/Warehouse:200", "Balance Qty:Float:100",
        "Opening Qty:Float:100", "In Qty:Float:80",
        "Out Qty:Float:80", "Company:Link/Company:100"
    ]

    return columns


def get_conditions(filters):
    conditions = ""
    if not filters.get("from_date"):
        frappe.throw(_("'From Date' is required"))

    if filters.get("to_date"):
        conditions += " and posting_date <= '%s'" % filters["to_date"]
    else:
        frappe.throw(_("'To Date' is required"))

    return conditions


# get all details
def get_stock_ledger_entries(filters):
    conditions = get_conditions(filters)
    sle =  frappe.db.sql("""select item_code, warehouse, posting_date, actual_qty, valuation_rate,
	stock_uom, company, voucher_type, qty_after_transaction, stock_value_difference
		from `tabStock Ledger Entry`
		where docstatus < 2 %s order by posting_date, posting_time, name""" %
                         conditions, as_dict=1)

    for e in sle:
        if 'FC' in e['item_code']:
            e['item_code'] = e['item_code'].replace('FC', '')
        elif 'EC' in e['item_code']:
            e['item_code'] = e['item_code'].replace('EC', '')

    return sle


def get_item_warehouse_map(filters):
    sle = get_stock_ledger_entries(filters)
    iwb_map = {}

    for d in sle:
        iwb_map.setdefault(d.company, {}).setdefault(d.item_code, {}). \
            setdefault(d.warehouse, frappe._dict({ \
            "opening_qty": 0.0, "opening_val": 0.0,
            "in_qty": 0.0, "in_val": 0.0,
            "out_qty": 0.0, "out_val": 0.0,
            "bal_qty": 0.0, "bal_val": 0.0,
            "val_rate": 0.0, "uom": None
        }))
        qty_dict = iwb_map[d.company][d.item_code][d.warehouse]
        qty_dict.uom = d.stock_uom

        if d.voucher_type == "Stock Reconciliation":
            qty_diff = flt(d.qty_after_transaction) - qty_dict.bal_qty
        else:
            qty_diff = flt(d.actual_qty)

        value_diff = flt(d.stock_value_difference)

        if d.posting_date < filters["from_date"]:
            qty_dict.opening_qty += qty_diff
            qty_dict.opening_val += value_diff
        elif d.posting_date >= filters["from_date"] and d.posting_date <= filters["to_date"]:
            qty_dict.val_rate = d.valuation_rate
            if qty_diff > 0:
                qty_dict.in_qty += qty_diff
                qty_dict.in_val += value_diff
            else:
                qty_dict.out_qty += abs(qty_diff)
                qty_dict.out_val += abs(value_diff)

        qty_dict.bal_qty += qty_diff
        qty_dict.bal_val += value_diff

    return iwb_map


def get_item_details(filters):
    item_map = {}
    for d in frappe.db.sql("select name, item_name, item_group, brand, \
		description from tabItem", as_dict=1):
        item_map.setdefault(d.name, d)

    return item_map
