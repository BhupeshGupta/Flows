# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint

from flows.flows.doctype.c_form_indent_invoice.c_form_indent_invoice import get_quarter_start_end


class CFormTool(Document):
	def get_conditions(self):
		cond = []
		start, end = get_quarter_start_end(self.fiscal_year, self.quarter)
		cond.append(' transaction_date between "{}" and "{}" '.format(start, end))

		if self.supplier_filter:
			cond.append('supplier like "{}"'.format(self.supplier_filter))

		if not cond:
			cond.append('1=1')

		return ' and '.join(cond)

	def generate_c_forms(self):
		for pair in frappe.db.sql("""
		select t.customer as customer, s.name as supplier
		from (
			select DISTINCT i.customer, s.tin_number
			from `tabIndent Invoice` i join `tabSupplier` s on i.supplier = s.name
			where i.sales_tax='CST' AND {cond}
			and i.docstatus = 1
		) t join `tabSupplier` s on s.tin_number=t.tin_number
		where s.supplier_type='OMC STATE';
		""".format(cond=self.get_conditions()), as_dict=True):
			try:
				doc = frappe.get_doc({
					'doctype': 'C Form Indent Invoice',
					'customer': pair.customer,
					'supplier': pair.supplier,
					'quarter': self.quarter,
					'fiscal_year': self.fiscal_year
				})
				doc.save()
				frappe.msgprint("C Form Generated for {customer}".format(**pair))
			except Exception as e:
				frappe.msgprint("Failed to create c form for {customer}".format(**pair))
		frappe.msgprint("Done")

	def send_reminders(self):
		for cform in frappe.db.sql("""
		SELECT `name`, supplier,
		customer, fiscal_year,
		`quarter`, amount_with_tax
		FROM `tabC Form Indent Invoice`
		WHERE docstatus != 2
		AND ifnull(c_form_number, '') = ''
		AND {cond}
		ORDER BY customer;
		""".format(
				cond=self.get_conditions() if self.filter_reminders else '1=1'
		), as_dict=True):

			frappe.msgprint(cform.name)

			# Send sms
			if cint(self.sms) == 1:
				msg = """Dear Customer request you to issue Form C in favour of {supplier} for LPG supplied during {quarter} Quarter of F.Y. {fiscal_year}.""".format(**cform)
				receiver_list = [
					c[0] for c in frappe.db.sql("""
				SELECT phone FROM `tabContact` WHERE ifnull(sms_optin, 0) = 1 AND customer = "{customer}"
				""".format(**cform))
				]

				if receiver_list:
					frappe.msgprint((msg, receiver_list))
					send_sms(receiver_list, msg)

			# Send emails
			if cint(self.email) == 1:

				email_list = [
					c[0] for c in frappe.db.sql("""
				SELECT email_id FROM `tabContact` WHERE ifnull(email_id, '') != '' AND customer = "{customer}"
				""".format(**cform))
				]
				if email_list:
					frappe.msgprint("sending email to {}".format(email_list))
					from frappe.utils.email_lib.email_body import get_email
					from frappe.utils.email_lib.smtp import send

					cform.letter_head = False
					from premailer import transform

					email_content = frappe.get_print_format('C Form Indent Invoice', cform.name,
															'C Form Request Letter')

					if self.message_box:
						email_content = '<strong>{}</strong><br/><br/>'.format(self.message_box) + email_content

					email = transform(email_content, base_url=frappe.conf.host_name + '/')
					frappe.msgprint(email)

					email_object = get_email(
							email_list, sender='',
							msg='',
							subject='Submission of Form-C Quarterwise for in favour of {supplier} for {quarter} '
									'Quarter of F.Y. {fiscal_year}: {customer}'.format(
								**cform),
							formatted=False, print_html=email
						)

					if self.cc:
						email_object.cc.append(self.cc)
						email_object.reply_to = self.cc

					send(email_object)


def send_sms(receiver_list, msg):
	from erpnext.setup.doctype.sms_settings.sms_settings import validate_receiver_nos, get_sender_name, \
		send_via_gateway

	receiver_list = validate_receiver_nos(receiver_list)
	arg = {
	'receiver_list': [','.join(receiver_list)],
	'message': msg,
	'sender_name': get_sender_name()
	}
	frappe.msgprint(send_via_gateway(arg))