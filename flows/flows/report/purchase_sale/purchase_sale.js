// Copyright (c) 2013, Arun Logistics and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Sale"] = {
	"filters":[
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
			"fieldname":"opening_computation_method",
			"label":__("Opening Computation Method"),
			"fieldtype": "Select",
			"options": 'Bill To' + NEWLINE + 'Ship To',
			"default": "Ship To"
		},
		{
			"fieldname":"current_computation_method",
			"label":__("Current Computation Method"),
			"fieldtype": "Select",
			"options": 'Bill To' + NEWLINE + 'Ship To',
			"default": "Ship To"
		},
		{
			"fieldname":"lot_vot_bifurcate",
			"label":__("LOT VOT Bifurcate"),
			"fieldtype":"Check",
			"default":0
		},
		{
			"fieldname":"show_material_returned",
			"label":__("Show Material Returned"),
			"fieldtype":"Check",
			"default":0
		}
	]
};
