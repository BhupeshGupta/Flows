frappe.ui.form.on_change("Journal Voucher", "voucher_type", function (frm) {
	set_clearance_date_state(frm);
});


frappe.ui.form.on_change("Journal Voucher", "onload", function (frm) {
	set_clearance_date_state(frm);
});

function set_clearance_date_state(frm) {
	frm.set_df_property(
		"clearance_date",
		"read_only",
		!(frm.doc.voucher_type == "Bank Voucher" || frm.doc.voucher_type == "Contra Voucher")
	);
}

