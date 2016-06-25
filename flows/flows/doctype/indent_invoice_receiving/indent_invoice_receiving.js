frappe.provide("erpnext.flows");

erpnext.flows.IndentInvoiceReceiving = frappe.ui.form.Controller.extend({
	onload:function () {
		this.setup_queries();
	},

	setup_queries:function () {
		this.frm.set_query("indent_invoice", "entries", function () {
			return {
				filters:{'docstatus':'1'}
			}
		});
	},

	indent_invoice:function (doc, cdt, cdn) {
		var me = this;
		var invoice_item = frappe.get_doc(cdt, cdn);
		invoice_item.checked = '';
		refresh_field("checked", invoice_item.name, invoice_item.parentfield);
	},

	//handling:function (doc, cdt, cdn) {
	//	var invoice_item = frappe.get_doc(cdt, cdn);
	//	if (invoice_item.workflow_state != 'Unchecked') {
	//		frappe.throw("You can not change Handling after invoice is checked!");
	//	}
	//},
	//
	//excise:function (doc, cdt, cdn) {
	//	var invoice_item = frappe.get_doc(cdt, cdn);
	//	if (invoice_item.workflow_state == 'Ok') {
	//		frappe.throw("You can not change Excise after invoice is checked!");
	//	}
	//},
	//
	//cst:function (doc, cdt, cdn) {
	//	var invoice_item = frappe.get_doc(cdt, cdn);
	//	if (invoice_item.workflow_state != 'Unchecked') {
	//		frappe.throw("You can not change CST after invoice is checked!");
	//	}
	//},

	print_consignment_note:function (doc, cdt, cdn) {

		var names = [];
		$.each(doc.entries, function (index, value) {
			//if (value.printable == 1) {
				names.push(value.transportation_invoice);
			//}
		});

		var name = '["' + names.join('","') + '"]';

		var w = window.open("/api/method/frappe.templates.pages.print.download_pdf?"
		+ "doctype=" + encodeURIComponent('Sales Invoice')
		+ "&name=" + encodeURIComponent(name)
		+ "&format=" + encodeURIComponent('Consignment Note')
		+ "&no_letterhead=0");
		if (!w) {
			msgprint(__("Please enable pop-ups"));
			return;
		}
	}

});


$.extend(cur_frm.cscript, new erpnext.flows.IndentInvoiceReceiving({frm:cur_frm}));

cur_frm.add_fetch('indent_invoice', 'customer', 'customer');
cur_frm.add_fetch('indent_invoice', 'transaction_date', 'invoice_date');
cur_frm.add_fetch('indent_invoice', 'actual_amount', 'amount');
cur_frm.add_fetch('indent_invoice', 'qty', 'qty');
cur_frm.add_fetch('indent_invoice', 'item', 'item');
cur_frm.add_fetch('indent_invoice', 'handling_charges', 'handling');
cur_frm.add_fetch('indent_invoice', 'cst', 'cst');
cur_frm.add_fetch('indent_invoice', 'excise', 'excise');
cur_frm.add_fetch('indent_invoice', 'printable', 'printable');
cur_frm.add_fetch('indent_invoice', 'workflow_state', 'workflow_state');
cur_frm.add_fetch('indent_invoice', 'cenvat', 'cenvat');
cur_frm.add_fetch('indent_invoice', 'transportation_invoice', 'transportation_invoice');
