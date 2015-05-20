frappe.provide("erpnext.flows");

erpnext.flows.IndentInvoice = frappe.ui.form.Controller.extend({
    onload: function () {
        this.setup_queries();
        this.set_fields(this.frm.doc, null, null);
    },

    set_plant_query: function (field) {
        if (this.frm.fields_dict[field]) {
            this.frm.set_query(field, function () {
                return {
                    filters: {'supplier_type': 'Gas Plant'}
                }
            });
        }
    },

    set_fields: function (doc, cdt, cdn) {
        var me = this;

        feilds_to_autofill_on_linking = [
            "customer", "item", "qty",
            "supplier", "rate", "load_type",
            "warehouse", "logistics_partner",
            "payment_type", "company",
            "sub_contracted"
        ];

        feilds_mandatory_for_linking = ["vehicle", "indent_item"];
        feilds_autofilled_on_linking = ["tentative_amount", "indent", "indent_date"];
        feilds_to_clear_on_indent_linking = ["sub_contracted", "warehouse"];

        $.each(feilds_to_autofill_on_linking, function (i, feild) {
            me.frm.set_df_property(feild, "read_only", doc.indent_linked == '1');
        });

        $.each(feilds_mandatory_for_linking, function (i, feild) {
            me.frm.set_df_property(feild, "reqd", doc.indent_linked == '1');
        });

        if (doc.indent_linked != '1') {
            if (doc.docstatus == 0) {
                $.each(feilds_mandatory_for_linking, function (i, feild) {
                    me.frm.set_value(feild, "");
                });
                $.each(feilds_autofilled_on_linking, function (i, feild) {
                    me.frm.set_value(feild, "");
                });
            }
        } else {
            $.each(feilds_to_clear_on_indent_linking, function (i, feild) {
                if (feild == "sub_contracted") {
                    me.frm.set_value(feild, 0);
                } else {
                    if (doc.docstatus == 0) {
                        me.frm.set_value(feild, "");
                    }
                }
            });

        }

        $.each(feilds_mandatory_for_linking, function (i, feild) {
            me.frm.set_df_property(feild, "hidden", doc.indent_linked != '1');
        });
        $.each(feilds_autofilled_on_linking, function (i, feild) {
            me.frm.set_df_property(feild, "hidden", doc.indent_linked != '1');
        });

        // Subcontracting data sanity
        feilds_to_clear_and_disable_on_sub_contract = ["warehouse", "load_type"];
        $.each(feilds_to_clear_and_disable_on_sub_contract, function (i, feild) {
            me.frm.set_df_property(feild, "read_only", doc.sub_contracted == '1' || doc.indent_linked == '1');
            if (doc.sub_contracted == '1') {
                me.frm.set_value(feild, "");
            }
        });
    },

    indent_linked: function (doc, cdt, cdn) {
        this.set_fields(doc, cdt, cdn);
    },

    sub_contracted: function (doc, cdt, cdn) {
        this.set_fields(doc, cdt, cdn);
    },

    setup_queries: function () {
        this.set_plant_query("plant");

        this.frm.set_query("indent_item", function (doc, cdt, cdn) {

            frappe.model.validate_missing(doc, "vehicle");

            return {
                query: "flows.flows.doctype.indent_invoice.indent_invoice.get_indent_for_vehicle",
                filters: {vehicle: doc.vehicle},
                searchfield: "customer"
            };
        });
    },

    indent: function (doc, cdt, cdn) {
        // "{"message":{"posting_date":"2015-03-06","plant":"IOCL una","logistics_partner":"Arun Logistics","vehicle":"HR58D4473"}}"
        var me = this;
        frappe.call({
            "method": "frappe.client.get_value",
            "args": {
                "doctype": "Indent",
                "filters": {
                    "name": doc.indent
                }, "fieldname": '["posting_date", "logistics_partner", "plant", "vehicle", "company"]'
            },
            callback: function (r, rt) {
                me.frm.set_value("indent_date", r.message.posting_date);
                me.frm.set_value("logistics_partner", r.message.logistics_partner);
                me.frm.set_value("supplier", r.message.plant);
                me.frm.set_value("company", r.message.company);
            }
        });
    },

    // Pre fill most used options to aid data entry
    supplier: function (doc, cdt, cdn) {
        if (doc.supplier == "Aggarwal Enterprises") {
            this.frm.set_value("company", "Aggarwal Enterprises");
            this.frm.set_value("logistics_partner", "Arun Logistics");
            this.frm.set_value("sub_contracted", 1);
            this.frm.set_value("payment_type", "Direct");
        }
    }

});

$.extend(cur_frm.cscript, new erpnext.flows.IndentInvoice({frm: cur_frm}));

cur_frm.add_fetch('item', 'description', 'description');
cur_frm.add_fetch('gatepass', 'plant', 'plant');
cur_frm.add_fetch('vehicle', 'driver', 'driver');

cur_frm.add_fetch('indent_item', 'customer', 'customer');
cur_frm.add_fetch('indent_item', 'item', 'item');
cur_frm.add_fetch('indent_item', 'qty', 'qty');
cur_frm.add_fetch('indent_item', 'rate', 'rate');

cur_frm.add_fetch('indent_item', 'parent', 'indent');
cur_frm.add_fetch('indent_item', 'load_type', 'load_type');
cur_frm.add_fetch('indent_item', 'payment_type', 'payment_type');
cur_frm.add_fetch('indent_item', 'cross_sold', 'cross_sold');