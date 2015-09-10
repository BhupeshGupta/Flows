# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint


class CustomerSale(Document):
	def autoname(self):
		self.name = '{}#{}'.format(self.customer, self.with_effect_from)

	def validate(self):
		if cint(self.display_rate) < 2:
			frappe.throw("Display Rate Can Not Be Less Than {}".format(2))