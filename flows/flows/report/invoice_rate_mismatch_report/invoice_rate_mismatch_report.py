# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

import frappe
from flows.flows.pricing_controller import compute_base_rate_for_a_customer_from_cpv_and_plant_rate


def execute(filters=None):
	columns = [
		'Doc No:Link/Indent Invoice:100',
		'Date:Date:100',
		'Diff:Currency:100',
		"Customer::250",
		"Supplier::250",
		"Item::",
		"Qty::",
		'CPV:Link/Customer Plant Variables:100',
	]
	return columns, get_data(filters)


def get_data(filters):
	final_log_set = []
	for i in frappe.db.sql("""
	select * from `tabIndent Invoice`
	where docstatus = 1
	and transaction_date > '2015-04-01'
	and item not like '%BK'
	and item like 'FC%'
	and transaction_date between "{from_date}" and "{to_date}"
	order by transaction_date ASC
	""".format(**filters), as_dict=True):
		context = {
		'customer': i.customer,
		'plant': i.supplier,
		'item': i.item,
		'posting_date': i.transaction_date,  # 'sales_tax': sales_tax
		}

		try:

			rs = frappe.db.sql("""
			SELECT name, with_effect_from AS wef
			FROM `tabPlant Rate`
			WHERE plant="{plant}" AND with_effect_from <= DATE("{posting_date}")
			ORDER BY with_effect_from DESC LIMIT 1;
			""".format(**context), as_dict=True)

			plant_rate_name = rs[0].name

			# Guess CPV Name
			rs = frappe.db.sql("""
			SELECT name, sales_tax
			FROM `tabCustomer Plant Variables` cpv
			WHERE cpv.plant="{plant}" AND cpv.with_effect_from <= DATE("{posting_date}") AND cpv.customer="{customer}"
			AND cpv.docstatus != 2 ORDER BY with_effect_from DESC LIMIT 1;
			""".format(**context), as_dict=True)

			cpv = rs[0].name
			sales_tax = i.sales_tax if i.sales_tax else rs[0].sales_tax

			adjustment = {
			'discount': i.discount if i.discount else 0,
			'transportation': i.handling if i.handling else 0
			} if i.adjusted else {}

			details = {}

			expected = compute_base_rate_for_a_customer_from_cpv_and_plant_rate(
				plant_rate_name, cpv, sales_tax, i.item, adjustment=adjustment, details=details
			) * i.qty

			qty = float(i.item.replace('FC', '').replace('L', '')) * i.qty

			print("Expected: {}, Actual: {}, qty: {}".format(expected, i.actual_amount, qty))

			rate_diff = round((expected - i.actual_amount) / qty, 2)

			if abs(rate_diff) >= .10:
				final_log_set.append([
					i.name, i.transaction_date, rate_diff, i.customer, i.supplier, i.qty, i.item, cpv
				])

		except Exception as e:
			print e

	return final_log_set