// Copyright (c) 2013, Arun Logistics and contributors
// For license information, please see license.txt

frappe.query_reports["Pricing Report"] = {
	"filters": [
		{
			"fieldname":"date",
			"label":__("Date"),
			"fieldtype":"Date",
			"default":frappe.datetime.month_start(),
			"reqd":1
		}
	]
};
