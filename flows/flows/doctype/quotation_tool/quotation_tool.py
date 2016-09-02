# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import codecs
import os
import json

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe.utils.email_lib.email_body import get_email
from frappe.utils.email_lib.smtp import send
from frappe.modules import get_doc_path
import csv


class QuotationTool(Document):
	def before_print(self):
		pass

	# if hasattr(self, 'row'):
	# return
	#
	# if self.row:
	# 	return
	#
	# frappe.msgprint("Before print row over-ride ran")
	#
	# json_file = json.loads(self.cpv_json)
	# json_file = [
	# 	frappe._dict({json_file[0][index]: value for index, value in enumerate(x)}) for x in json_file[1:]
	# ]
	# json_file = json_file[0]
	#
	#
	#
	# if json_file:
	# 	self.row = json_file
	#
	# 	if self.price_bump:
	# 		frappe.msgprint("Price bumped from {}".format(self.row['Landed']))
	# 		self.row['Landed'] = flt(self.row['Landed']) + flt(self.price_bump)
	# 		frappe.msgprint("to {}".format(self.row['Landed']))


	def send_emails(self):

		csv_file = json.loads(self.cpv_json)
		json_file = [
			frappe._dict({csv_file[0][index]: value for index, value in enumerate(x)}) for x in csv_file[1:]
		]

		pending_list = [csv_file[0]]

		# json_file = [json_file[10]]
		# json_file = json_file[:10]

		# frappe.msgprint(json_file)

		for index, row in enumerate(json_file):

			if self.price_bump:
				row['Landed'] = flt(row['Landed']) + flt(self.price_bump)

			row['Landed'] = flt(row['Landed'])

			email_list = [
				c[0] for c in frappe.db.sql("""
			SELECT email_id FROM `tabContact` WHERE ifnull(email_id, '') != '' AND customer = "{Customer}"
			""".format(**row))
			]

			if not email_list:
				frappe.msgprint("Email not found for {Customer}.".format(**row))
				pending_list.append(csv_file[index + 1])
				continue

			# frappe.msgprint(row)

			frappe.msgprint("Sending email to {}".format(email_list))


			# row.letter_head = False
			from premailer import transform

			# email_content = frappe.get_print_format('Quotation Tool', self.name, 'Quotation Email')

			email_content = self.render({'doc': {'row': row} })


			email = transform(email_content, base_url=frappe.conf.host_name + '/')

			email_object = get_email(
				email_list, sender='',
				msg='',
				subject='LPG price for SEP*-2016: {Customer}'.format(**row),
				formatted=False, print_html=email
			)

			if self.cc:
				email_object.cc.append(self.cc)
				email_object.reply_to = self.cc

			send(email_object)

		with open('/tmp/quote_report.csv', 'wb') as csvfile:
			spamwriter = csv.writer(csvfile)
			for x in pending_list:
				spamwriter.writerow(x)

		frappe.msgprint(pending_list)

		with open('/tmp/quote_report.csv', 'r') as f:
			content = f.read()

		email_object = get_email(
				self.cc, sender='',
				msg='PFA report file',
				subject='Quote run report',
				formatted=False,
				attachments=[{'fname': 'email_not_found_report.csv', 'fcontent': content}]
			)

		send(email_object)


	def render(self, row):
		jenv = frappe.get_jenv()
		template = jenv.from_string(get_print_format('Quotation Tool', 'Quotation Email'))
		return template.render(**row)


@frappe.whitelist()
def upload():
	from frappe.utils.csvutils import read_csv_content_from_uploaded_file

	csv_content = read_csv_content_from_uploaded_file()
	return filter(lambda x: x and any(x), csv_content)


standard_format = "templates/print_formats/standard.html"


def get_print_format(doctype, format_name):
	if format_name == standard_format:
		return format_name

	opts = frappe.db.get_value("Print Format", format_name, "disabled", as_dict=True)
	if not opts:
		frappe.throw("Print Format {0} does not exist".format(format_name), frappe.DoesNotExistError)
	elif opts.disabled:
		frappe.throw("Print Format {0} is disabled".format(format_name), frappe.DoesNotExistError)

	# server, find template
	path = os.path.join(get_doc_path(frappe.db.get_value("DocType", doctype, "module"),
									 "Print Format", format_name), frappe.scrub(format_name) + ".html")

	if os.path.exists(path):
		with codecs.open(path, "r", encoding='utf=8') as pffile:
			return pffile.read()
	else:
		html = frappe.db.get_value("Print Format", format_name, "html")
		if html:
			return html
		else:
			frappe.throw("No template found at path: {0}".format(path),
						 frappe.TemplateNotFoundError)
