# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe


class CustomerPlantVariables(Document):
	def autoname(self):
		self.name = '{}#{}#{}'.format(
			str(self.customer).strip(),
			str(self.plant).strip(),
			self.with_effect_from
		)

	def before_submit(self):
		if hasattr(self, 'ignore_invoice_check'):
			return

		rs = frappe.db.sql(
			"""
			select name, transaction_date from `tabIndent Invoice`
			where transaction_date >= "{}"
			and customer = "{}"
			and supplier = "{}"
			and docstatus = 1
			order by transaction_date asc
			""".format(self.with_effect_from, self.customer, self.plant)
		)

		if not rs:
			return

		frappe.throw(
			"Following invoices are submitted with previous CPV. Cancel these before submitting new variable. \n\n{}"
				.format('\n'.join(['{1} <a href="/desk#Form/Indent Invoice/{0}">{0}</a>'.format(x[0], x[1]) for x in rs]))
		)
