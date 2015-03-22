frappe.provide("erpnext.flows");

erpnext.flows.GoodsReceiptController = frappe.ui.form.Controller.extend({
    onload: function () {
        this.setup_queries();
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
    }
});

$.extend(cur_frm.cscript, new erpnext.flows.GoodsReceiptController({frm: cur_frm}));