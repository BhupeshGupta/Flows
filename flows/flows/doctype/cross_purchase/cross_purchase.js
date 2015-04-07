frappe.provide("erpnext.flows");

erpnext.flows.CrossPurchase = frappe.ui.form.Controller.extend({
    onload: function () {
        this.setup_queries();
        this.frm.set_value("consignment_note_amount", 0.0);
    },

    setup_queries: function () {
        this.frm.set_query("invoice", "invoice_items", function (doc, cdt, cdn) {
            frappe.model.validate_missing(doc, "customer");
            frappe.model.validate_missing(doc, "to_date");
            return {
                query: "flows.flows.doctype.cross_purchase.cross_purchase.get_pending_invoices",
                filters: {customer: doc.customer, to_date: doc.to_date}
            };
        });
    },

    invoice: function (doc, cdt, cdn) {
        var invoice_item = frappe.get_doc(cdt, cdn);
        invoice_item.total = flt(invoice_item.consignment_note_amount) + flt(invoice_item.invoice_amount);
        refresh_field("total", invoice_item.name, invoice_item.parentfield);
        this.compute_totals(doc);
    },

    compute_totals: function (doc) {
        var invoice_total = 0;
        var consignment_note_amount_total = 0;
        $.each(doc.invoice_items, function (index, invoice_item) {
            invoice_total += invoice_item.invoice_amount;
            consignment_note_amount_total += invoice_item.consignment_note_amount;
        });
        this.frm.set_value("total_invoice_amount", invoice_total);
        this.frm.set_value("total_consignment_note_amount", consignment_note_amount_total);
        this.frm.set_value("grand_total", invoice_total + consignment_note_amount_total);
    },

    invoice_items_remove: function (doc, cdt, cdn) {
        this.compute_totals(doc);
    },

    get_pending_invoices: function () {
        var me = this;
        var btn = this.frm.get_field("get_pending_invoices")
        this.frm.runscript(btn.df.options, btn, function() {
            me.frm.doc.__unsaved = 1;
            me.frm.refresh();
        });
    }

});

$.extend(cur_frm.cscript, new erpnext.flows.CrossPurchase({frm: cur_frm}));

cur_frm.add_fetch('invoice', 'actual_amount', 'invoice_amount');
cur_frm.add_fetch('invoice', 'transportation_invoice', 'consignment_note');
cur_frm.add_fetch('invoice', 'transportation_invoice_amount', 'consignment_note_amount');
cur_frm.add_fetch('invoice', 'item', 'item');
cur_frm.add_fetch('invoice', 'qty', 'qty');
cur_frm.add_fetch('invoice', 'transaction_date', 'invoice_date');