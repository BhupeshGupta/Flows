from __future__ import unicode_literals

import frappe
from flows.stdlogger import root


@frappe.whitelist()
def compute_base_rate_for_a_customer(customer, plant, item, sales_tax_type, indent_date, extra_precision=1):
    context = {
        'customer': customer,
        'plant': plant,
        'item': item,
        'indent_date': indent_date,
        'sales_tax_type': sales_tax_type
    }

    base_rate_query = """
    select base_rate
    from `tabPlant Rate`
    where plant='{plant}' and with_effect_from <= DATE('{indent_date}')
    order by with_effect_from desc limit 1;
    """.format(**context)

    rs = frappe.db.sql(base_rate_query)
    base_rate_for_plant = rs[0][0]

    transportation = discount = 0

    discount_transportation_query = """
    select transportation, discount, tax_percentage, surcharge_percentage
    from `tabCustomer Plant Variables`
    where plant='{plant}' and with_effect_from <= DATE('{indent_date}') and customer='{customer}'
    order by with_effect_from desc limit 1;
    """.format(**context)

    rs = frappe.db.sql(discount_transportation_query)
    if len(rs) > 0:
        transportation, discount, tax_percentage, surcharge_percentage = rs[0]

    round_off_digit = 4 if extra_precision == 0 else 5

    base_rate_for_customer_before_tax = round(base_rate_for_plant + transportation - discount, round_off_digit)
    tax = round(base_rate_for_customer_before_tax * tax_percentage / 100, round_off_digit)
    surcharge = round(tax * surcharge_percentage / 100, round_off_digit)
    base_rate_for_customer = round(base_rate_for_customer_before_tax + tax + surcharge, round_off_digit)

    conversion_factor_query = """
    select conversion_factor
    from `tabItem Conversion`
    where item='{item}';
    """.format(**context)

    conversion_factor = frappe.db.sql(conversion_factor_query)[0][0]

    root.debug({
        "base_rate_for_plant": base_rate_for_plant,
        "transportation": transportation,
        "discount": discount,
        "tax_percentage": tax_percentage,
        "surcharge_percentage": surcharge_percentage,
        "tax": tax,
        "surcharge": surcharge,
        "base_rate_for_customer": base_rate_for_customer,
        "conversion_factor": conversion_factor
    })

    return round(base_rate_for_customer * conversion_factor, round_off_digit)


@frappe.whitelist()
def get_customer_payment_info(customer, plant, indent_date):
    context = {
        'customer': customer,
        'plant': plant,
        'indent_date': indent_date,
    }

    discount_transportation_query = """
    select sales_tax_type, cenvat, tax_percentage, surcharge_percentage, payment_mode
    from `tabCustomer Plant Variables`
    where plant='{plant}' and with_effect_from <= DATE('{indent_date}') and customer='{customer}'
    order by with_effect_from desc limit 1;
    """.format(**context)

    rs = frappe.db.sql(discount_transportation_query)
    if len(rs) > 0:
        sales_tax_type, cenvat, tax_percentage, surcharge_percentage, payment_mode = rs[0]

    return {
        "sales_tax_type": sales_tax_type,
        "cenvat": cenvat,
        "tax_percentage": tax_percentage,
        "surcharge_percentage": surcharge_percentage,
        "payment_mode": payment_mode
    }