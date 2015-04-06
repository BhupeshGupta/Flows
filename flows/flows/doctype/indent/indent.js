cur_frm.add_fetch('item', 'item_name', 'item_name');
cur_frm.add_fetch('item', 'description', 'description');
cur_frm.add_fetch('gatepass', 'plant', 'plant');
cur_frm.add_fetch('vehicle', 'driver', 'driver');

frappe.provide("erpnext.flows");

erpnext.flows.IndentController = frappe.ui.form.Controller.extend({
    onload: function () {
        this.setup_queries();
        // Set company according to naming series
        this.naming_series(this.frm.doc, null, null);
    },

    set_plant_query: function (field) {
        if (this.frm.fields_dict[field]) {
            this.frm.set_query(field, function () {
                return{
                    filters: { 'supplier_type': 'Gas Plant' }
                }
            });
        }
    },

    setup_queries: function () {
        this.set_plant_query("plant");

        this.frm.set_query("item", "indent", function () {
            return{
                filters: [
                    ["Item", "name", "like", "F%"]
                ]
            }
        });

        this.frm.fields_dict['indent'].grid.get_field("eiv")
    },

    // Hook events to compute func
    rate: function (doc, cdt, cdn) {
        this.compute_indent_item_amount(doc, cdt, cdn);
    },
    qty: function (doc, cdt, cdn) {
        this.compute_indent_item_amount(doc, cdt, cdn);
    },

    // Indent level info
    plant: function (doc, cdt, cdn) {
        this.populate_payment_type_info(doc, cdt, cdn);
        this.compute_base_rate(doc, cdt, cdn);
    },

    posting_date: function (doc, cdt, cdn) {
        this.populate_payment_type_info(doc, cdt, cdn);
        this.compute_base_rate(doc, cdt, cdn);
    },

    // Indent item info
    customer: function (doc, cdt, cdn) {
        this.populate_payment_type_info(doc, cdt, cdn);
        this.compute_base_rate(doc, cdt, cdn);
    },

    item: function (doc, cdt, cdn) {
        this.compute_base_rate(doc, cdt, cdn);
    },

    amount: function (doc, cdt, cdn) {
        this.compute_totals(doc, cdt, cdn);
    },

    payment_type: function (doc, cdt, cdn) {
        this.compute_totals(doc, cdt, cdn);
    },

    // Compute base rate for customer taking in consideration of indent date, plant, customer and item
    compute_base_rate: function (doc, cdt, cdn) {
        var me = this;

        // To handel changes in plant and date
        if (cdt == "Indent") {
            var indent_items = doc.indent;
        }
        else {
            var indent_items = [frappe.get_doc(cdt, cdn)];
        }

        // Skip computation if indent items are empty
        if (indent_items) {
            $.each(indent_items, function (index, indent_item) {
                if (indent_item.item && indent_item.customer && doc.plant && doc.posting_date) {
                    return frappe.call({
                        method: "flows.flows.pricing_controller.compute_base_rate_for_a_customer",
                        args: {
                            plant: doc.plant,
                            customer: indent_item.customer,
                            item: indent_item.item,
                            sales_tax_type: indent_item.sales_tax_type,
                            posting_date: doc.posting_date
                        },
                        callback: function (r) {
                            console.log("compute_base_rate callback");
                            if (!r.exc) {
                                console.log(r.message);

                                // Do not change rate if we dont have value
                                if (r.message <= 0) return;

                                indent_item.rate = r.message;
                                refresh_field("rate", indent_item.name, indent_item.parentfield);
                                if (me.rate) {
                                    me.rate(indent_item, indent_item.doctype, indent_item.name);
                                }
                            }
                        }
                    });

                }

            });
        }

    },

    populate_payment_type_info: function (doc, cdt, cdn) {

        var me = this;

        // To handel changes in plant and date
        if (cdt == "Indent") {
            var indent_items = doc.indent;
        }
        else {
            var indent_items = [frappe.get_doc(cdt, cdn)];
        }

        if (indent_items) {
            $.each(indent_items, function (index, indent_item) {

                if (indent_item.customer) {

                    return frappe.call({
                        method: "flows.flows.pricing_controller.get_customer_payment_info",
                        args: {
                            plant: doc.plant,
                            customer: indent_item.customer,
                            posting_date: doc.posting_date
                        },
                        callback: function (r) {
                            console.log("populate_payment_type_info callback");
                            if (!r.exc) {
                                console.log(r.message);

                                indent_item.sales_tax_type = r.message.sales_tax_type;
                                refresh_field("sales_tax_type", indent_item.name, indent_item.parentfield);
                                if (me.sales_tax_type) {
                                    me.sales_tax_type(indent_item, indent_item.doctype, indent_item.name);
                                }

                                indent_item.payment_type = r.message.payment_mode;
                                refresh_field("payment_type", indent_item.name, indent_item.parentfield);
                                if (me.payment_type) {
                                    me.payment_type(indent_item, indent_item.doctype, indent_item.name);
                                }

                            }
                        }
                    });

                }
            });
        }

    },

    // Compute amount per indent item
    compute_indent_item_amount: function (doc, cdt, cdn) {

        var indent_item = frappe.get_doc(cdt, cdn);
        // If Rate and Quantity is derived, compute amount
        if (indent_item.rate && indent_item.qty) {
            indent_item.amount = flt(indent_item.rate) * flt(indent_item.qty);
            refresh_field("amount", indent_item.name, indent_item.parentfield);
            if (this.amount) {
                this.amount(indent_item, indent_item.doctype, indent_item.name);
            }
        }

    },

    compute_totals: function (doc, cdt, cdn) {

        var indent = doc;
        if (doc.doctype == "Indent Item") {
            //parenttype: "Indent"
            //parent: "IOC00001"
            indent = frappe.get_doc(doc.parenttype, doc.parent)
        }

        var indent_items = indent.indent;

        var grand_total = 0;
        var total_payable_by_us = 0;

        $.each(indent_items, function (index, indent_item) {
            if (indent_item.amount) {
                grand_total += indent_item.amount;
                if (indent_item.payment_type && indent_item.payment_type != "Direct") {
                    total_payable_by_us += indent_item.amount;
                }
            }
        });

        // Update
        indent.grand_total = grand_total;
        indent.total_payable_by_us = total_payable_by_us;

        refresh_field("grand_total", indent.name, indent.parentfield);
        refresh_field("total_payable_by_us", indent.name, indent.parentfield);


        // Trigger hooks
        if (this.grand_total) {
            this.grand_total(indent, indent.doctype, indent.name);
        }
        if (this.total_payable_by_us) {
            this.total_payable_by_us(indent, indent.doctype, indent.name);
        }

    },

    load_type: function (doc, cdt, cdn) {
        var indent_item = frappe.get_doc(cdt, cdn);
        if (indent_item.load_type == 'Refill') {
            indent_item.eiv = '';
            refresh_field('eiv', indent_item.name, indent_item.parentfield);
        }
    },

    naming_series: function (doc, cdt, cdn) {
        var company = null;
        switch (doc.naming_series) {
            case 'IOC':
                company = 'Mosaic Enterprises Ltd.';
                break;
            case 'BPC':
                company = 'Ludhiana Enterprises Ltd.';
                break;
            case 'HPC':
                company = 'Alpine Energy';
                break;
        }

        if (!company) return;

        this.frm.set_value('company', company);

        if (this.company) {
            this.company(doc, cdt, cdn);
        }
    },

    company: function (doc, cdt, cdn) {
        this.frm.set_value('letter_head', doc.company);
    },

    custom_validate: function (doc) {
        eiv_map = {};

        $.each(doc.indent, function (index, indent_item) {
            if (indent_item.load_type == 'Oneway') {

                // Ensure every oneway load has an eiv
                if (!indent_item.eiv || indent_item.eiv == '') {
                    frappe.throw('EIV is mandatory for Oneway loads');
                }

                // Count EIVs
                eiv_map[indent_item.eiv] = 1 + (eiv_map[indent_item.eiv] || 0);
            } else {
                indent_item.eiv = '';
                refresh_field('eiv', indent_item.name, indent_item.parentfield);
            }
        });

        // Ensure EIV is used only once
        for (var key in eiv_map) {
            if (eiv_map[key] > 1) {
                frappe.throw('Same EIV cant be used across multiple loads');
            }
        }
    }

});

$.extend(cur_frm.cscript, new erpnext.flows.IndentController({frm: cur_frm}));