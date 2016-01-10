# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import csv
import sys
import json

import StringIO


class CustomerPlantVariablesTool(Document):
	def apply_data(self):
		def validate_and_insert_row(row):
			row_hash = ', '.join(['{}: {}'.format(k, v) for k, v in row.iteritems()])

			if frappe.db.sql("""
			select name
			from `tabCustomer Plant Variables`
			where customer = "{customer}"
			and plant = "{plant}"
			and with_effect_from >= "{with_effect_from}"
			limit 1
			""".format(**row)):
				return 'Customer Plant Variable ({}) is not latest. Please check!'.format(row_hash)

			row.update({'doctype': 'Customer Plant Variables', 'docstatus': 1})
			try:
				doc = frappe.get_doc(row)
				doc.save()
			except Exception as e:
				return '{}: {}'.format(row_hash, e)

		json_file = json.loads(self.cpv_json)
		json_file = [frappe._dict({json_file[0][index]: value for index, value in enumerate(x)}) for x in json_file[1:]]

		error_list = []
		for row in json_file:
			error = validate_and_insert_row(row)
			if error:
				error_list.append(error)

		if error_list:
			frappe.db.rollback()
			for error in error_list:
				frappe.msgprint("Did Not create!")
				frappe.msgprint(error)
		else:
			frappe.db.commit()
			frappe.msgprint("Customer Plant Variables Created")

@frappe.whitelist()
def download(plant, date):
	def map_row(row):
		return row if row else None

	keys = (
		'with_effect_from', 'customer', 'discount', 'discount_via_credit_note', 'incentive',
		'transportation', 'contract_number', 'plant', 'payment_mode', 'sales_tax', 'enabled'
	)

	final_rows = []
	hp_instance = None

	for c in frappe.db.sql(
			"""
			select distinct customer
			from `tabIndent Invoice`
			where docstatus = 1
			and transaction_date > '2015-10-01';
			"""
	):
		customer = c[0]
		hp = frappe.db.sql("""
		SELECT with_effect_from, customer, discount,
		discount_via_credit_note, incentive, transportation,
		contract_number, plant, payment_mode, sales_tax, enabled
		from `tabCustomer Plant Variables`
		where with_effect_from <= "{date}"
		and customer = "{customer}"
		and plant like "{plant}"
		and docstatus = 1 order by with_effect_from desc;
		""".format(date=date, plant=plant, customer=customer), as_dict=True)
		if hp:
			hp = hp[0]
			final_rows.append(map_row(hp))
			hp_instance = hp

	fp = StringIO.StringIO()
	writer = csv.DictWriter(fp, keys)
	writer.writeheader()
	writer.writerows(final_rows)

	# write out response as a type csv
	frappe.response['result'] = fp.getvalue()
	frappe.response['type'] = 'csv'
	frappe.response['doctype'] = "Customer Plant Variables"

	fp.close()


@frappe.whitelist()
def upload():
	from frappe.utils.csvutils import read_csv_content_from_uploaded_file
	csv_content = read_csv_content_from_uploaded_file()
	return filter(lambda x: x and any(x), csv_content)
