# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from flows.flows.pricing_controller import compute_base_rate_for_a_customer

def execute(filters=None):
	columns = [
		"Customer:Link/Customer:150",
		"Supplier:Link/Supplier:150",
		"Basic:Currency:",
		"Discount:Currency:",
		"Handling:Currency:",
		"Tax:Currency:",
		"Transport:Currency:",
		"Landed:Currency:",
		"CPV:Link/Customer Plant Variables:"
	]
	data = get_data(filters)
	return columns, data


def get_data(filters):
	customer_plant_list = get_customer_supplier_list(filters)

	rs = []

	for customer_plant in customer_plant_list:
		detail = {}
		res = compute_base_rate_for_a_customer(
			customer_plant['customer'],
			customer_plant['plant'],
			'FC19',
			filters.date,
			details=detail,
			force_check_for_this_month_plant_rate=True,
			raise_error=0
		)

		if not res: continue

		rs.append(map_row(detail, customer_plant))

	return rs

def map_row(row, customer_plant):
	"""
		{
			"plant_rate": 42.0,
			"invoice_discount": 6.0,
			"invoice_handling": 0.0,
			"tax": 0.72,
			"surcharge": 0.0,
			"base_rate_for_customer_before_tax": 36.0,
			"base_rate_for_customer": 36.72,
			"conversion_factor": 19.0,
		}
	:param row:
	:param customer_plant:
	:return:
	"""

	tspt = row['applicable_transportation']
	return [
		customer_plant['customer'],
		customer_plant['plant'],
		row['plant_rate'],
		row['invoice_discount'],
		row['invoice_handling'],
		row['tax'] + row['surcharge'],
		tspt,
		row['base_rate_for_customer'] + (tspt if tspt else 0),
		customer_plant['cpv']
	]

def get_customer_supplier_list(filters):
	results = []

	customers = [c[0] for c in frappe.db.sql("""select name from `tabCustomer` where enabled = 1 and purchase_enabled = 1""")]

	for customer in customers:
		omcs = [omc[0] for omc in frappe.db.sql(
			"""
			select DISTINCT omc from `tabOMC Customer Registration`
			where customer = "{}" and docstatus = 1 and with_effect_from <= "{}"
			""".format(customer, filters.date)
		)]

		valid_omcs = []
		for omc in omcs:
			x = frappe.db.sql(
				"""
				select * from `tabOMC Customer Registration`
				where customer = "{}"
				and omc = "{}"
				and with_effect_from <= "{}"
				and docstatus = 1
				order by with_effect_from desc
				limit 1
				""".format(customer, omc, filters.date), as_dict=True
			)[0]

			if x.enabled:
				valid_omcs.append(x)

		for omc in valid_omcs:
			plants = [cpv[0] for cpv in frappe.db.sql(
				"""
				select DISTINCT plant
				from `tabCustomer Plant Variables`
				where customer = "{}"
				and plant like "{}%"
				and docstatus = 1
				and with_effect_from <= "{}"
				""".format(customer, omc.omc, filters.date)
			)]

			for plant in plants:
				x = frappe.db.sql(
				"""
					select * FROM `tabCustomer Plant Variables`
					where customer = "{}"
					and plant = "{}"
					and with_effect_from <= "{}"
					and docstatus = 1
					order by with_effect_from desc
					limit 1
					""".format(customer, plant, filters.date), as_dict=True
				)[0]

				if x.enabled:
					results.append({'customer': x.customer, 'plant': x.plant, 'cpv': x.name})

	return results