cur_frm.add_fetch('item', 'item_name', 'item_name');
cur_frm.add_fetch('item', 'description', 'description');
cur_frm.add_fetch('gatepass', 'plant', 'plant');

frappe.provide("erpnext.flows");

erpnext.flows.CashReceiptController = frappe.ui.form.Controller.extend({
	onload:function () {
		//if (frappe.boot.payment_receipt && frappe.boot.payment_receipt.stock_owner) {
		//	this.frm.set_value("stock_owner", frappe.boot.payment_receipt.stock_owner, "");
		//	this.frm.set_df_property("stock_owner", "read_only", frappe.boot.payment_receipt.stock_owner != "");
		//} else {
		//	this.frm.set_df_property("stock_owner", "reqd", true);
		//}

		this.frm.set_value("company", "VK Logistics");
		this.frm.set_value("stock_owner_company", "Arun Logistics");
		this.frm.set_df_property("company", "read_only", true);
		this.frm.set_df_property("stock_owner_company", "read_only", true);
		this.cancelled(this.frm.doc, null, null);

		this.frm.set_query('debit_account', function () {
			return {
				filters:{
					'company': doc.company,
					'account_type': 'Imprest'
				}
			}
		});

	},

	refresh: function (doc) {
		me.frm.set_df_property("id", "hidden", cur_frm.doc.amended_from);
	},

	cancelled:function (doc, dt, dn) {
		this.frm.set_df_property("stock_owner", "reqd", !doc.cancelled);
		this.frm.set_df_property("item", "reqd", !doc.cancelled);
		this.frm.set_df_property("transaction_type", "reqd", !doc.cancelled);
		this.frm.set_df_property("qty", "reqd", !doc.cancelled);
		this.frm.set_df_property("amount_per_item", "reqd", !doc.cancelled);
		this.frm.set_df_property("total", "reqd", !doc.cancelled);
		this.frm.set_df_property("stock_date", "reqd", !doc.cancelled);
		this.frm.set_df_property("posting_date", "reqd", !doc.cancelled);
		this.frm.set_df_property("posting_time", "reqd", !doc.cancelled);
		this.frm.set_df_property("remarks", "reqd", doc.cancelled);
	},

	qty:function (doc, cdt, cdn) {
		this.compute_totals(doc, cdt, cdn);
	},

	amount_per_item:function (doc, cdt, cdn) {
		this.compute_totals(doc, cdt, cdn);
	},

	compute_totals:function (doc, cdt, cdn) {
		if (doc.qty && doc.amount_per_item) {
			doc.total = doc.qty * doc.amount_per_item;

			refresh_field("total", doc.name, doc.parentfield);

			// Trigger hooks
			if (this.total) {
				this.total(doc, cdt, cdn);
			}
		}
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.CashReceiptController({frm:cur_frm}));