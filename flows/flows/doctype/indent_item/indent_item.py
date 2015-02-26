# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class IndentItem(Document):
	def autoname(self):
		self.name = make_autoname(self.parent + '.##')