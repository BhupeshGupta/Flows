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
					"name": "Cash Receipt",
					"description": _("Cash Sale")
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
			"label": _("Main Reports"),
			"icon": "icon-table",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Flows Stock Ledger",
					"doctype": "Item",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Flows Stock Balance",
					"doctype": "Item",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Flows Empty Report",
					"doctype": "Item",
				},
			    {
					"type": "report",
					"is_query_report": True,
					"name": "Filled Ledger",
					"doctype": "Item",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Flows Invoice Report",
					"doctype": "Item",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Transportation Report",
					"doctype": "Item",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "C Form Report",
					"doctype": "Item",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "C Form Analytics",
					"doctype": "Item",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Fuel Report",
					"doctype": "Item",
				},
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
