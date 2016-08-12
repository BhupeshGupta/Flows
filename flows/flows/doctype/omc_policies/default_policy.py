def eval(doc, omc, cpv):

	total_discount = cpv.discount + cpv.discount_via_credit_note

	# doc.discount is -ve in case discount is not received
	discount_in_invoice = cpv.discount + doc.discount

	return {
		'total_discount_passed': total_discount,
		'discount_in_invoice': discount_in_invoice,
		'discount_mismatch': -1 * doc.discount if doc.discount else 0,
		'incentive': cpv.incentive,
		'additional_discount': total_discount - discount_in_invoice,
		'investment_discount': omc.incentive_on_investment
	}