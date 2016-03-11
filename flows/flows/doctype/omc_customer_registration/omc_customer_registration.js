frappe.provide("erpnext.flows");

erpnext.flows.OmcCustomerRegistrationController = frappe.ui.form.Controller.extend({
	onload:function () {
		this.setup_queries();
	},

	setup_queries:function () {
		this.frm.set_query("sales_invoice_account", function (doc, cdt, cdn) {
			frappe.model.validate_missing(doc, "sales_invoice_company");
			return {
				filters:{
					company: doc.sales_invoice_company
				}
			};
		});

        this.frm.set_query("debit_account", "credit_accounts", function(doc, cdt, cdn) {
            var credit_ac_active_section = frappe.get_doc(cdt, cdn)
            return {
                filters: {
                    company: credit_ac_active_section.debit_account_company,
                }
            };
        });

        this.frm.set_query("credit_account", "credit_accounts", function(doc, cdt, cdn) {
            var credit_ac_active_section = frappe.get_doc(cdt, cdn)
            return {
                filters: {
                    company: credit_ac_active_section.credit_account_company,
                }
            };
        });
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.OmcCustomerRegistrationController({frm:cur_frm}));