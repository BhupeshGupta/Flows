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

	context = {
	'customer': customer,
	'plant': plant,
	'item': item,
	'posting_date': posting_date,
	'sales_tax': sales_tax
	}

	# Guess Plant Rate Name
	rs = frappe.db.sql("""
    SELECT name, with_effect_from as wef
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

	plant_rate_name = rs[0].name

	# Guess CPV Name
	rs = frappe.db.sql("""
	SELECT name
	FROM `tabCustomer Plant Variables` cpv
	WHERE cpv.plant="{plant}" AND cpv.with_effect_from <= DATE("{posting_date}") AND cpv.customer="{customer}"
	AND cpv.docstatus != 2 ORDER BY with_effect_from DESC LIMIT 1;
    """.format(**context), as_dict=True)

	if not (rs and len(rs) > 0):
		frappe.throw("Unable to find Customer Purchase Variables")

	cpv_name = rs[0].name


	return compute_base_rate_for_a_customer_from_cpv_and_plant_rate(
		plant_rate_name, cpv_name, sales_tax, item,
		extra_precision=extra_precision, adjustment=adjustment, details=details
	)



def compute_base_rate_for_a_customer_from_cpv_and_plant_rate(
		plant_rate, cpv, sales_tax, item, extra_precision=1, adjustment=None, details={}
):
	adjustment = adjustment if adjustment else {}
	round_off_digit = 4 if extra_precision == 0 else 5

	rs = frappe.db.sql("""
    SELECT base_rate as base_rate_for_plant
    FROM `tabPlant Rate`
    WHERE name = "{}"
    """.format(plant_rate), as_dict=True)
	purchase_variables = rs[0]

	rs = frappe.db.sql("""
	SELECT cpv.transportation, cpv.discount
	FROM `tabCustomer Plant Variables` cpv
	WHERE name = "{}";
    """.format(cpv), as_dict=True)
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
    WHERE item="{}";
    """.format(item))[0][0]

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

	registration = frappe.db.sql("""
	select name, default_credit_account, docstatus
	from `tabOMC Customer Registration`
	where customer= "{customer}"
	and omc= "{omc}"
	and docstatus != 2
	and with_effect_from <= DATE("{posting_date}")
	ORDER BY with_effect_from DESC LIMIT 1;
	""".format(omc=plant.split(' ')[0].capitalize(), **context), as_dict=True)[0]

	if registration.docstatus != 1:
		frappe.throw("Customer `{}` registration is not approved."
					 "Please get it approved from competent authority"
					 .format(customer))

	possible_account_types = [x[0] for x in frappe.db.sql("""
	select DISTINCT type from `tabOMC Customer Registration Credit Account`
	where parent="{}"
	""".format(registration.name))]

	discount_transportation_query = """
	SELECT name, sales_tax
	FROM `tabCustomer Plant Variables`
	WHERE plant="{plant}"
	AND with_effect_from <= DATE("{posting_date}")
	AND customer="{customer}"
	AND docstatus != 2
	ORDER BY with_effect_from DESC LIMIT 1;
	""".format(**context)

	cpv = frappe.db.sql(discount_transportation_query, as_dict=True)

	if not cpv:
		frappe.throw(
		"""Customer Plant Master Not Found For Customer {}, Plant {} and Date {}.
		Please enter details in customer plant master and reload this customer in indent before proceeding
		further""".format(customer, plant, posting_date))
	cpv = cpv[0]


	return {
	"sales_tax": cpv.sales_tax,
	"credit_account": registration.default_credit_account,
	"possible_credit_accounts": possible_account_types,
	"registration": registration.name,
	"cpv": cpv.name
	}


@frappe.whitelist()
def get_account_info(customer, credit_account, plant, date):
	rs = frappe.db.sql("""
	select ca.*
	from `tabOMC Customer Registration` reg left join `tabOMC Customer Registration Credit Account` ca
	on reg.name = ca.parent
	where reg.customer= "{customer}"
	and reg.omc = "{omc}"
	AND reg.with_effect_from <= DATE("{posting_date}")
	and reg.docstatus = 1
	and ca.type = "{credit_account}"
	ORDER BY reg.with_effect_from DESC LIMIT 1;
	"""
	.format(
		customer=customer,
		omc=plant.split(' ')[0].capitalize(),
		posting_date=date,
		credit_account=credit_account
	), as_dict=True)

	if not rs:
		frappe.throw("No account configured for customer `{}` account type `{}`".
					 format(customer, credit_account))

	rs = rs[0]

	return rs
