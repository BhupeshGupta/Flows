# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from flows import utils
from frappe.model.document import Document

from flows.stdlogger import root

from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.stock.stock_ledger import make_sl_entries


class PaymentReceipt(Document):
	def __init__(self, *args, **kwargs):
		super(PaymentReceipt, self).__init__(*args, **kwargs)
		self.set_missing_values()

	def autoname(self):
		if self.id and self.id != '':
			self.name = self.id

	def on_submit(self):
		self.make_gl_entry()
		if self.stock_date != '':
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

		owners_account = utils.get_imprest_or_get_or_create_customer_like_account(self.company, self.owner)
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
