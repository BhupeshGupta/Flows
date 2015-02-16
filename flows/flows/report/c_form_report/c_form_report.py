# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
    columns, data = [], []
    return columns, data


def get_data():
    frappe.db.sql("Select customer, sum(actual_amount) from `tabIndent Invoice`;")
