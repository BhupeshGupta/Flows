# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import throw, _


class GoodsReceiptBook(Document):
    def autoname(self):
        self.name = 'GBR#{}-{}'.format(self.serial_start, self.serial_end)

    def validate(self):

        verify_book_query = """
        SELECT name FROM `tabGoods Receipt Book` where serial_start <= {0} and serial_end >= {0}
        """

        book = frappe.db.sql(verify_book_query.format(self.serial_start))

        if len(book) > 0:
            throw(
                _("Invalid {position} serial. Receipt book {book} already include this {position} serial {serial}").
                format(position="start", book=book[0][0], serial=self.serial_start)
            )

        book = frappe.db.sql(verify_book_query.format(self.serial_end))

        if len(book) > 0:
            throw(
                _("Invalid {position} serial. Receipt book {book} already include this {position} serial {serial}").
                format(position="end", book=book[0][0], serial=self.serial_end)
            )

    def on_trash(self):
        verify_book_query = """
        SELECT name FROM `tabGoods Receipt` where goods_receipt_number >= {start} and goods_receipt_number <= {end}
        """.format(start=self.serial_start, end=self.serial_end)

        receipt = frappe.db.sql(verify_book_query)

        if len(receipt) > 0:
            throw(
                _("{} Goods Receipt are associated with this book, can not delete").
                format(len(receipt))
            )