frappe.listview_settings['Indent Invoice'] = {
	onload: function(me) {
		console.log(frappe.route_options);
		frappe.route_options = {
			"docstatus": ["!=", "2"],
			"customer": ["!=", "Alpine Energy"]
		};
	}
}

