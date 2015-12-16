from __future__ import unicode_literals

import frappe
from flows.stdlogger import root


@frappe.whitelist()
def get_landed_rate(customer, posting_date, item):
	rs = frappe.db.sql("""
	SELECT landed_rate FROM `tabCustomer Landed Rate`
	WHERE with_effect_from <= "{posting_date}"
	AND customer = "{customer}" AND docstatus =1
	ORDER BY with_effect_from DESC LIMIT 1;
	""".format(posting_date=posting_date, customer=customer))

	landed_rate_per_kg = rs[0][0] if rs and len(rs) > 0 else 0

	rs = frappe.db.sql("""
    SELECT conversion_factor
    FROM `tabItem Conversion`
    WHERE item="{item}";
    """.format(item=item))

	conversion_factor = rs[0][0] if rs and len(rs) > 0 else 0

	return landed_rate_per_kg * conversion_factor


@frappe.whitelist()
def compute_base_rate_for_a_customer(
		customer, plant, item, sales_tax, posting_date, extra_precision=1, adjustment=None,
		details={}, force_check_for_this_month_plant_rate=False
):
	adjustment = adjustment if adjustment else {}
	round_off_digit = 4 if extra_precision == 0 else 5

	context = {
	'customer': customer,
	'plant': plant,
	'item': item,
	'posting_date': posting_date,
	'sales_tax': sales_tax
	}

	rs = frappe.db.sql("""
    SELECT base_rate as base_rate_for_plant, with_effect_from as wef
    FROM `tabPlant Rate`
    WHERE plant="{plant}" AND with_effect_from <= DATE("{posting_date}")
    ORDER BY with_effect_from DESC LIMIT 1;
    """.format(**context), as_dict=True)

	if not (rs and len(rs)) > 0:
		frappe.throw("Unable to find basic rate for plant {plant}".format(**context))

	if force_check_for_this_month_plant_rate:
		expected_date = '-'.join(posting_date.split('-')[:2])
		plant_rate_date = '-'.join(rs[0].wef.split('-')[:2])

		if plant_rate_date != expected_date:
			frappe.throw("Rate for plant {plant} {date} not found".format(date=expected_date, **context))

	purchase_variables = rs[0]

	rs = frappe.db.sql("""
	SELECT cpv.transportation, cpv.discount
	FROM `tabCustomer Plant Variables` cpv
	WHERE cpv.plant="{plant}" AND cpv.with_effect_from <= DATE("{posting_date}") AND cpv.customer="{customer}"
	AND cpv.docstatus != 2 ORDER BY with_effect_from DESC LIMIT 1;
    """.format(**context), as_dict=True)
	if not (rs and len(rs) > 0):
		frappe.throw("Unable to find Customer Purchase Variables")

	purchase_variables.update(rs[0])


	purchase_variables.update(frappe.get_doc("Indent Invoice Tax", sales_tax).as_dict())

	for key, value in adjustment.items():
		purchase_variables[key] += adjustment[key]


	base_rate_for_customer_before_tax = round(
		purchase_variables.base_rate_for_plant + purchase_variables.transportation - purchase_variables.discount,
		round_off_digit
	)

	tax = round(base_rate_for_customer_before_tax * purchase_variables.tax_percentage / 100, round_off_digit)
	surcharge = round(tax * purchase_variables.surcharge_percentage / 100, round_off_digit)
	base_rate_for_customer = round(base_rate_for_customer_before_tax + tax + surcharge, round_off_digit)

	conversion_factor = frappe.db.sql("""
    SELECT conversion_factor
    FROM `tabItem Conversion`
    WHERE item="{item}";
    """.format(**context))[0][0]

	details.update({
	'base_rate_for_customer_before_tax': base_rate_for_customer_before_tax,
	'tax': tax,
	'surcharge': surcharge,
	'base_rate_for_customer': base_rate_for_customer,
	'conversion_factor': conversion_factor
	})

	return round(base_rate_for_customer * conversion_factor, round_off_digit)


@frappe.whitelist()
def get_customer_payment_info(customer, plant, posting_date):
	context = {
	'customer': customer,
	'plant': plant,
	'posting_date': posting_date,
	}

	discount_transportation_query = """
    SELECT sales_tax, cenvat, payment_mode
    FROM `tabCustomer Plant Variables`
    WHERE plant="{plant}" AND with_effect_from <= DATE("{posting_date}") AND customer="{customer}"
	AND docstatus != 2
    ORDER BY with_effect_from DESC LIMIT 1;
    """.format(**context)

	rs = frappe.db.sql(discount_transportation_query)
	if len(rs) > 0:
		sales_tax, cenvat, payment_mode = rs[0]

		return {
		"sales_tax": sales_tax,
		"cenvat": cenvat,
		"payment_mode": payment_mode
		}

	frappe.throw("""Customer Plant Master Not Found For Customer {}, Plant {} and Date {}.
	Please enter details in customer plant master and reload this customer in indent before proceeding
	further""".format(
		customer, plant, posting_date))