# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
	missing_map, books_map, max_missing = get_missing_map(filters)
	columns = get_columns(max_missing)

	data = []
	for missing_book in sorted(missing_map.keys()):
		book_ref = books_map[missing_book]
		missing_list = missing_map[missing_book]
		row = [
			book_ref.name,
			book_ref.warehouse,
			book_ref.issued_to
		]
		row.extend(missing_list)
		data.append(row)

	data = sorted(data, key = lambda x: (x[1], x[2]))

	return columns, data


def get_missing_map(filters=None):
	books = frappe.db.sql(
		"""
		SELECT name, warehouse, issued_to,
		serial_start, serial_end
		FROM `tabGoods Receipt Book` WHERE
		name NOT IN ("GBR#0-500") AND state != 'Closed/Received';
		""", as_dict=True)

	books_map = {}
	missing_map = {}

	max_missing = 0
	for book in books:
		books_map[book.name] = book

		data = frappe.db.sql("""
		SELECT goods_receipt_number FROM `tabGoods Receipt` WHERE docstatus = 1
		AND goods_receipt_number BETWEEN {} AND {};
		""".format(book.serial_start, book.serial_end))
		gr_list = [int(x[0]) for x in data if x[0].isnumeric()]

		if not gr_list:
			continue

		missing = sorted(set(xrange(min(gr_list), max(gr_list))) - set(gr_list))

		if missing:
			missing_map[book.name] = missing
			if len(missing) > max_missing:
				max_missing = len(missing)

	return missing_map, books_map, max_missing


def get_columns(max_missing):
	d = [
		"Book Id:Link/Goods Receipt Book:170",
		"Warehouse:Warehouse:150",
		"Issued To::100",
	]
	if max_missing > 0:
		d.extend(["Missing {}".format(i) for i in xrange(1, max_missing)])

	return d