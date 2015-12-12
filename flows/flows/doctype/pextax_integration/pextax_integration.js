cur_frm.add_fetch('item', 'item_name', 'item_name');
cur_frm.add_fetch('item', 'description', 'description');
cur_frm.add_fetch('gatepass', 'plant', 'plant');
cur_frm.add_fetch('vehicle', 'driver', 'driver');

frappe.provide("erpnext.flows");

erpnext.flows.IndentController = frappe.ui.form.Controller.extend({
	onload:function () {
		this.set_image(cur_frm.doc);
	},

	refresh:function (doc) {
		this.set_image(cur_frm.doc);
	},

	set_image:function (doc) {
		console.log('Hello JS!!');
		$(this.frm.fields_dict['html'].wrapper).html('<img src="' + doc.file + '"/>');
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.IndentController({frm:cur_frm}));
