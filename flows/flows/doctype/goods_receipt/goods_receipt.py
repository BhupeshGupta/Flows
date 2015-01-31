# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _, throw
from flows import utils
from frappe.utils import today, now
from erpnext.accounts.utils import get_fiscal_year


class GoodsReceipt(Document):
    def validate(self):

        verify_book_query = """
        SELECT name FROM `tabGoods Receipt Book` where serial_start <= {0} and serial_end >= {0}
        """.format(self.goods_receipt_number)

        if len(frappe.db.sql(verify_book_query)) == 0:
            throw(
                _("Invalid serial. Can not find any receipt book for this serial {}").format(self.goods_receipt_number)
            )

    def on_submit(self):
        self.transfer_stock()

    def on_cancel(self):
        self.transfer_stock()

    def transfer_stock(self):
        from erpnext.stock.stock_ledger import make_sl_entries

        self.set_missing_values()

        transportation_vehicle_warehouse = utils.get_or_create_vehicle_stock_account(self.vehicle, self.company)
        transportation_vehicle_warehouse_name = transportation_vehicle_warehouse.name

        # TODO: write a method to find the same
        customer_warehouse_name = utils.get_or_create_customer_stock_account(self.customer, self.company).name

        sl_entries = []

        if self.item_delivered and self.delivered_quantity:
            sl_entries.append(
                self.get_sl_entry({
                    "item_code": self.item_delivered,
                    "actual_qty": -1 * self.delivered_quantity,
                    "warehouse": transportation_vehicle_warehouse_name
                })
            )

            sl_entries.append(
                self.get_sl_entry({
                    "item_code": self.item_delivered,
                    "actual_qty": self.delivered_quantity,
                    "warehouse": customer_warehouse_name
                })
            )

        if self.item_received and self.received_quantity:

            if self.item_received.startswith('E'):

                empty_cylinders_available_at_customers_warehouse = frappe.db.sql("""
                select sum(actual_qty) as current_quantity from `tabStock Ledger Entry` where docstatus < 2
                and item_code="{}" and warehouse="{}";
                """.format(self.item_received, customer_warehouse_name), as_dict=1)[0]['current_quantity']

                empty_cylinders_available_at_customers_warehouse = empty_cylinders_available_at_customers_warehouse \
                    if empty_cylinders_available_at_customers_warehouse else 0

                filled_cylinders_available_at_customers_warehouse = frappe.db.sql("""
                select sum(actual_qty) as current_quantity from `tabStock Ledger Entry` where docstatus < 2
                and item_code="{}" and warehouse="{}";
                """.format(self.item_received.replace('E', 'F'), customer_warehouse_name), as_dict=1)[0][
                    'current_quantity']

                filled_cylinders_available_at_customers_warehouse = filled_cylinders_available_at_customers_warehouse \
                    if filled_cylinders_available_at_customers_warehouse else 0

                new_empty_cylinder_quantity = empty_cylinders_available_at_customers_warehouse - self.received_quantity

                if new_empty_cylinder_quantity < 0:
                    cylinders_consumed_from_last_gr_entry = min(
                        -1 * new_empty_cylinder_quantity,
                        filled_cylinders_available_at_customers_warehouse
                    )
                else:
                    cylinders_consumed_from_last_gr_entry = 0

                if cylinders_consumed_from_last_gr_entry > 0:

                    for sl_e in self.convert_items_empty_in_place(
                            self.item_received.replace('E', 'F'),
                            self.item_received,
                            cylinders_consumed_from_last_gr_entry,
                            customer_warehouse_name
                    ):
                        sl_e['process'] = 'Consumption'
                        sl_entries.append(sl_e)

            sl_entries.append(
                self.get_sl_entry({
                    "item_code": self.item_received,
                    "actual_qty": -1 * self.received_quantity,
                    "warehouse": customer_warehouse_name
                })
            )

            sl_entries.append(
                self.get_sl_entry({
                    "item_code": self.item_received,
                    "actual_qty": 1 * self.received_quantity,
                    "warehouse": transportation_vehicle_warehouse_name
                })
            )

        make_sl_entries(sl_entries)

    def convert_items_empty_in_place(self, from_item, to_item, item_quantity, in_warehouse):
        conversion_sl_entries = []

        conversion_sl_entries.append(
            self.get_sl_entry({
                "item_code": from_item,
                "actual_qty": -1 * item_quantity,
                "warehouse": in_warehouse
            })
        )
        conversion_sl_entries.append(

            self.get_sl_entry({
                "item_code": to_item,
                "actual_qty": 1 * item_quantity,
                "warehouse": in_warehouse
            })
        )

        return conversion_sl_entries

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