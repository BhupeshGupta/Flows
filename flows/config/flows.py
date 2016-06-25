from frappe import _


def get_data():
	return [
		{
			"label": _("Documents"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Gatepass",
					"description": _("Gatepass and ERVs")
				},
				{
					"type": "doctype",
					"name": "Indent",
					"description": _("Indent raised to Gas Plants.")
				},
				{
					"type": "doctype",
					"name": "Indent Invoice",
					"description": _("Invoice raised by Gas Plants in name fo Customers.")
				},
				{
					"type": "doctype",
					"name": "Goods Receipt",
					"description": _("Delivery Notes")
				},
				{
					"type": "doctype",
					"name": "Payment Receipt",
					"description": _("Payment Receipt(PR) Voucher")
				},
				{
					"type": "doctype",
					"name": "C Form Indent Invoice",
					"description": _("C Form Collection On Behalf Of OMC")
				},
				{
					"type": "doctype",
					"name": "Customer",
					"description": _("Customer database.")
				},
				{
					"type": "doctype",
					"name": "Supplier",
					"description": _("Supplier database.")
				}
			]
		},
		{
			"label": _("Tools"),
			"icon": "icon-wrench",
			"items": [
				{
					"type": "doctype",
					"name": "Vendor Gatepass Tool",
					"description": _("Create vendor gatepassed in bulk")
				},
				{
					"type": "doctype",
					"name": "Indent Invoice Customer Change Tool",
					"description": _("Change customer in indent as well as in invoice")
				},
				{
					"type": "doctype",
					"name": "Payment Mode Change Tool",
					"description": _("")
				}
			]
		},
		{
			"label": _("Equipment Docs"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Equipment Issue Voucher",
					"description": _("")
				}
			]
		},
		{
			"label": _("Enrollment Docs"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "OMC Customer Variables",
					"description": _("")
				}
			]
		},
		{
			"label": _("Main Reports"),
			"icon": "icon-table",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Flows Stock Ledger",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Flows Stock Balance",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Flows Empty Report",
				},
			    {
					"type": "report",
					"is_query_report": True,
					"name": "Filled Ledger",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Customer Stock Register",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase Sale",
				}
			]
		},
	    {
			"label": _("Stock Reports"),
			"icon": "icon-table",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Register",
					"doctype": "Gatepass",
				}
			]
		},
		 {
			"label": _("Daily Status"),
			"icon": "icon-table",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "GR Missing Report",
					"doctype": "Goods Receipt",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase Cycle Report",
					"doctype": "Indent",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "GR Summary",
					"doctype": "Goods Receipt",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Daily GR Report",
					"doctype": "Goods Receipt",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vendor Report",
					"doctype": "Gatepass",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Bill Tracking",
					"doctype": "Indent Invoice",
				}
			]
		},
		{
			"label": _("Monthly Reports"),
			"icon": "icon-table",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "HPCL Incentive",
					"doctype": "Indent Invoice",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "IOCL Incentive",
					"doctype": "Indent Invoice",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "IOCL Discount",
					"doctype": "Indent Invoice",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Transportation Report",
					"doctype": "Gatepass",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Fuel Report",
					"doctype": "Gatepass",
				}
			]
		},
		{
			"label": _("Quarterly Reports"),
			"icon": "icon-table",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "C Form Report",
					"doctype": "Indent Invoice",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "C Form Analytics",
					"doctype": "Indent Invoice",
				},
			]
		},
		{
			"label": _("Setup"),
			"icon": "icon-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Plant Rate",
					"description": _("Base rate of Gas Plants")
				},
				{
					"type": "doctype",
					"name": "Customer Plant Variables",
					"description": _("Values specific to Customer and Plant.")
				},
				{
					"type": "doctype",
					"name": "Route Cost",
					"description": _("Cost for a route")
				},
				{
					"type": "doctype",
					"name": "Goods Receipt Book",
					"description": _("Invoice raised by Gas Plants in name fo Customers.")
				},
				{
					"type": "doctype",
					"name": "Item Conversion",
					"description": _("Quantity of gas in an Item.")
				},
				{
					"type": "doctype",
					"name": "Customer Landed Rate",
				}
			]
		},
	]
