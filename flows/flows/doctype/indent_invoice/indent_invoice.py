# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

from flows.stdlogger import root


class IndentInvoice(Document):
    pass


def get_indent_for_vehicle(doctype, txt, searchfield, start, page_len, filters):
    gatepass_sql = """
    SELECT name FROM `tabGatepass` WHERE vehicle = '{vehicle}'
    """.format(vehicle=filters["vehicle"])

    root.debug(gatepass_sql)

    gatepass_names = [x[0] for x in frappe.db.sql(gatepass_sql)]

    indent_sql = """
    SELECT name FROM `tabIndent` WHERE gatepass in {gatepass_names}
    """.format(gatepass_names="({})".format(",".join(["'{}'".format(x) for x in gatepass_names])))

    root.debug(indent_sql)

    indent_names = [x[0] for x in frappe.db.sql(indent_sql)]

    if not indent_names:
        return []

    indent_items_sql = """select name, customer
        from `tabIndent Item`
		where parent in {indent_names}
		and {search_key} like "{search_val}%"
		order by customer asc limit {start}, {page_len}""".format(
        indent_names="({})".format(",".join(["'{}'".format(x) for x in indent_names])),
        start=start,
        page_len=page_len,
        search_key=searchfield,
        search_val=txt)

    root.debug(indent_items_sql)

    indent_item_names = [x[0] for x in frappe.db.sql(indent_items_sql)]

    indent_items = frappe.db.sql(indent_items_sql)

    indent_items_attached_to_invoice_sql = """select indent_item
        from `tabIndent Invoice`
		where indent_item in {indent_names}
		and vehicle = '{vehicle}'""".format(
        indent_names="({})".format(",".join(["'{}'".format(x) for x in indent_item_names])),
        vehicle=filters["vehicle"]
    )

    root.debug(indent_items_attached_to_invoice_sql)

    indent_items_already_attached_to_invoice = [x[0] for x in frappe.db.sql(indent_items_attached_to_invoice_sql)]

    indent_items_pending_for_invoice_attach_process = []

    for x in indent_items:
        if x[0] not in indent_items_already_attached_to_invoice:
            indent_items_pending_for_invoice_attach_process.append(x)

    return indent_items_pending_for_invoice_attach_process