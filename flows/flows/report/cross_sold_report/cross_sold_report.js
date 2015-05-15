// Copyright (c) 2013, Arun Logistics and contributors
// For license information, please see license.txt

frappe.query_reports["Cross Sold Report"] = {
	"filters":[
		{
			"fieldname":"from_date",
			"label":__("From Date"),
			"fieldtype":"Date",
			"width":"80",
			"default":frappe.datetime.month_start(),
			"reqd":1
		},
		{
			"fieldname":"to_date",
			"label":__("To Date"),
			"fieldtype":"Date",
			"width":"80",
			"default":frappe.datetime.month_end(),
			"reqd":1
		},
		{
			"fieldname":"customer",
			"label":__("Customer"),
			"fieldtype":"Link",
			"options":"Customer",
			"reqd":0
		},
		{
			"fieldname":"include_indents",
			"label":__("Include Indents"),
			"fieldtype":"Check",
			"options":"Item",
			default:1
		}

	]
};
