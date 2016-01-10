# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import StringIO
import csv
import json

import frappe
from frappe.model.document import Document
from frappe.utils import cstr
from frappe.utils.csvutils import UnicodeWriter

f = ['enabled', 'customer', 'plant', 'discount_in_invoice', 'discount_via_credit_note', 'incentive', 'transportation',
	 'contract_number', 'payment_mode', 'sales_tax']


class CustomerPlantVariablesTool(Document):
	def apply_data(self):
		def validate_and_insert_row(row):
			def get_hash(doc):
				values = []
				for key in sorted(doc.iterkeys()):
					if key in f:
						value = doc[key]
						try:
							value = float(value)
							value = '{0:.2f}'.format(value)
						except:
							pass
						values.append(str(value))
				hash = '#'.join(values)
				return hash

			row_hash = ', '.join(['{}: {}'.format(k, v) for k, v in row.iteritems()])

			if frappe.db.sql("""
			select name
			from `tabCustomer Plant Variables`
			where customer = "{customer}"
			and plant = "{plant}"
			and with_effect_from >= "{with_effect_from}"
			and docstatus = 1
			limit 1
			""".format(**row)):
				return 'Customer Plant Variable ({}) is not latest. Please check!'.format(row_hash)

			last_active_entry = frappe.db.sql("""
			select * from `tabCustomer Plant Variables`
			where with_effect_from <= "{with_effect_from}"
			and customer = "{customer}"
			and plant = "{plant}"
			and docstatus = 1 order by with_effect_from desc;
			""".format(**row), as_dict=True)

			if last_active_entry:
				if get_hash(last_active_entry[0]) == get_hash(row):
					frappe.msgprint("No change found.\n{} skipped.".format(row_hash))
					return

			row.update({'doctype': 'Customer Plant Variables', 'docstatus': 1})
			try:
				doc = frappe.get_doc(row)
				doc.save()
			except Exception as e:
				return '{}: {}'.format(row_hash, e)

		json_file = json.loads(self.cpv_json)
		json_file = [frappe._dict({json_file[0][index]: value for index, value in enumerate(x)}) for x in json_file[
																										  1:]]

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
def download(plant, date, as_file=True):
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

	if as_file:

		fp = StringIO.StringIO()
		writer = csv.DictWriter(fp, keys)
		writer.writeheader()
		writer.writerows(final_rows)

		# write out response as a type csv
		frappe.response['result'] = fp.getvalue()
		frappe.response['type'] = 'csv'
		frappe.response['doctype'] = "Customer Plant Variables"

		fp.close()

	else:
		return final_rows


@frappe.whitelist()
def export_hpcl_file(plant, date):
	variations = (
		('0948064', 19),
		('0948122', 35),
		('0948042', 47.5),
	)
	plant_map = {
		'hpcl bahadurgarh': 12121,
		'hpcl hoshiarpur': 12203,
		'hpcl bhatinda': 12215
	}

	discount_headers = (
		'Quantity From', 'UM', 'Factor Value  Numeric', 'B  C', 'Cur  Cod', 'Effective  Date', 'Expired  Date',
		'Cost  Meth', 'Formula/  Variable', '2nd Item  Number', 'Address  Number', 'Customer  Group', 'Item  Group',
		'Sls  Cd4', 'Order  Detail', 'Business  Unit', 'PC  1', 'Flag'
	)

	def map_hpcl_discount_row(row):
		return [{
					'Quantity From': '-9999999999999',
					'UM': 'EA',
					'Factor Value  Numeric': -1 * x[1] * row.discount,
					'B  C': 5,
					'Cur  Cod': 'INR',
					'Effective  Date': '',
					'Expired  Date': '',
					'Cost  Meth': '',
					'Formula/  Variable': '',
					'2nd Item  Number': x[0],
					'Address  Number': frappe.db.get_value('Customer', row.customer, 'hpcl_erp_number'),
					'Customer  Group': '',
					'Item  Group': '',
					'Sls  Cd4': '',
					'Order  Detail': '',
					'Business  Unit': plant_map.get(row.plant.lower(), row.plant.lower()),
					'PC  1': '',
					'Flag': ''
				} for x in variations]

	discount_rows = []
	for row in download(plant, date, as_file=False):
		discount_rows.extend(map_hpcl_discount_row(row))

	fp = StringIO.StringIO()
	writer = csv.DictWriter(fp, discount_headers)
	writer.writeheader()
	writer.writerows(discount_rows)

	# write out response as a type csv
	frappe.response['result'] = fp.getvalue()

	# write out response as a type csv
	frappe.response['result'] = fp.getvalue()
	frappe.response['type'] = 'csv'
	frappe.response['doctype'] = "Customer Plant Variables"


@frappe.whitelist()
def upload():
	from frappe.utils.csvutils import read_csv_content_from_uploaded_file
	csv_content = read_csv_content_from_uploaded_file()
	return filter(lambda x: x and any(x), csv_content)
