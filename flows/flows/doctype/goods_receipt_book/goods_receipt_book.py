# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import throw, _, msgprint
from flows.flows.report.gr_missing_report.gr_missing_report import get_missing_map

class GoodsReceiptBook(Document):
	def autoname(self):
		self.name = 'GBR#{}-{}'.format(self.serial_start, self.serial_end)

	def validate(self):

		verify_book_query = """
        SELECT name FROM `tabGoods Receipt Book` where serial_start <= {0} and serial_end >= {0} and name != "{1}"
        """

		book = frappe.db.sql(verify_book_query.format(self.serial_start, self.name))

		if len(book) > 0:
			throw(
				_("Invalid {position} serial. Receipt book {book} already include this {position} serial {serial}").
				format(position="start", book=book[0][0], serial=self.serial_start)
			)

		book = frappe.db.sql(verify_book_query.format(self.serial_end, self.name))

		if len(book) > 0:
			throw(
				_("Invalid {position} serial. Receipt book {book} already include this {position} serial {serial}").
				format(position="end", book=book[0][0], serial=self.serial_end)
			)

		missing_map, books_map, max_missing = get_missing_map()

		from flows.stdlogger import root
		root.debug(missing_map)

		if self.state == "Closed/Received" and self.name in missing_map:
			msg = "{} GRs are missing in this book.".format(len(missing_map[self.name]))
			if frappe.session.user == "Administrator":
				msgprint(msg)
			else:
				throw(msg + "Did not not close")

		book_in_db = frappe.get_doc("Goods Receipt Book", self.name)

		if book_in_db.state == "Closed/Received" and self.state != "Closed/Received":
			if frappe.session.user == "Administrator":
				msgprint("Book reopened")
			else:
				throw("Can not open closed books. Please contact administrator")


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