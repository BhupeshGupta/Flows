# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate
from frappe import msgprint

class IndentInvoiceReceiving(Document):
	def get_invoices(self):
		self.set('entries', [])

		for invoice in frappe.db.sql("""
		SELECT * FROM
		`tabIndent Invoice` WHERE
		vehicle = '{vehicle}' AND
		docstatus = 1 {conditions}
		""".format(vehicle=self.vehicle, conditions=self.get_conditions()), as_dict=True):

			invoice_item = self.append('entries', {})
			invoice_item.indent_invoice = invoice.name
			invoice_item.invoice_date = invoice.transaction_date
			invoice_item.amount = flt(invoice.actual_amount)
			invoice_item.customer = invoice.customer
			invoice_item.item = invoice.item
			invoice_item.qty = invoice.qty

			invoice_item.invoice_receive_date = invoice.invoice_receive_date
			invoice_item.handling = invoice.handling_charges
			invoice_item.cst = invoice.cst
			invoice_item.excise = invoice.excise


	def get_conditions(self):
		conditions = []
		if not cint(self.include_received_invoices) == 1:
			conditions.append("ifnull(invoice_receive_date, '') in ('', '0000-00-00')")

		if self.indent:
			conditions.append('indent = "{}"'.format(self.indent))

		return " {} {}".format("and" if conditions else "", " and ".join(conditions))

	def update_invoices(self):
		vouchers = []
		for d in self.get('entries'):
			if d.invoice_receive_date:
				frappe.db.sql("""
					update `tabIndent Invoice` set
					invoice_receive_date = %s,
					handling_charges = %s,
					excise = %s,
					cst = %s,
					modified = %s
					where name=%s""", (
				d.invoice_receive_date,
				d.handling,
				d.excise,
				d.cst,
				nowdate(),
				d.indent_invoice
				))
				vouchers.append(d.indent_invoice)

		if vouchers:
			msgprint("Data Updated in: {0}".format(", ".join(vouchers)))
		else:
			msgprint("Date not mentioned")
