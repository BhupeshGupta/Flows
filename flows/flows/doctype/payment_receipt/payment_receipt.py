# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from flows import utils
from frappe.model.document import Document

from flows.stdlogger import root

from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.stock.stock_ledger import make_sl_entries
from frappe import _, throw


class PaymentReceipt(Document):
	def __init__(self, *args, **kwargs):
		super(PaymentReceipt, self).__init__(*args, **kwargs)
		self.set_missing_values()

	def validate_book(self):
		if not self.id: return
		if not self.id.isdigit(): throw("ID needs to be a number, Please check the serial on PR receipt.")

		verify_book_query = """
		SELECT * FROM `tabGoods Receipt Book` WHERE serial_start <= {0} AND serial_end >= {0}
		""".format(self.id)

		rs = frappe.db.sql(verify_book_query, as_dict=True)

		if len(rs) == 0:
			throw(
				_("Invalid serial. Can not find any receipt book for this serial {}").format(self.id)
			)
		elif utils.cint(rs[0].pr_enabled) == 0:
			throw(
				_("Receipt Book ({} - {}) Is Not Marked For PR. Please Contact Book Manager").
					format(rs[0].serial_start, rs[0].serial_end)
			)
		elif rs[0].state == "Closed/Received":
			throw(
				_("PR Book has been closed, amendment prohibited").format(self.id)
			)

		self.debit_account = rs[0].pr_debit


	def validate_unique(self):
		rs = frappe.db.sql("select name from `tabGoods Receipt` where name=\"{0}\" or name like \"{0}-%\"".format(self.id))
		if len(rs) > 0:
			throw("Goods Receipt with this serial already exists {}".format(self.id))

	def validate(self):
		# if self.amended_from:
		# return
		self.validate_book()
		self.validate_unique()

	def autoname(self):
		if self.id and self.id != '':
			self.name = self.id

	def on_submit(self):
		self.make_gl_entry()
		self.transfer_stock()

	def on_update_after_submit(self):
		from flows.stdlogger import root

		root.debug("on_update_after_submit")
		self.transfer_stock(is_cancelled='Yes')
		if self.stock_date != '':
			root.debug("stock_date update")
			self.transfer_stock()

	def on_cancel(self):
		self.make_gl_entry()
		self.transfer_stock(is_cancelled='Yes')

	def transfer_stock(self, is_cancelled=None):

		if not self.stock_date or self.stock_date.strip() == '':
			return

		is_cancelled = is_cancelled if is_cancelled is not None else (self.docstatus == 2 and "Yes" or "No")

		stock_owner = utils.get_stock_owner_via_sales_person_tree(self.stock_owner)
		stock_owner_warehouse = utils.get_or_create_warehouse(stock_owner, self.stock_owner_company)

		sl_entries = []

		if self.transaction_type in ("Refill", "New Connection"):
			sl_entries.append(
				self.get_sl_entry({
				"item_code": self.item,
				"actual_qty": -1 * self.qty,
				"warehouse": stock_owner_warehouse.name,
				"process": self.transaction_type,
				"is_cancelled": is_cancelled,
				"posting_date": self.stock_date,
				})
			)

		# if refill sale or tv-out
		if self.transaction_type in ('Refill', 'TV Out'):
			sl_entries.append(
				self.get_sl_entry({
				"item_code": self.item.replace('F', 'E'),
				"actual_qty": self.qty,
				"warehouse": stock_owner_warehouse.name,
				"process": self.transaction_type,
				"is_cancelled": is_cancelled,
				"posting_date": self.stock_date,
				})
			)

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
			"company": self.stock_owner_company,
			"fiscal_year": self.fiscal_year,
			})

		sl_dict.update(args)
		return sl_dict

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

	def make_gl_entry(self):

		gl_entries = []

		company_abbr = frappe.db.get_value(
			"Company", self.company, "abbr"
		)

		owners_account = self.debit_account
		sales_account = 'Sales - {}'.format(company_abbr)

		cost_center = 'Main - {}'.format(company_abbr)

		assert_dr_or_cr = "debit" if self.transaction_type in ("Refill", "New Connection") else "credit"
		sales_dr_or_cr = "debit" if assert_dr_or_cr == "credit" else "credit"

		if self.total:
			gl_entries.append(
				self.get_gl_dict({
				"account": owners_account,
				assert_dr_or_cr: self.total,
				"remarks": "{qty}x{amount_per_item} [{stock_owner}] [CR {cr_id}({txn_type})]".format(
					qty=self.qty,
					amount_per_item=self.amount_per_item,
					stock_owner=self.stock_owner,
					cr_id=self.name,
					txn_type=self.transaction_type
				),
				})
			)

			gl_entries.append(
				self.get_gl_dict({
				"account": sales_account,
				sales_dr_or_cr: self.total,
				"cost_center": cost_center,
				"remarks": "{qty}x{amount_per_item} [{stock_owner}] [CR {cr_id}({txn_type})]".format(
					qty=self.qty,
					amount_per_item=self.amount_per_item,
					stock_owner=self.stock_owner,
					cr_id=self.name,
					txn_type=self.transaction_type
				),
				})
			)

		root.debug(gl_entries)
		root.debug(self.total)

		if gl_entries:
			make_gl_entries(
				gl_entries,
				cancel=(self.docstatus == 2),
				update_outstanding='Yes',
				merge_entries=False
			)

	def set_missing_values(self):
		from frappe.utils import today, now
		from erpnext.accounts.utils import get_fiscal_year

		for fieldname in ["posting_date"]:
			if not self.get(fieldname):
				self.set(fieldname, today())

		self.fiscal_year = get_fiscal_year(self.posting_date)[0]

		if not self.get("posting_time"):
			self.posting_time = now()
