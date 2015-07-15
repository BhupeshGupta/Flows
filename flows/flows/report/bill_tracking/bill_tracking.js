// Copyright (c) 2013, Arun Logistics and contributors
// For license information, please see license.txt

var el = document.createElement('script');
var att = document.createAttribute("src");
att.value = "http://mleibman.github.io/SlickGrid/slick.editors.js";
el.setAttributeNode(att);

document.getElementsByTagName('head')[0].appendChild(el);

frappe.query_reports["Bill Tracking"] = {
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
		}
	],
	startup:function (grid, dataview) {
		grid.onCellChange.subscribe(function (e, args) {
			grid.invalidateRow(args.row);
			var row = dataview.getItem(args.row);
			//row[grid.getColumns()[args.cell].field] = 'Yay';

			if (!grid.getColumns()['change']) row[grid.getColumns()['change']] = [];

			grid.getColumns()['change'].push(grid.getColumns()[args.cell].field);
			dataview.updateItem(args.item.id, row);
			grid.render();
		});
	}
};

var report = frappe.query_report;
report.appframe.add_button(__('Update'), function () {
	console.log("Update Triggered");
}, "icon-thumbs-up");

frappe.query_report.slickgrid_options["editable"] = true;
frappe.query_report.slickgrid_options["autoEdit"] = false;