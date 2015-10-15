# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


validation_map = {
	'AARTI STEEL': 'AARTI STEEL',
	'Christian Medical': 'Christian Medical'
}

class IndentInvoiceCustomerChangeTool(Document):
	def validate_change(self, invoice, src_customer, target_customer):
		if invoice.docstatus != 1:
			frappe.throw("Invoice needs to be submitted before applying change")

		for src, target in validation_map.items():
			if src in src_customer and target in target_customer:
				return

		frappe.throw("Change prohibited by rules. Please contact admin")

	def apply_change(self):
		invoice = frappe.get_doc('Indent Invoice', self.invoice)

		src_customer = invoice.customer
		target_customer = self.customer

		self.validate_change(invoice, src_customer, target_customer)

		frappe.db.sql("""
		UPDATE `tabIndent Item` SET customer = '{customer}' WHERE name = '{name}'
		""".format(name=invoice.indent_item, customer=self.customer))

		invoice.cancel()
		invoice.amended_from = invoice.name
		invoice.name = None
		invoice.docstatus = 0
		invoice.save()
		invoice.submit()

		frappe.msgprint("Changed customer from {} to {}".format(src_customer, target_customer))