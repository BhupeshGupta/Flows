frappe.provide("erpnext.flows");

erpnext.flows.GoodsReceiptController = frappe.ui.form.Controller.extend({
	onload:function () {
		this.setup_queries();
		this.cancelled(this.frm.doc, null, null);
	},

	setup_queries:function () {
		var me = this;
		this.frm.set_query("warehouse", function () {
			return {
				filters:[
					["Warehouse", "company", "=", me.frm.doc.company]
				]
			}
		});
	},

	cancelled:function (doc, dt, dn) {
		this.frm.set_df_property("customer", "reqd", !doc.cancelled);
		this.frm.set_df_property("remarks", "reqd", doc.cancelled);
	},

	item_delivered:function (doc, dt, dn) {
		this.update_delivered_required(doc);
	},

	delivered_quantity:function (doc, dt, dn) {
		this.update_delivered_required(doc);
	},

	update_delivered_required:function (doc) {
		this.frm.set_df_property("item_delivered", "reqd", doc.item_delivered || doc.delivered_quantity);
		this.frm.set_df_property("delivered_quantity", "reqd", doc.item_delivered || doc.delivered_quantity);
	},

	item_received:function (doc, dt, dn) {
		this.update_received_required(doc);
	},

	received_quantity:function (doc, dt, dn) {
		this.update_received_required(doc);
	},

	update_received_required:function (doc) {
		this.frm.set_df_property("item_received", "reqd", doc.item_received || doc.received_quantity);
		this.frm.set_df_property("received_quantity", "reqd", doc.item_received || doc.received_quantity);
	},

	excess:function (doc, dt, dn) {
		this.validate_units(doc);
	},
	residue:function (doc, dt, dn) {
		this.validate_units(doc);
	},
	short:function (doc, dt, dn) {
		this.validate_units(doc);
	},
	validate_units:function (doc) {
		var raise = false;
		if (doc.excess && (parseInt(doc.excess) / 1000).toFixed(2) <= 0.3)
			raise = true;
		if (doc.residue && (parseInt(doc.residue) / 1000).toFixed(2) <= 0.3)
			raise = true;
		if (doc.short && (parseInt(doc.short) / 1000).toFixed(2) <= 0.3)
			raise = true;
		if (raise)
			frappe.throw("Excess/Short/Residue below 300 grms in not accepted");
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.GoodsReceiptController({frm:cur_frm}));