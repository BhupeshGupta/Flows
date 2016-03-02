cur_frm.cscript.custom_refresh = function (doc, dt, dn) {
    $(cur_frm.fields_dict['omc_customer_list_html'].wrapper)
    .html(frappe.render(frappe.templates.omc_customer_variable_list, cur_frm.doc.__onload))
    .find(".btn-address").on("click", function () {
        new_doc("OMC Customer Variables");
    });
};