// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

//frappe.require("assets/erpnext/js/financial_statements.js");

frappe.query_reports["Inventory Balance"] = {
	"filters":[
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd":1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd":1
		}
	],
	"tree":true,
	"name_field":"warehouse",
	"parent_field":"parent_warehouse",
	"initial_depth":0,
	"formatter":function (row, cell, value, columnDef, dataContext, default_formatter) {
		if (columnDef.df.fieldname == "warehouse") {
			value = dataContext.warehouse;
			columnDef.df.is_tree = true;
		}

		value = default_formatter(row, cell, value, columnDef, dataContext);

		if (!dataContext.parent_warehouse) {
			var $value = $(value).css("font-weight", "bold");
			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	}
};