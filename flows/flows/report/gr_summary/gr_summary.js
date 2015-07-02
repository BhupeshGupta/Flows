// Copyright (c) 2013, Arun Logistics and contributors
// For license information, please see license.txt

frappe.query_reports["GR Summary"] = {
	"filters":[
		{
			"fieldname":"from_date",
			"label":__("From Date"),
			"fieldtype":"Date",
			"width":"80",
			"default":frappe.datetime.get_today(),
			"reqd":1
		},
		{
			"fieldname":"to_date",
			"label":__("To Date"),
			"fieldtype":"Date",
			"width":"80",
			"default":frappe.datetime.get_today(),
			"reqd":1
		},
		{
			"fieldname":"show_draft_entries",
			"label":__("Show Draft Entries"),
			"fieldtype":"Check",
			"default":0
		},
	]
};
