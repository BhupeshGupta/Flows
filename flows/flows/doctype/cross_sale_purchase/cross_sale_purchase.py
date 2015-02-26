# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

from erpnext.accounts.party import get_party_account
from erpnext.accounts.general_ledger import make_gl_entries


class CrossSalePurchase(Document):
	def cancel(self):
		self.update_gl()


	def on_submit(self):
		self.update_gl()

	def update_gl(self):
		buyer_account = get_party_account(self.company, self.to_customer, "Customer")
		seller_account = get_party_account(self.company, self.from_customer, "Customer")

		gl_entries = []
		remark = "Sale of {} {} from {} to {}".format(self.qty, self.item, self.from_customer, self.to_customer)

		gl_entries.append(
			self.get_gl_dict({
			"account": buyer_account,
			"debit": self.sale_amount,
			"remarks": remark
			})
		)

		gl_entries.append(
			self.get_gl_dict({
			"account": seller_account,
			"credit": self.purchase_amount,
			"remarks": remark
			})
		)

		income = self.sale_amount - self.purchase_amount

		if income != 0:

			adjustment_gl_entry = self.get_gl_dict({
			"account": "Sales - AL",
			"remarks": remark,
			"cost_center": "Main - AL"
			})

			adjustment_gl_entry['credit' if income else 'debit'] = income

			gl_entries.append(adjustment_gl_entry)

		make_gl_entries(gl_entries, cancel=(self.docstatus == 2),
		                update_outstanding='Yes', merge_entries=False)


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