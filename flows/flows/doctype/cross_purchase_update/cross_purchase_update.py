# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe

class CrossPurchaseUpdate(Document):
	def update_payment_details(self):
		cp = frappe.get_doc("Cross Purchase", self.cross_purchase)

		if not cp.payment_in_jv or cp.payment_in_jv == "":
			cp.payment_in_jv = self.payment_in_jv
		if not cp.payment_withdrawn_jv or cp.payment_withdrawn_jv == "":
			cp.payment_withdrawn_jv = self.payment_withdrawn_jv
		if not cp.payment_out_jv or cp.payment_out_jv == "":
			cp.payment_out_jv = self.payment_out_jv

		if hasattr(cp, "validate_closure"):
			cp.validate_closure()

		self.payment_in_jv = cp.payment_in_jv
		self.payment_withdrawn_jv= cp.payment_withdrawn_jv
		self.payment_out_jv = cp.payment_out_jv

		update = []
		if self.payment_in_jv:
			update.append(" payment_in_jv = '{}' ".format(self.payment_in_jv))
		if self.payment_withdrawn_jv:
			update.append(" payment_withdrawn_jv = '{}' ".format(self.payment_withdrawn_jv))
		if self.payment_out_jv:
			update.append(" payment_out_jv = '{}' ".format(self.payment_out_jv))

		if update:
			frappe.db.sql("""
				UPDATE `tabCross Purchase` SET {}
				WHERE name = "{}";
			""".format(", ".join(update), cp.name)
			)