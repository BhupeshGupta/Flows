// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.flows");

erpnext.flows.QuotationTool = frappe.ui.form.Controller.extend({
	onload: function() {

	},

	setup: function() {

	},

	refresh: function() {
        this.show_upload();
        this.frm.set_intro(__("You can upload the Pricing sheet to send quotes."));
        this.show_cpv_data();
	},

	show_upload: function() {
		var me = this;
		var $wrapper = $(cur_frm.fields_dict.upload_html.wrapper).empty();

		// upload
		frappe.upload.make({
			parent: $wrapper,
			args: {
				method: 'flows.flows.doctype.quotation_tool.quotation_tool.upload'
			},
			sample_url: "e.g. http://example.com/somefile.csv",
			callback: function(attachment, r) {
				me.frm.set_value("cpv_json", JSON.stringify(r.message));
				me.show_cpv_data();
				me.frm.save();
			}
		});

		// rename button
		$wrapper.find('form input[type="submit"]')
			.attr('value', 'Upload')

	},

	show_cpv_data: function() {
		var $wrapper = $(cur_frm.fields_dict.quotation_html.wrapper).empty();
		if(this.frm.doc.cpv_json) {
			var reconciliation_data = JSON.parse(this.frm.doc.cpv_json);

			var _make = function(data, header) {
				var result = "";

				var _render = header
					? function(col) { return "<th>" + col + "</th>"; }
					: function(col) { return "<td>" + col + "</td>"; };

				$.each(data, function(i, row) {
					result += "<tr>"
						+ $.map(row, _render).join("")
						+ "</tr>";
				});
				return result;
			};

			var $reconciliation_table = $("<div style='overflow-x: auto;'>\
					<table class='table table-striped table-bordered'>\
					<thead>" + _make([reconciliation_data[0]], true) + "</thead>\
					<tbody>" + _make(reconciliation_data.splice(1)) + "</tbody>\
					</table>\
				</div>").appendTo($wrapper);
		}
	}

});

cur_frm.cscript = new erpnext.flows.QuotationTool({frm: cur_frm});
