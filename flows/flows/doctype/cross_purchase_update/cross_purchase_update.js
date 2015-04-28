frappe.provide("erpnext.flows");

erpnext.flows.CrossPurchaseUpdate = frappe.ui.form.Controller.extend({
	onload:function () {
		this.frm.set_query("cross_purchase", function (doc, cdt, cdn) {
			return {
				filters:{
					docstatus:1
				}
			};
		});
	},
	refresh:function () {
		console.log("refresh");
		this.cross_purchase(this.frm.doc, null, null);
	},

	cross_purchase:function (doc, cdt, cdn) {
		console.log("CP");
		this.frm.set_df_property("payment_in_jv", "read_only", (doc.payment_in_jv && doc.payment_in_jv != null) || doc.payment_in_jv == "");
		this.frm.set_df_property("payment_withdrawn_jv", "read_only", (doc.payment_withdrawn_jv && doc.payment_withdrawn_jv != null) || doc.payment_withdrawn_jv == "");
		this.frm.set_df_property("payment_out_jv", "read_only", (doc.payment_out_jv && doc.payment_out_jv != null) || doc.payment_out_jv == "");
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.CrossPurchaseUpdate({frm:cur_frm}));

cur_frm.add_fetch('cross_purchase', 'payment_in_jv', 'payment_in_jv');
cur_frm.add_fetch('cross_purchase', 'payment_withdrawn_jv', 'payment_withdrawn_jv');
cur_frm.add_fetch('cross_purchase', 'payment_out_jv', 'payment_out_jv');