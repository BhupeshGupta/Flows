import frappe
from frappe.utils import get_first_day, get_last_day



def get_basic_and_additional(uplifting, doc):
	basic_discount = 4
	additional_discount = 0

	# 500 & 1000 19 kg cyld eqv. in M.T.
	if 500 * 19 / 1000 < uplifting[doc.customer] <= 1000 * 19 /1000:
		additional_discount = 2
	elif 1000 * 19 / 1000 < uplifting[doc.customer]:
		additional_discount = 3

	return basic_discount, additional_discount

uplift = {}

def eval(doc, omc, cpv):
	from_date = get_first_day(doc.transaction_date)
	# Cache expensive query results
	if from_date not in uplift:
		to_date = get_last_day(doc.transaction_date)
		uplift[from_date] = get_uplift_in_mt({'from_date': from_date, 'to_date': to_date})

	uplifting = uplift[from_date]

	basic_discount, additional_discount = get_basic_and_additional(uplifting, doc)

	discount_to_be_claimed = basic_discount + additional_discount

	# doc.discount is -ve in case discount is not received
	discount_in_invoice = cpv.discount + doc.discount

	return {
		'discount_in_invoice': discount_in_invoice,
		'discount_mismatch': -1 * doc.discount if doc.discount else 0,
		'incentive': cpv.incentive,
		'additional_discount': discount_to_be_claimed - discount_in_invoice,
		'investment_discount': omc.incentive_on_investment,
		'uplifting': uplifting
	}


def get_uplift_in_mt(filters):
	rs = frappe.db.sql(
		"""
		select t.customer, sum(t.multi * t.t_qty / 1000) as mt
		 from (
			 select customer,
			 CASE
			  WHEN item = 'FC19' THEN '19'
			  when item = 'FC35' then '35'
			  when item like 'FC47.5%' then '47.5'
			 end  as multi,
			 item, sum(qty) as t_qty
			 from `tabIndent Invoice`
			 where docstatus = 1
			 and supplier like 'iocl%'
			 and item like 'FC%'
			 and transaction_date between "{from_date}" and "{to_date}"
			 group by customer, item
		 ) t
		 group by t.customer;
		""".format(**filters), as_dict=True
	)

	rs_map = {}
	for r in rs:
		rs_map[r.customer] = r.mt

	return rs_map