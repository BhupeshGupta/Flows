frappe.provide("erpnext.flows");

erpnext.flows.CrossSalePurchase = frappe.ui.form.Controller.extend({
    onload: function () {
        this.setup_queries();
    },

    setup_queries: function () {
    },

    posting_date: function (doc, cdt, cdn) {
        this.query_purchase_rate(doc, cdt, cdn);
        this.query_sale_rate(doc, cdt, cdn);
    },

    item: function (doc, cdt, cdn) {
        this.query_purchase_rate(doc, cdt, cdn);
        this.query_sale_rate(doc, cdt, cdn);
    },

    from_customer: function (doc, cdt, cdn) {
        this.query_purchase_rate(doc, cdt, cdn);
    },

    to_customer: function (doc, cdt, cdn) {
        this.query_sale_rate(doc, cdt, cdn);
    },

    query_purchase_rate: function (doc, cdt, cdn) {
        if (doc.from_customer && doc.item && doc.posting_date) {
            var me = this;
            return frappe.call({
                method: "flows.flows.pricing_controller.get_landed_rate",
                args: {
                    customer: doc.from_customer,
                    item: doc.item,
                    posting_date: doc.posting_date
                },
                callback: function (r) {
                    if (!r.exc) {
                        me.frm.set_value("purchase_rate", r.message);
                        if (me.purchase_rate) {
                            me.purchase_rate(doc, cdt, cdn);
                        }
                    }
                }
            });

        }

    },

    query_sale_rate: function (doc, cdt, cdn) {
        if (doc.to_customer && doc.item && doc.posting_date) {
            var me = this;
            return frappe.call({
                method: "flows.flows.pricing_controller.get_landed_rate",
                args: {
                    customer: doc.to_customer,
                    item: doc.item,
                    posting_date: doc.posting_date
                },
                callback: function (r) {
                    if (!r.exc) {
                        me.frm.set_value("sale_rate", r.message);
                        if (me.sale_rate) {
                            me.sale_rate(doc, cdt, cdn);
                        }
                    }
                }
            });
        }
    },

    qty: function (doc, cdt, cdn) {
        this.compute_purchase_amount(doc, cdt, cdn);
        this.compute_sale_amount(doc, cdt, cdn);
    },

    purchase_rate: function (doc, cdt, cdn) {
        this.compute_purchase_amount(doc, cdt, cdn);
    },

    compute_purchase_amount: function (doc, cdt, cdn) {
        this.frm.set_value("purchase_amount", doc.qty * doc.purchase_rate);
    },

    sale_rate: function (doc, cdt, cdn) {
        this.compute_sale_amount(doc, cdt, cdn);
    },

    compute_sale_amount: function (doc, cdt, cdn) {
        this.frm.set_value("sale_amount", doc.qty * doc.sale_rate);
    }

});

$.extend(cur_frm.cscript, new erpnext.flows.CrossSalePurchase({frm: cur_frm}));