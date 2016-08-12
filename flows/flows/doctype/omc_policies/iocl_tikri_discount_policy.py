import frappe

def eval(doc, omc, cpv):
	margin_to_be_claimed = .9 * get_tikri_margin(doc.transaction_date)

	# doc.discount is -ve in case discount is not received
	discount_in_invoice = cpv.discount + doc.discount

	return {
		'discount_in_invoice': discount_in_invoice,
		'discount_mismatch': -1 * doc.discount if doc.discount else 0,
		'incentive': cpv.incentive,
		'additional_discount': margin_to_be_claimed - discount_in_invoice - cpv.incentive,
		'investment_discount': omc.incentive_on_investment
	}


margin_cache = {

}

def get_tikri_margin(date):
	month_year = '-'.join(date.split('-')[:2])

	if month_year not in margin_cache:

		rs = frappe.db.sql(
			"""
			select margin from `tabPlant Rate`
			where plant = "IOCL TIKRI"
			and with_effect_from like '{}-%'
			""".format(month_year)
		)

		if not rs:
			frappe.throw("Plant Rate from IOCL TIKRI not set")

		if not rs[0][0]:
			frappe.throw("IOCL TIKRI margin not set")

		margin_cache[month_year] = rs[0][0]

	return margin_cache[month_year]