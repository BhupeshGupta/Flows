# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CPVReplacementTool(Document):
	def get_invoices(self):

		cpv = frappe.get_doc("Customer Plant Variables", self.cpv)

		self.invoices = []

		for i in frappe.db.sql(
			"""
			select * from `tabIndent Invoice`
			where transaction_date >= "{with_effect_from}"
			and customer = "{customer}"
			and supplier = "{plant}"
			and  docstatus != 2
			and customer_plant_variables != "{name}";
			""".format(**cpv.as_dict()), as_dict=True
		):

			self.append('invoices', {
				'transaction_date': i.transaction_date,
				'indent_invoice': i.name,
				'transportation_invoice': i.transportation_invoice,
				'applicable_transportation_invoice_rate': i.applicable_transportation_invoice_rate,
				'adjusted': i.adjusted,
				'handling': i.handling,
				'discount': i.discount,
			})

	def replace(self):
		cpv = frappe.get_doc("Customer Plant Variables", self.cpv)
		cpv.ignore_invoice_check = True
		cpv.submit()

		for i in self.invoices:
			frappe.msgprint(i.indent_invoice)
			doc = frappe.get_doc("Indent Invoice", i.indent_invoice)

			# if doc.docstatus == 1:
			# 	doc.cancel()
			#
			# if doc.docstatus == 2:
			# 	doc.amended_from = doc.name
			# 	doc.name = ""
			# 	doc.docstatus = 0

			# doc.docstatus == 0
			doc.customer_plant_variables = self.cpv
			doc.adjusted = i.adjusted
			doc.handling = i.handling
			doc.discount = i.discount

			doc.ignore_validate_update_after_submit = True

			doc.validate_purchase_rate()

			doc.save()
			# doc.submit()

		self.get_invoices()
