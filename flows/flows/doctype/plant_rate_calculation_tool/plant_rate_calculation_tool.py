# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class PlantRateCalculationTool(Document):
	def compute_rate(self):
		context = {
		'date': self.invoice_date,
		'customer': self.customer,
		'plant': self.plant,
		'item': self.item,
		'qty': self.quantity
		}

		discount_transportation_query = """
		SELECT transportation, discount, tax_percentage, surcharge_percentage
		FROM `tabCustomer Plant Variables`
		WHERE plant="{plant}" AND with_effect_from <= DATE("{date}") AND customer="{customer}"
		ORDER BY with_effect_from DESC LIMIT 1;
		""".format(**context)

		rs = frappe.db.sql(discount_transportation_query, as_dict=True)
		if not (rs and len(rs) > 0):
			frappe.throw("Unable to find Customer Purchase Variables")

		purchase_variables = rs[0]

		conversion_factor_query = """
		SELECT conversion_factor
		FROM `tabItem Conversion`
		WHERE item="{item}";
		""".format(**context)

		rs = frappe.db.sql(conversion_factor_query)
		if rs and len(rs) > 0:
			conversion_factor = rs[0][0]

		bill_rate_per_kg = self.amount / conversion_factor / self.quantity

		tax_per_rs = purchase_variables.tax_percentage / 100
		surcharge_per_rs = tax_per_rs * purchase_variables.surcharge_percentage
		tax_removal_ratio = 100 / (100 * (1 + tax_per_rs + surcharge_per_rs))

		bill_rate_without_tax = bill_rate_per_kg * tax_removal_ratio

		self.plant_rate = bill_rate_without_tax + purchase_variables.discount - purchase_variables.transportation