// Copyright (c) 2013, Arun Logistics and contributors
// For license information, please see license.txt

frappe.query_reports["HPCL Reconciliation"] = {
	"filters": [
		{
			"fieldname":"date",
			"label":__("Date"),
			"fieldtype":"Date",
			"reqd":1
		}
	]
};
