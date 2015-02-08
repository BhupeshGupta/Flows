# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe.model.document import Document

import frappe
from frappe.utils import today, now
from erpnext.accounts.utils import get_fiscal_year
from flows import utils
from frappe.model.naming import make_autoname


class Gatepass(Document):
    def autoname(self):
        name_series = 'GP+.DD.MM.YY.###'
        self.name = make_autoname(name_series)
        self.name = self.name.replace('+', self.dispatch_destination[0].upper())
        self.name = '{}-{}'.format(self.name, self.gatepass_type)

    def on_submit(self):
        self.transfer_stock()

    def on_cancel(self):
        self.transfer_stock()

    def transfer_stock(self):

        self.set_missing_values()

        from flows import utils as flow_utils

        stock_owner = flow_utils.get_stock_owner_via_sales_person_tree(self.driver)
        stock_owner = stock_owner if stock_owner else self.vehicle

        stock_owner_act = utils.get_or_create_vehicle_stock_account(stock_owner, self.company)
        stock_owner_act_name = stock_owner_act.name

        sl_entries = []

        for d in self.items:
            sl_entries.append(
                self.get_sl_entry({
                    "item_code": d.item,
                    "actual_qty": -1 * d.quantity,
                    "warehouse": self.warehouse if self.gatepass_type.lower() == 'out' else
                    stock_owner_act_name
                })
            )

            sl_entries.append(
                self.get_sl_entry({
                    "item_code": d.item,
                    "actual_qty": 1 * d.quantity,
                    "warehouse": self.warehouse if self.gatepass_type.lower() == 'in' else
                    stock_owner_act_name
                })
            )

        from erpnext.stock.stock_ledger import make_sl_entries

        make_sl_entries(sl_entries)

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

    def set_missing_values(self):
        for fieldname in ["posting_date", "posting_time" "transaction_date"]:
            if not self.get(fieldname):
                self.set(fieldname, today())

        if not self.get("fiscal_year"):
            self.fiscal_year = get_fiscal_year(today())[0]

        if not self.get("posting_time"):
            self.posting_time = now()