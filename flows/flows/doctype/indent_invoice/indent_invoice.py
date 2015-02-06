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
        super(IndentInvoice, self).__init__(*args, **kwargs)

    def on_submit(self):
        super(IndentInvoice, self).on_submit()
        self.make_gl_entries()

    def validate(self):
        return super(IndentInvoice, self).validate()

    def make_gl_entries(self, repost_future_gle=True):
        gl_entries = self.get_gl_entries()

        root.debug("Gl Entry Map: {}".format(gl_entries))

        if gl_entries:


            make_gl_entries(gl_entries, cancel=(self.docstatus == 2),
                            update_outstanding='Yes', merge_entries=False)

    def set_missing_values(self, *args, **kwargs):

        super(IndentInvoice, self).set_missing_values(*args, **kwargs)

        sql = """
select company, plant
from `tabIndent`
where docstatus = 1 and
name = '{}'""".format(self.indent)

        root.debug(str((self.indent, self.indent_item)))

        self.company, self.plant = frappe.db.sql(sql)[0]

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

        self.set_missing_values()

        supplier_account = flow_utils.get_supplier_account(self.company, self.plant)

        root.debug({
            "plant_account": supplier_account,
        })

        customer_account = get_party_account(self.company, self.customer, "Customer")

        root.debug("plant account name {}".format(customer_account))

        root.debug(account_utils.get_fiscal_year(date=self.posting_date))

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
    indent_items_sql = """select name, customer
        from `tabIndent Item`
		where parent in (select name from tabIndent where vehicle = "{vehicle}" and docstatus = 1)
		and {search_key} like "{search_val}%"
		and name not in (select indent from `tabIndent Invoice` where docstatus = 1)
		order by customer asc limit {start}, {page_len}""".format(
        vehicle=filters["vehicle"],
        start=start,
        page_len=page_len,
        search_key=searchfield,
        search_val=txt
    )

    return frappe.db.sql(indent_items_sql)