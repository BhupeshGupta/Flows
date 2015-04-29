frappe.provide("erpnext.flows");

erpnext.flows.GoodsReceiptController = frappe.ui.form.Controller.extend({
    onload: function () {
        this.setup_queries();
	    this.cancelled(this.frm.doc, null, null);
    },

    setup_queries: function () {
        var me = this;
        this.frm.set_query("warehouse", function () {
            return {
                filters: [
                    ["Warehouse", "company", "=", me.frm.doc.company]
                ]
            }
        });
    },

	cancelled: function (doc, dt, dn) {
		this.frm.set_df_property("customer", "reqd", !doc.cancelled);
	},

	item_delivered: function (doc, dt, dn) {
		this.update_delivered_required(doc);
	},

	delivered_quantity: function (doc, dt, dn) {
		this.update_delivered_required(doc);
	},

	update_delivered_required: function (doc) {
		this.frm.set_df_property("item_delivered", "reqd", doc.item_delivered || doc.delivered_quantity);
		this.frm.set_df_property("delivered_quantity", "reqd", doc.item_delivered || doc.delivered_quantity);
	},

	item_received: function (doc, dt, dn) {
		this.update_received_required(doc);
	},

	received_quantity: function (doc, dt, dn) {
		this.update_received_required(doc);
	},

	update_received_required: function (doc) {
		this.frm.set_df_property("item_received", "reqd", doc.item_delivered || doc.delivered_quantity);
		this.frm.set_df_property("received_quantity", "reqd", doc.item_delivered || doc.delivered_quantity);
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.GoodsReceiptController({frm: cur_frm}));