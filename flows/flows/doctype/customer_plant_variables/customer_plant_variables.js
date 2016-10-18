frappe.provide("erpnext.flows");

erpnext.flows.CustomerPlantVariables = frappe.ui.form.Controller.extend({
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
    },

    refresh: function() {
	    var vm = this;
        this.frm.add_custom_button(__("Validate With OMC"), function() {
            frappe.call({
	            "method": "flows.flows.doctype.customer_plant_variables.customer_plant_variables.validate_variables_with_omc",
	            args: {
	                cpv: vm.frm.doc,
	            },
	            callback: function (data) {
	                console.log(data);
		            if (data.message) {
			            msgprint(data.message, "Mismatch")
		            } else {
			            msgprint("Pricing is correct")
		            }
	            }
	        })
		});
    }

});

$.extend(cur_frm.cscript, new erpnext.flows.CustomerPlantVariables({frm: cur_frm}));

cur_frm.add_fetch('omc_policy', 'discount', 'discount');
cur_frm.add_fetch('omc_policy', 'discount_via_credit_note', 'discount_via_credit_note');
cur_frm.add_fetch('omc_policy', 'incentive', 'incentive');
cur_frm.add_fetch('omc_policy', 'dcn_ba_benefit', 'dcn_ba_benefit');
