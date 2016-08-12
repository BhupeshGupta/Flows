cur_frm.add_fetch('item', 'item_name', 'item_name');
cur_frm.add_fetch('item', 'description', 'description');
cur_frm.add_fetch('gatepass', 'plant', 'plant');
cur_frm.add_fetch('vehicle', 'driver', 'driver');

frappe.provide("erpnext.flows");

erpnext.flows.OmcPoliciesController = frappe.ui.form.Controller.extend({
	onload:function () {
	},

	refresh:function (doc, dt, dn) {
		doc.description_html = '';
		if (doc.description_markdown) {
			$(this.frm.fields_dict['description_html'].wrapper).html(
				doc.description_html = frappe.markdown(doc.description_markdown)
			)
		}
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.OmcPoliciesController({frm: cur_frm}));
