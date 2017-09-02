app_name = "flows"
app_title = "Flows"
app_publisher = "Arun Logistics"
app_description = "Implements custom workflows for Arun Logistics"
app_icon = "icon-book"
app_color = "#589494"
app_email = "bhupesh00gupta@gmail.com"
app_url = "No URL yet"
app_version = "0.0.1"

fixtures = [
	# "Custom Field",
	# "Supplier Type",
	# "Item Group",
	# "Warehouse",
	# "Item",
	# "Item Conversion",
	# "Workflow State",
	# "Workflow Action",
	# "Workflow",
	# "Letter Head",
	# "Print Heading",
	# "Print Format",
	# "Property Setter",
	# "Sales Taxes and Charges Master",
	# "Terms and Conditions"
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/flows/css/flows.css"
app_include_js = "/assets/js/flows.min.js"

# include js, css files in header of web template
# web_include_css = "/assets/flows/css/flows.css"
# web_include_js = "/assets/flows/js/flows.js"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# "Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "flows.install.before_install"
# after_install = "flows.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "flows.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.core.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.core.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Journal Voucher": {
		"autoname": "flows.flows.custom_validation.journal_voucher_autoname",
		"validate": "flows.flows.custom_validation.journal_voucher_validate"
	},
	"Contact": {
		"validate": "flows.flows.custom_validation.contact_validate_for_sms"
	},
	"GL Entry": {
		"on_submit": "flows.flows.custom_validation.validate_imprest_account_gl_entry_date",
	},
	"Customer": {
		"onload": "flows.flows.custom_validation.customer_onload"
	},
	"Indent Invoice": {
		"on_submit": "flows.flows.controller.ephesoft_integration.create_docs_in_review_server",
		"validate": "flows.flows.controller.autoinvoicing_controller.validate_invoice_number"
	},
	"Indent": {
		"on_submit": "flows.flows.controller.autoinvoicing_controller.save_and_submit_invoices"
	},
	"Sales Invoice": {
		"before_save": "flows.flows.custom_validation.validate_gst_number"
	}
}


# Scheduled Tasks
# ---------------

scheduler_events = {
	"all": [],
	"daily_long": [
		"flows.flows.controller.hpcl_controller.fetch_and_record_hpcl_balance"
	],
	"hourly": [
		"flows.flows.controller.hpcl_controller.update_invoice_status_for_pending_indents",
		"flows.flows.controller.iocl_controller.fetch_and_record_iocl_transactions_controller",
		"flows.flows.controller.autoinvoicing_controller.submit_indents"
	],
	"weekly": [],
	"monthly": []
}

# Testing
# -------

# before_tests = "flows.install.before_tests"

doctype_js = {
	"Warehouse": ["asserts/js/warehouse.js"],
	"Journal Voucher": ["c_scripts/journal_voucher.js"],
	"Customer": ["c_scripts/customer.js"],
	"Sales Invoice": ["c_scripts/sales_invoice.js"],
}

# Overriding Whitelisted Methods
# ------------------------------
#
override_whitelisted_methods = {
	"frappe.model.rename_doc.rename_doc": "flows.flows.customer.rename_doc",
    "frappe.templates.pages.print.download_pdf": "flows.flows.print.download_pdf"
}


boot_session = "flows.flows.startup_boot_info.boot_session"
startup_js = "flows.flows.startup_boot_info.get_startup_js"

jenv_filter = [
	'indent_refill_qty:flows.jinja_filters.indent_refill_qty',
	'indent_oneway_qty:flows.jinja_filters.indent_oneway_qty',
	'compute_erv_for_refill_in_indent:flows.jinja_filters.compute_erv_for_refill_in_indent',
	'get_contract_number:flows.jinja_filters.get_contract_number',
	'get_registration_code:flows.jinja_filters.get_registration_code',
	'get_customer_tin_number:flows.jinja_filters.get_customer_tin_number',
	'get_cenvat_status:flows.jinja_filters.get_cenvat_status',
	'get_address_display:flows.jinja_filters.get_address_display',
	'report_build_erv_item_map:flows.jinja_filters.report_build_erv_item_map',
	'get_item_qty_aggr_gatepass:flows.jinja_filters.get_item_qty_aggr_gatepass',
	'get_account_code:flows.jinja_filters.get_account_code',
	'get_address_display_name:flows.jinja_filters.get_address_display_name',
	'get_omc_item_mapped:flows.jinja_filters.get_omc_item_mapped',
	'get_rsp:flows.jinja_filters.get_rsp',
	'get_omc_so:flows.jinja_filters.get_omc_so',
	'get_name_rev:flows.jinja_filters.get_id_and_percision'
]
