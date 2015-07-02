// Copyright (c) 2013, Arun Logistics and contributors
// For license information, please see license.txt

frappe.query_reports["Vendor Report"] = {
	"filters": [
		{
			"fieldname":"date",
			"label":__("Date"),
			"fieldtype":"Date",
			"width":"80",
			"reqd":1
		},
		{
			"fieldname":"item_code",
			"label":__("Item"),
			"fieldtype":"Link",
			"options":"Item",
			"reqd":1,
			"get_query":function () {
				return {
					filters:[
						["Item", "name", "like", "F%"]
					]
				}
			}
		},
		{
			"fieldname":"bifurcate",
			"label":__("Bifurcate"),
			"fieldtype":"Check",
			"options":"Item",
			default: 0
		}
	]
};
