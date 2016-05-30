frappe.ui.form.on_change("Journal Voucher", "voucher_type", function (frm) {
	set_clearance_date_state(frm);
});


frappe.ui.form.on_change("Journal Voucher", "refresh", function (frm) {

	var doc = frm.doc;
	var map_html_string = '';
	if (doc.receiving_file) {
		map_html_string += '<img src="' + doc.receiving_file + '"/><p>Indent Invoice</p>';
	}

	if (map_html_string) {
		$(frm.fields_dict['receiving_image'].wrapper).html('<div class="indentInvoiceReceivingImg">' + map_html_string + '</div>');
	} else {
		$(frm.fields_dict['receiving_image'].wrapper).html('');
	}
});

function set_clearance_date_state(frm) {
	frm.set_df_property(
		"clearance_date",
		"read_only",
		!(frm.doc.voucher_type == "Bank Voucher" || frm.doc.voucher_type == "Contra Voucher")
	);
}

