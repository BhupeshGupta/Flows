frappe.provide("erpnext.flows");

erpnext.flows.PlantRateController = frappe.ui.form.Controller.extend({
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
    }

});

$.extend(cur_frm.cscript, new erpnext.flows.PlantRateController({frm: cur_frm}));