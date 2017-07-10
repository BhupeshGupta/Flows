cur_frm.add_fetch('item', 'item_name', 'item_name');
cur_frm.add_fetch('item', 'description', 'description');
cur_frm.add_fetch('gatepass', 'plant', 'plant');

frappe.provide("erpnext.flows");

erpnext.flows.SubcontractedInvoiceController = frappe.ui.form.Controller.extend({
	onload:function () {
		// this.frm.set_value("company", "Aggarwal Enterprises");
	},

	refresh: function (doc) {
		me.frm.set_df_property("id", "hidden", cur_frm.doc.amended_from);
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.SubcontractedInvoiceController({frm:cur_frm}));