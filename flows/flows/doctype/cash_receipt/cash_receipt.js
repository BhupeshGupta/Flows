cur_frm.add_fetch('item', 'item_name', 'item_name');
cur_frm.add_fetch('item', 'description', 'description');
cur_frm.add_fetch('gatepass', 'plant', 'plant');

frappe.provide("erpnext.flows");

erpnext.flows.CashReceiptController = frappe.ui.form.Controller.extend({
    onload: function () {
    },

    qty: function (doc, cdt, cdn) {
        this.compute_totals(doc, cdt, cdn);
    },

    amount_per_item: function (doc, cdt, cdn) {
        this.compute_totals(doc, cdt, cdn);
    },

    compute_totals: function (doc, cdt, cdn) {
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

$.extend(cur_frm.cscript, new erpnext.flows.CashReceiptController({frm: cur_frm}));

if (frappe.boot.cash_receipt && frappe.boot.cash_receipt.stock_owner) {
    cur_frm.set_value("stock_owner", frappe.boot.cash_receipt.stock_owner, "");
    cur_frm.set_df_property("stock_owner", "read_only", frappe.boot.cash_receipt.stock_owner != "");
} else {
    cur_frm.set_df_property("stock_owner", "reqd", true);
}