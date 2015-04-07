from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.accounts.party import get_party_account
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts import utils as account_utils

class CrossSale(Document):
	def cancel(self):
		super(CrossSale, self).cancel()
		self.update_gl()

	def on_submit(self):
		self.update_gl()

	def update_gl(self):

		# Pull out config
		indent_invoice_settings = frappe.db.get_values_from_single(
			'*', None, 'Cross Sale Purchase Settings', as_dict=True
		)[0]

		# a/c as suggested by cross sale purchase settings, used to balance VK sale/purchase
		company = indent_invoice_settings.buyer_company

		gl_entries = []
		remark = "Cross Sale to {}".format(self.customer)

		gl_entries.append(
			self.get_gl_dict({
			"company": company,
			"account": get_party_account(company, self.customer, "Customer"),
			"debit": self.amount,
			"remarks": remark
			})
		)

		gl_entries.append(
			self.get_gl_dict({
			"company": company,
			"account": indent_invoice_settings.buyer_sale_head,
			"cost_center": indent_invoice_settings.buyer_sales_cost_center,
			"credit": self.amount,
			"remarks": remark
			})
		)

		make_gl_entries(gl_entries, cancel=(self.docstatus == 2),
		                update_outstanding='Yes', merge_entries=False)


	def get_gl_dict(self, args):
		"""this method populates the common properties of a gl entry record"""
		gl_dict = frappe._dict({
		'posting_date': self.posting_date,
		'voucher_type': self.doctype,
		'voucher_no': self.name,
		'aging_date': self.get("aging_date") or self.posting_date,
		'remarks': self.get("remarks"),
		'fiscal_year': account_utils.get_fiscal_year(self.posting_date)[0],
		'debit': 0,
		'credit': 0,
		'is_opening': "No"
		})
		gl_dict.update(args)
		return gl_dict

