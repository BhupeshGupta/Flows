// Copyright (c) 2013, Arun Logistics and contributors
// For license information, please see license.txt

frappe.query_reports["Outstanding Report"] = {
	"filters": [
		{
			"fieldname":"date",
			"label":__("Date"),
			"fieldtype":"Date",
			"default":frappe.datetime.get_today(),
			"reqd":1
		}
	]
};
