# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe.model.document import Document
from erpnext.accounts.party import get_party_account
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts import utils as account_utils


class CrossPurchase(Document):
	def get_pending_invoices(self):
		self.set('invoice_items', [])
		for invoice in get_pending_invoices(
				None, None, None, None, None,
				{
				'customer': [x.customer for x in self.customer_list],
				'to_date': self.to_date
				}, as_dict=True
		):
			invoice_item = self.append('invoice_items', {})
			invoice_item.invoice = invoice.name
			invoice_item.consignment_note = invoice.transportation_invoice
			invoice_item.item = invoice.item
			invoice_item.qty = invoice.qty
			invoice_item.invoice_date = invoice.transaction_date

			invoice_item.invoice_amount = flt(invoice.actual_amount)
			invoice_item.consignment_note_amount = flt(invoice.transportation_invoice_amount)
			invoice_item.total = flt(invoice_item.invoice_amount) + flt(invoice_item.consignment_note_amount)

		self.compute_totals()

	def compute_totals(self):
		self.total_invoice_amount = sum([flt(x.invoice_amount) for x in self.invoice_items])
		self.total_consignment_note_amount = sum([flt(x.consignment_note_amount) for x in self.invoice_items])
		self.grand_total = self.total_invoice_amount + self.total_consignment_note_amount


	def cancel(self):
		super(CrossPurchase, self).cancel()
		self.update_gl()

	def on_submit(self):
		self.update_gl()

	def update_gl(self):

		# Pull out config
		indent_invoice_settings = frappe.db.get_values_from_single(
			'*', None, 'Cross Sale Purchase Settings', as_dict=True
		)[0]

		# a/c as suggested by cross sale purchase settings, used to balance VK sale/purchase
		seller_company = indent_invoice_settings.seller_company
		buyer_company = indent_invoice_settings.buyer_company

		gl_entries = []
		remark = "Cross Purchase from {}".format(self.customer)

		gl_entries.append(
			self.get_gl_dict({
			"company": buyer_company,
			"account": indent_invoice_settings.buyer_purchase_head,
			"cost_center": indent_invoice_settings.buyer_purchase_cost_center,
			"debit": self.grand_total,
			"remarks": remark
			})
		)

		gl_entries.append(
			self.get_gl_dict({
			"company": buyer_company,
			"account": indent_invoice_settings.suppliers_payment_account,
			"credit": self.grand_total,
			"remarks": remark
			})
		)

		# From VK to Party in Seller Company Books
		gl_entries.append(
			self.get_gl_dict({
			"company": seller_company,
			"account": get_party_account(seller_company, indent_invoice_settings.customer_account, "Customer"),
			"cost_center": indent_invoice_settings.buyer_purchase_cost_center,
			"debit": self.grand_total,
			"remarks": remark
			})
		)

		gl_entries.append(
			self.get_gl_dict({
			"company": seller_company,
			"account": get_party_account(seller_company, self.customer, "Customer"),
			"credit": self.grand_total,
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


def get_pending_invoices(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	rs = frappe.db.sql("""
		SELECT name, transaction_date, item, qty, actual_amount, transportation_invoice, transportation_invoice_amount
		FROM `tabIndent Invoice`
		WHERE cross_sold = 1 AND
		customer IN ({customer}) AND
		transaction_date <= "{date}" AND
		name NOT IN (SELECT invoice FROM `tabCross Purchase Item` WHERE docstatus = 1)
		ORDER BY transaction_date ASC;
		""".format(
		customer='"{}"'.format('","'.join(filters['customer'])),
		date=filters['to_date']), as_dict=as_dict
	)
	return rs