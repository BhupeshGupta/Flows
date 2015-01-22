frappe.provide("erpnext.flows");

erpnext.flows.IndentInvoice = frappe.ui.form.Controller.extend({
    onload: function () {
        this.setup_queries();
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

        this.frm.set_query("indent_item", function (doc, cdt, cdn) {

            frappe.model.validate_missing(doc, "vehicle");

            return {
                query: "flows.flows.doctype.indent_invoice.indent_invoice.get_indent_for_vehicle",
                filters: { vehicle: doc.vehicle },
                searchfield: "customer"
            };
        });
    }

});

$.extend(cur_frm.cscript, new erpnext.flows.IndentInvoice({frm: cur_frm}));