// Copyright (c) 2013, Arun Logistics and contributors
// For license information, please see license.txt

frappe.query_reports["C Form Report"] = {
    "filters": [
	    {
			"fieldname":"customer",
			"label":__("Customer"),
			"fieldtype":"Link",
			"options":"Customer",
			"reqd":1
		},
	    {
			"fieldname":"from_date",
			"label":__("From Date"),
			"fieldtype":"Date",
			"default":frappe.datetime.month_start(),
			"reqd":1
		},
		{
			"fieldname":"to_date",
			"label":__("To Date"),
			"fieldtype":"Date",
			"default":frappe.datetime.month_end(),
			"reqd":1
		},
		{
			"fieldname":"supplier",
			"label":__("Supplier"),
			"fieldtype":"Link",
			"options":"Supplier",
			"reqd":1,
			"get_query": function() {
				return {
					"filters": [
						['Supplier', 'supplier_type', '=', 'OMC STATE'],
					]
				}
			}
		}
    ]
};