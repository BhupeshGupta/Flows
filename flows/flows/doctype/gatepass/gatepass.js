frappe.provide("erpnext.flows");

erpnext.flows.GatepassController = frappe.ui.form.Controller.extend({
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

    set_pump_query: function (field) {
        if (this.frm.fields_dict[field]) {
            this.frm.set_query(field, function () {
                return{
                    filters: { 'supplier_type': 'Fuel Pump' }
                }
            });
        }
    },

    setup_queries: function () {
        this.set_plant_query("plant");
        this.set_pump_query("fuel_pump");
    }

});

$.extend(cur_frm.cscript, new erpnext.flows.GatepassController({frm: cur_frm}));