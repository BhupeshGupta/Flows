frappe.provide("erpnext.flows");

erpnext.flows.GoodsReceiptController = frappe.ui.form.Controller.extend({
	onload:function () {
		this.setup_queries();
	},

	refresh:function (doc, dt, dn) {
		if (this.frm.doc.__islocal) {
    	    this.frm.set_df_property("goods_receipt_number", "reqd", true);
		}
		if (this.frm.doc.goods_receipt_number) {
    	    this.frm.set_df_property("goods_receipt_number", "reqd", true);
		}

		console.log(doc);
		if (doc.location_latitude && doc.location_longitude) {
			var map_html_string = "<img src='https://maps.googleapis.com/maps/api/staticmap?zoom=15&size=600x300&maptype=roadmap&markers=color:blue|" + doc.location_latitude + "," + doc.location_longitude + "'/>";
			$(this.frm.fields_dict['map_html'].wrapper).html(map_html_string);
		} else {
			$(this.frm.fields_dict['map_html'].wrapper).html('');
		}

		this.cancelled(doc);
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
		this.frm.set_query("customer", function () {
			return {
				filters: [
					["Customer", "enabled", "=", 1],
					["Customer", "sale_enabled", "=", 1]
				]
			}
		});
	},

	set_remarks_mandatory: function (doc) {
		var mandatory = false;
		if (doc.cancelled)
			mandatory = true;
		else if (doc.item_received && doc.item_received.indexOf('FC') >= 0)
			mandatory = true;
		else if (doc.item_delivered && doc.item_delivered.indexOf('EC') >= 0)
			mandatory = true;
		this.frm.set_df_property("remarks", "reqd", mandatory);
	},

	cancelled:function (doc, dt, dn) {
		this.frm.set_df_property("customer", "reqd", !doc.cancelled);
		this.frm.set_df_property("vehicle", "reqd", !doc.cancelled);
		this.set_remarks_mandatory(doc);
	},

	item_delivered:function (doc, dt, dn) {
		this.update_delivered_required(doc);
		this.set_remarks_mandatory(doc);
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
		this.set_remarks_mandatory(doc);
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
