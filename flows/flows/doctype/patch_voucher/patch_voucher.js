cur_frm.add_fetch('invoice', 'customer', 'invoice_customer');
cur_frm.add_fetch('invoice', 'item', 'item');
cur_frm.add_fetch('invoice', 'qty', 'qty');

frappe.provide("erpnext.flows");

erpnext.flows.PatchVoucherController = frappe.ui.form.Controller.extend({
    onload: function () {
    },

    setup_queries: function () {
    }
});

$.extend(cur_frm.cscript, new erpnext.flows.PatchVoucherController({frm: cur_frm}));