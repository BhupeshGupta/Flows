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
                    "name": "Item Conversion",
                    "description": _("Quantity of gas in an Item.")
                }
            ]
        },
    ]
