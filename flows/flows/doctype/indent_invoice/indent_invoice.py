# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from flows.stdlogger import root

import frappe
import frappe.defaults
from flows import utils as flow_utils
from erpnext.controllers.selling_controller import StockController
from erpnext.accounts import utils as account_utils

from erpnext.accounts.party import get_party_account

from erpnext.accounts.general_ledger import make_gl_entries

from frappe.utils import today, now



class IndentInvoice(StockController):
    def __init__(self, *args, **kwargs):
        self.set_missing_values()
        super(IndentInvoice, self).__init__(*args, **kwargs)

    def on_submit(self):
        super(IndentInvoice, self).on_submit()

    def validate(self):
        return super(IndentInvoice, self).validate()

    def make_gl_entries(self, repost_future_gle=True):
        gl_entries = self.get_gl_entries()

        root.debug("Gl Entry Map: {}".format(gl_entries))

        if gl_entries:


            make_gl_entries(gl_entries, cancel=(self.docstatus == 2),
                            update_outstanding='Yes', merge_entries=False)

    def set_missing_values(self, *args, **kwargs):

        # self.transaction_date = self.indent_date

        self.customer = frappe.db.sql(
            """select customer from `tabIndent Item`
					where name = %s""", self.indent_item
        )[0]

        self.company, self.plant = frappe.db.sql(
            """select company, plant from `tabIndent`
					where docstatus = 1 and name = %s""", self.indent
        )[0]

        root.debug({
            "indent_item_name": self.indent_item,
            "indent_name": self.indent,
            "customer": self.customer,
            "company": self.company,
            "plant": self.plant
        })

        if not self.posting_date:
            self.posting_date = today()
        if not self.posting_time:
            self.posting_time = now()
        if not self.fiscal_year:
            self.fiscal_year = account_utils.get_fiscal_year(date=self.posting_date)[0]

        super(IndentInvoice, self).set_missing_values(*args, **kwargs)


    def cancel(self):
        super(IndentInvoice, self).cancel()
        self.make_gl_entries()
        root.debug("Canceled {}".format(self.name))

    def get_gl_entries(self, warehouse_account=None):

        gl_entries = []

        self.make_customer_gl_entry(gl_entries)

        # # merge gl entries before adding pos entries
        # gl_entries = merge_similar_entries(gl_entries)

        return gl_entries

    def make_customer_gl_entry(self, gl_entries):

        supplier_account = flow_utils.get_supplier_account(self.company, self.plant)

        root.debug({
            "plant_account": supplier_account,
        })

        customer_account = get_party_account(self.company, self.customer, "Customer")

        root.debug("plant account name {}".format(customer_account))

        root.debug(account_utils.get_fiscal_year(date=self.indent_date))

        if self.actual_amount:
            gl_entries.append(
                self.get_gl_dict({
                    "account": customer_account,
                    "against": supplier_account,
                    "debit": self.actual_amount,
                    "remarks": "Against Invoice Id {}".format(self.name),
                    "against_voucher": self.name,
                    "against_voucher_type": self.doctype,
                })
            )

            gl_entries.append(
                self.get_gl_dict({
                    "account": supplier_account,
                    "against": customer_account,
                    "credit": self.actual_amount,
                    "remarks": "Against Invoice Id {}".format(self.name),
                    "against_voucher": self.name,
                    "against_voucher_type": self.doctype,
                })
            )

    def get_gl_dict(self, args):
        """this method populates the common properties of a gl entry record"""
        gl_dict = frappe._dict({
            'company': self.company,
            'posting_date': self.posting_date,
            'voucher_type': self.doctype,
            'voucher_no': self.name,
            'aging_date': self.get("aging_date") or self.posting_date,
            'remarks': self.get("remarks"),
            'fiscal_year': self.fiscal_year,
            'debit': 0,
            'credit': 0,
            'is_opening': "No"
        })
        gl_dict.update(args)
        return gl_dict

    def get_indent(self, dict=False):
        if not self._indent:
            self._indent = frappe.get_doc("Indent", self.indent)
        return self._indent if dict else self._indent.name

    def get_indent_item(self, dict=False):
        if not self._indent_item:
            self._indent_item = frappe.get_doc("Indent Item", self.indent_name)
        return self._indent_item if dict else self._indent_item.name

    def get_sl_entry(self, args):
        sl_dict = frappe._dict(
            {
                "posting_date": self.posting_date,
                "posting_time": self.posting_time,
                "voucher_type": self.doctype,
                "voucher_no": self.name,
                "actual_qty": 0,
                "incoming_rate": 0,
                "company": self.company,
                "fiscal_year": self.fiscal_year,
                "is_cancelled": self.docstatus == 2 and "Yes" or "No"
            })

        sl_dict.update(args)

        return sl_dict


def get_indent_for_vehicle(doctype, txt, searchfield, start, page_len, filters):
    gatepass_sql = """
    SELECT name FROM `tabGatepass` WHERE vehicle = '{vehicle}' AND docstatus=1
    """.format(vehicle=filters["vehicle"])

    root.debug(gatepass_sql)

    gatepass_names = [x[0] for x in frappe.db.sql(gatepass_sql)]

    indent_sql = """
    SELECT name FROM `tabIndent` WHERE gatepass in {gatepass_names} and docstatus = "1"
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