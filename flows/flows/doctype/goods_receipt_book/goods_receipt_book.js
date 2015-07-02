frappe.provide("erpnext.flows");

erpnext.flows.GoodsReceiptBookController = frappe.ui.form.Controller.extend({
	onload:function () {
		this.setup_queries();
		this.set_fields(this.frm.doc, null, null);
	},

	setup_queries:function () {
		console.log("Set up ran");

		this.frm.set_query("pr_debit", function () {
            return {
                filters: [
                    ["Account", "company", "=", "VK Logistics"]
                ]
            }
        });

	},

	gr_enabled:function (doc, cdt, cdn) {
		this.set_fields(doc, cdt, cdn);
	},

	pr_enabled:function (doc, cdt, cdn) {
		this.set_fields(doc, cdt, cdn);
	},

	set_fields:function (doc, cdt, cdn) {
		if (doc.gr_enabled == 0)
			this.frm.set_value("warehouse", "");
		if (doc.pr_enabled == 0)
			this.frm.set_value("pr_debit", "");

		this.frm.set_df_property("warehouse", "reqd", doc.gr_enabled == 1);
		this.frm.set_df_property("pr_debit", "reqd", doc.pr_enabled == 1);
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.GoodsReceiptBookController({frm: cur_frm}));