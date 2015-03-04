// Copyright (c) 2013, Arun Logistics and contributors
// For license information, please see license.txt

frappe.require("assets/erpnext/js/financial_statements.js");

frappe.query_reports["Sales Report"] = {
    "filters": [
        {
            "fieldname": "item_code",
            "label": __("Item"),
            "fieldtype": "Select",
            "options": "19\n35\n47.5\n47.5L"
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "width": "80",
            "default": frappe.datetime.get_today()
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "width": "80",
            "default": frappe.datetime.get_today()
        }
    ],
    "tree": true,
    "name_field": "account",
    "parent_field": "parent_account",
    "initial_depth": 3,

    "formatter": erpnext.financial_statements.formatter
};