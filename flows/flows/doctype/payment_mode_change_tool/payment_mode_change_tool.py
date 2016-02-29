# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PaymentModeChangeTool(Document):
	def apply_change(self):
		invoice = frappe.get_doc('Indent Invoice', self.invoice)

		frappe.db.sql("""
		UPDATE `tabIndent Item` SET payment_type = "{payment_type}" WHERE name = "{name}"
		""".format(payment_type=self.payment_type, name=invoice.indent_item))

		invoice.cancel()
		invoice.amended_from = invoice.name
		invoice.name = None
		invoice.docstatus = 0

		invoice.save()
		invoice.submit()

		frappe.msgprint("Changed Payment Mode To {}".format(self.payment_type))