frappe.provide("erpnext.flows");

erpnext.flows.CrossSale = frappe.ui.form.Controller.extend({
	onload:function () {
		this.frm.set_query("item", function (doc, cdt, cdn) {
			return {
				filters:[
					["Item", "name", "like", "F%"]
				]
			};
		});
	},

	refresh:function () {
	},

	qty:function (doc, cdt, cdn) {
		this.update_amount(doc, cdt, cdn);
	},

	rate:function (doc, cdt, cdn) {
		this.update_amount(doc, cdt, cdn);
	},

	update_amount:function (doc, cdt, cdn) {
		if (doc.qty && doc.rate) {
			this.frm.set_value("amount", doc.qty * doc.rate);
		}
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.CrossSale({frm:cur_frm}));