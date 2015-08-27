frappe.provide("erpnext.flows");

erpnext.flows.CFromIndentInvoice = frappe.ui.form.Controller.extend({
	onload:function () {
		this.setup_queries();
	},

	setup_queries:function () {
		this.frm.set_query("supplier", function (doc, cdt, cdn) {
			frappe.model.validate_missing(doc, "customer");
			frappe.model.validate_missing(doc, "quarter");
			frappe.model.validate_missing(doc, "fiscal_year");
			return {
				query:"flows.flows.doctype.c_form_indent_invoice.c_form_indent_invoice.get_supplier_list",
				filters:{
					'fiscal_year': doc.fiscal_year,
					'quarter': doc.quarter,
					'customer': doc.customer
				}
			};
		})
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.CFromIndentInvoice({frm:cur_frm}));