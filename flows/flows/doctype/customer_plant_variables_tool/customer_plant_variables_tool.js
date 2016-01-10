// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.flows");

erpnext.flows.CustomerPlantVariablesTool = frappe.ui.form.Controller.extend({
	onload: function() {

	},

	setup: function() {

	},

	download: function (doc, cdt, cdn) {
      window.location.href = repl(frappe.request.url
         + '?cmd=%(cmd)s&date=%(date)s&plant=%(plant)s',
         {
            cmd:'flows.flows.doctype.customer_plant_variables_tool.customer_plant_variables_tool.download',
            date: this.frm.doc.date,
            plant: this.frm.doc.plant,
         });
   },

   export_hpcl_file: function (doc, cdt, cdn) {
      window.location.href = repl(frappe.request.url
         + '?cmd=%(cmd)s&date=%(date)s&plant=%(plant)s',
         {
            cmd:'flows.flows.doctype.customer_plant_variables_tool.customer_plant_variables_tool.export_hpcl_file',
            date: this.frm.doc.date,
            plant: this.frm.doc.plant,
         });
   },

	refresh: function() {
        this.show_upload();
        this.frm.set_intro(__("You can download template and upload the same to update customer plant variables."));
        this.show_cpv_data();
	},

	show_upload: function() {
		var me = this;
		var $wrapper = $(cur_frm.fields_dict.upload_html.wrapper).empty();

		// upload
		frappe.upload.make({
			parent: $wrapper,
			args: {
				method: 'flows.flows.doctype.customer_plant_variables_tool.customer_plant_variables_tool.upload'
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

//	show_download_reconciliation_data: function() {
//		var me = this;
//		if(this.frm.doc.reconciliation_json) {
//			this.frm.add_custom_button(__("Download Reconcilation Data"), function() {
//				this.title = __("Stock Reconcilation Data");
//				frappe.tools.downloadify(JSON.parse(me.frm.doc.reconciliation_json), null, this);
//				return false;
//			}, "icon-download", "btn-default");
//		}
//	},

	show_cpv_data: function() {
		var $wrapper = $(cur_frm.fields_dict.customer_plant_variables_html.wrapper).empty();
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
	},
});

cur_frm.cscript = new erpnext.flows.CustomerPlantVariablesTool({frm: cur_frm});
