# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from flows.flows.controller.utils import get_portal_user_password
from flows.flows.iocl_interface import IOCLPortal
import json
from flows.flows.controller.iocl_controller import IOCL_PLANT_CODE_MAP
from frappe.utils import flt, today
from flows.flows.pricing_controller import compute_base_rate_for_a_customer

IOCL_PLANT_TO_CODE_MAP = {v: k for k, v in IOCL_PLANT_CODE_MAP.items()}


class CustomerPlantVariables(Document):
	def autoname(self):
		self.name = '{}#{}#{}'.format(
			str(self.customer).strip(),
			str(self.plant).strip(),
			self.with_effect_from
		)

	def before_submit(self):
		if hasattr(self, 'ignore_invoice_check'):
			return

		rs = frappe.db.sql(
			"""
			select name, transaction_date from `tabIndent Invoice`
			where transaction_date >= "{}"
			and customer = "{}"
			and supplier = "{}"
			and docstatus = 1
			order by transaction_date asc
			""".format(self.with_effect_from, self.customer, self.plant)
		)

		if not rs:
			return

		frappe.throw(
			"Following invoices are submitted with previous CPV. Cancel these before submitting new variable. \n\n{}"
				.format('\n'.join(['{1} <a href="/desk#Form/Indent Invoice/{0}">{0}</a>'.format(x[0], x[1]) for x in rs]))
		)


@frappe.whitelist()
def validate_variables_with_omc(cpv):
	# from flows.stdlogger import root
	cpv = frappe._dict(json.loads(cpv))

	mismatch = {}
	if 'iocl' in cpv.plant.lower():
		user, passwd = get_portal_user_password(cpv.customer, 'IOCL')
		customer_code = frappe.db.sql(
			"""
			select customer_code
			from `tabOMC Customer Registration`
			where docstatus = 1
			and customer = "{}"
			order by with_effect_from DESC
			limit 1
			""".format(cpv.customer)
		)[0][0]
		portal = IOCLPortal(user, passwd)
		portal.login()
		pricing = portal.get_pricing(customer_code, IOCL_PLANT_TO_CODE_MAP[cpv.plant], 'M00002', c_form=(cpv.sales_tax == 'CST'))

		if not pricing.get('Spl Discount-Pre Tax', 0)/19 == -1 * cpv.discount:
			mismatch['Discount'] = {'expected': cpv.discount, 'loaded': -1 * flt(pricing.get('Spl Discount-Pre Tax', 0))/19}

		if not pricing.get('Delivery Assistance', 0)/19 == cpv.transportation:
			mismatch['Delivery Assistance'] = {'expected': cpv.transportation, 'loaded': pricing.get('Delivery Assistance', 0)/19}

		rate_per_item = compute_base_rate_for_a_customer(cpv.customer, cpv.plant, 'FC19', today())
		loaded_price = pricing.get('Total', 0) - pricing.get('Rounding Difference', 0)

		if round(abs(loaded_price - rate_per_item) / 19, 2) > .01:
			mismatch['Total'] = {'expected': round(rate_per_item/19, 2), 'loaded': round(loaded_price/19, 2)}
	else:
		mismatch['Message'] = "Not Implemented yet for this OMC"

	return mismatch