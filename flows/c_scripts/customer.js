cur_frm.cscript.custom_refresh = function (doc, dt, dn) {
    if(doc.__islocal) {
		hide_field(['omc_customer_list_html']);
	} else {
		unhide_field(['omc_customer_list_html']);
		// make lists
        var template = $(cur_frm.fields_dict['omc_customer_list_html'].wrapper)
        .html(frappe.render(frappe.templates.omc_customer_variable_list, cur_frm.doc.__onload));
        template.find("#omccr.btn-address").on("click", function () {
            new_doc("OMC Customer Registration");
        });
        template.find("#cpv.btn-address").on("click", function () {
            new_doc("Customer Plant Variables");
        });
	}

	cur_frm.cscript.service_tax_liability(doc, dt, dn);
	cur_frm.cscript.cenvat(doc, dt, dn);
};

cur_frm.cscript.cenvat = function (doc, dt, dn) {
    this.frm.set_df_property("ecc_number", "reqd", doc.cenvat == 1);
    this.frm.set_df_property("excise_commissionerate_code", "reqd", doc.cenvat == 1);
    this.frm.set_df_property("excise_range_code", "reqd", doc.cenvat == 1);
    this.frm.set_df_property("excise_division_code", "reqd", doc.cenvat == 1);
};

cur_frm.cscript.service_tax_liability = function (doc, dt, dn) {
    this.frm.set_df_property("service_tax_number", "reqd", doc.service_tax_liability == "Consignee(Customer)");
};

