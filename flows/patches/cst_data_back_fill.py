import frappe
from flows.flows.pricing_controller import compute_base_rate_for_a_customer_from_cpv_and_plant_rate
import json

def auto_back_cst_fill():
	final_log_set = []
	exp_list = []
	for i in frappe.db.sql("""
	select * from `tabIndent Invoice`
	where ifnull(sales_tax, '') = ''
	and docstatus = 1
	and transaction_date > '2015-04-01'
	and item not like '%BK'
	and item like 'FC%'
	and customer not like 'VK %'
	and supplier not like 'Aggarwal%'
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
			SELECT name, with_effect_from AS wef
			FROM `tabPlant Rate`
			WHERE plant="{plant}" AND with_effect_from <= DATE("{posting_date}")
			ORDER BY with_effect_from DESC LIMIT 1;
			""".format(**context), as_dict=True)

			if not rs:
				exp_list.append([i.transaction_date, i.name, i.customer, 'Plant Rate Not Found'])
				continue

			plant_rate_name = rs[0].name

			rs = None

			while not rs:
				# Guess CPV Name
				rs = frappe.db.sql("""
				SELECT *
				FROM `tabCustomer Plant Variables` cpv
				WHERE cpv.plant="{plant}" AND cpv.with_effect_from <= DATE("{posting_date}") AND cpv.customer="{customer}"
				AND cpv.docstatus != 2 ORDER BY with_effect_from DESC LIMIT 1;
				""".format(**context), as_dict=True)

				if not rs:
					copy = frappe.db.sql("""
					SELECT *
					FROM `tabCustomer Plant Variables` cpv
					WHERE cpv.plant="{plant}" AND cpv.with_effect_from >= DATE("{posting_date}") AND cpv.customer="{customer}"
					AND cpv.docstatus != 2 ORDER BY with_effect_from ASC LIMIT 1;
					""".format(**context), as_dict=True)

					if not copy:
						cpv = create_cpv(i)
						if not cpv:
							raise Exception('CPV New Draft Unexpected')
						exp_list.append([i.transaction_date, i.name, i.customer, i.supplier, 'New CPV Drafted'])
						continue

					draft_cpv(copy[0])
					final_log_set.append([i.transaction_date, i.name, i.customer, i.supplier, 'CPV copied'])
			if not rs:
				continue

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

			# final_log_set.append(', '.join(['Skipping', i.transaction_date, i.name, i.customer, rate_diff]))
			if abs(rate_diff) >= .10:
				final_log_set.append([
					i.name, i.transaction_date, rate_diff, i.customer, i.supplier, i.qty, i.item
				])
			else:
				frappe.db.sql(
					"""
					update `tabIndent Invoice`
					set customer_plant_variables = "{cpv}",
					sales_tax = "{sales_tax}"
					where name = "{name}"
					""".format(name=i.name, cpv=cpv, sales_tax=sales_tax)
				)

		except Exception as e:
			exp_list.append([i.name, str(e)])
			print e

	final_log_set=json.dumps(final_log_set)
	exp_list = json.dumps(exp_list)
	print(final_log_set)
	print exp_list
	f = open('/tmp/run.log', 'w')
	f.write(final_log_set)
	f.write(exp_list)
	f.close()


cpv_attrib_to_copy = ["customer", "plant", "transportation", "discount", "payment_mode", "cenvat", "contract_number", "incentive", "discount_via_credit_note", "sales_tax", "enabled"]
def draft_cpv(cpv_to_copy_from):
	new_voucher = {'doctype': 'Customer Plant Variables', 'with_effect_from': '2015-04-01'}
	for key, value in cpv_to_copy_from.items():
		if key in cpv_attrib_to_copy:
			new_voucher[key] = value

	frappe.get_doc(new_voucher).save()

def create_cpv(invoice):
	def guess_sales_tax(plant):
		if 'lalru' in plant.lower():
			return 'Punjab Vat'
		if 'hissar' in plant.lower():
			return 'CST'
		return 'CST'

	rs = frappe.db.sql("""SELECT *
	FROM `tabCustomer Plant Variables` cpv
	WHERE cpv.customer="{customer}"
	AND cpv.docstatus != 2 ORDER BY with_effect_from ASC LIMIT 1;""".format(**invoice), as_dict=True)


	if rs:
		rs = rs[0]

	cpv = frappe.get_doc({
	'doctype': 'Customer Plant Variables',
	'with_effect_from': '2015-04-01',
	'customer': invoice.customer,
	'plant': invoice.supplier,
	'transportation': 0,
	'discount': 0,
	'cenvat': '1',
	'incentive': '0',
	'discount_via_credit_note': '0',
	'contract_number': '',

	'payment_mode': rs.payment_mode if rs else 'Indirect',
	'sales_tax': rs.sales_tax if rs else guess_sales_tax(invoice.supplier),

	'enabled': 1
	})

	cpv.save()

	return cpv
