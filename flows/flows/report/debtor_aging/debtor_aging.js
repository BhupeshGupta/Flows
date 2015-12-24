// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
// For license information, please see license.txt

frappe.query_reports["Debtor Aging"] = {
	"filters":[
		{
			"fieldname":"interval",
			"label":__("Interval"),
			"fieldtype":"Int",
			"reqd":1
		},
		{
			"fieldname":"no_of_intervals",
			"label":__("No Of Intervals"),
			"fieldtype":"Int",
			"reqd":1
		},
		{
			"fieldname":"company",
			"label":__("Company"),
			"fieldtype":"Link",
			"options":"Company",
			"default":frappe.defaults.get_user_default("company"),
			"reqd":1
		},
		{
			"fieldname":"account",
			"label":__("Account"),
			"fieldtype":"Link",
			"options":"Account",
			"get_query":function () {
				var company = frappe.query_report.filters_by_name.company.get_value();
				return {
					"doctype":"Account",
					"filters":{
						"company":company,
						"group_or_ledger":'Group'
					}
				}
			}
		}
	],
	"tree":true,
	"name_field":"name",
	"parent_field":"parent_account",
	"initial_depth":0,

	"formatter":function (row, cell, value, columnDef, dataContext, default_formatter) {
		if (columnDef.df.fieldname == "name") {
			value = dataContext.name;
			columnDef.df.is_tree = true;
		}

		value = default_formatter(row, cell, value, columnDef, dataContext);

		if (dataContext.group_or_ledger=='Group') {
			var $value = $(value).css("font-weight", "bold");
			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	}
};
