frappe.provide("erpnext.flows");

erpnext.flows.IndentInvoiceReceiving = frappe.ui.form.Controller.extend({
	onload:function () {
		this.setup_queries();
	},

	setup_queries:function () {
		this.frm.set_query("indent", function (doc, cdt, cdn) {
			return {
				filters:{
					vehicle:doc.vehicle
				}
			};
		});
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.IndentInvoiceReceiving({frm:cur_frm}));
