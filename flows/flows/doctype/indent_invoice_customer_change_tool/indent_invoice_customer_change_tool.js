frappe.provide("erpnext.flows");

erpnext.flows.IndentInvoiceCustomerChangeTool = frappe.ui.form.Controller.extend({
	onload:function () {
		this.setup_queries();
	},

	setup_queries:function () {
		this.frm.set_query("invoice", function (doc, cdt, cdn) {
			return {
				filters:{
					docstatus:1
				}
			};
		});
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.IndentInvoiceCustomerChangeTool({frm:cur_frm}));
