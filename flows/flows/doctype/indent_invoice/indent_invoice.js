frappe.provide("erpnext.flows");

erpnext.flows.IndentInvoice = frappe.ui.form.Controller.extend({
    onload: function () {
        this.setup_queries();
        this.set_fields(this.frm.doc, null, null);
    },

    content_url: function (url) {
        url = url.split("proxy/alfresco/api/node/");
        url[1].replace("/", "://");
        url = url[0] + 'page/site/receivings/document-details?nodeRef=' + url[1];
        url = url.split("/content/thumbnails/imgpreview");
        url = url[0];
        console.log(url);
        return url;
    },

    refresh: function () {
        var doc = this.frm.doc;
        var map_html_string = '';
        vm = this;
        if (doc.receiving_file) {
            map_html_string +=
            '<a target="_blank" href="' + this.content_url(doc.receiving_file) + '">'+
                '<img src="' + doc.receiving_file + '"/><p>Indent Invoice</p>' +
            '</a>';
        }

        if (doc.data_bank) {

            var dataBank = JSON.parse(doc.data_bank);

            if (dataBank.receivings) {
                $.each(dataBank.receivings, function(key, value) {
                    map_html_string +='<a target="_blank" href="' + vm.content_url(value) +'">'+'<img src="' + value + '"/><p>' + key + '</p>'+ '</a>';
                    console.log(key, value)
                });
            }

        }

        if (map_html_string) {
			$(this.frm.fields_dict['receiving_image'].wrapper).html('<div class="indentInvoiceReceivingImg">' + map_html_string + '</div>');
		} else {
			$(this.frm.fields_dict['receiving_image'].wrapper).html('');
		}

	    me.frm.set_df_property("invoice_number", "hidden", cur_frm.doc.amended_from);

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
    },

	validate: function (doc, cdt, cdn) {
		var lease = 0;
		if (doc.invoice_number.match(/-/gi)) {
			frappe.throw("Invoice Number can not contain dash (-).");
		}
		if (doc.invoice_number.match(/\//gi)) {
			lease += 2;
		}

		// HPCL -> 08
		// IOCL -> 09
		// BPCL -> 10
		var invoice_no_len = doc.invoice_number.split("/")[0].length;

		if (doc.supplier.match(/hpcl/gi) && invoice_no_len != 8 + lease) {
			frappe.throw("Please check invoice number. HPCL invoice numbers length should be 8 or 10.");
		} else if (doc.supplier.match(/iocl/gi) && invoice_no_len != 9 + lease) {
			frappe.throw("Please check invoice number. IOCL invoice numbers length should be 9 or 11.");
		} else if (doc.supplier.match(/bpcl/gi) && invoice_no_len != 10 + lease) {
			frappe.throw("Please check invoice number. BPCL invoice numbers length should be 10 or 12.");
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