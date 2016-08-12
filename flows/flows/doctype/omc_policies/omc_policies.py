# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import importlib

class OMCPolicies(Document):

	def init(self):
		name = self.name.replace(' ', '_').lower()
		self.module = importlib.import_module('flows.flows.doctype.omc_policies.{}'.format(name))


	def execute(self, invoice_number):
		doc = frappe.get_doc("Indent Invoice", invoice_number)
		omc = frappe.get_doc("OMC Customer Registration", doc.omc_customer_registration)
		cpv = frappe.get_doc("Customer Plant Variables", doc.customer_plant_variables)

		res = self.module.eval(doc, omc, cpv)

		return res