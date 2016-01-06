import frappe
from flows.flows.pricing_controller import compute_base_rate_for_a_customer_from_cpv_and_plant_rate
import json

def auto_back_cst_fill():
	final_log_set = []
	for i in frappe.db.sql("""
	select * from `tabIndent Invoice`
	where ifnull(sales_tax, '') = ''
	and docstatus = 1
	and transaction_date > '2015-04-01'
	and item not like '%BK'
	and item like 'FC%'
	order by transaction_date ASC
	""", as_dict=True):
		context = {
			'customer': i.customer,
			'plant': i.supplier,
			'item': i.item,
			'posting_date': i.transaction_date,
			# 'sales_tax': sales_tax
		}

		try:

			rs = frappe.db.sql("""
			SELECT name, with_effect_from as wef
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
			sales_tax = rs[0].sales_tax

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

			rate_diff = abs(round((expected - i.actual_amount)/qty, 2))

			if rate_diff >= .10:
				final_log_set.append('Skiping invoice no {} {} mismatch of {}'.format(i.name, i.transaction_date, rate_diff))
			else:
				final_log_set.append('Combination Found {} {}'.format(i.name, i.transaction_date))
				frappe.db.sql("""
				update `tabIndent Invoice`
				set customer_plant_variables = '{cpv}',
				sales_tax = '{sales_tax}'
				where name = '{name}'
				""".format(name=i.name, cpv=cpv, sales_tax=sales_tax))
		except Exception as e:
			print e

	f = open('/tmp/run.log', 'w')
	f.write(json.dumps(final_log_set, indent=4))
	f.close()