# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import re
from frappe.utils import today
from flows.flows.hpcl_interface import HPCLCustomerPortal, LoginError, ServerBusy


class HPCLPasswordExtractor(Document):
	def validate(self):
		extracted_passwords = set(re.findall(
			r'Dear customer, (.*?) is your',
			self.passoword_messages,
			re.M|re.I
		))
		already_extracted_passwords = set([p.password for p in self.pending_passwords])

		for password in (extracted_passwords - already_extracted_passwords):
			self.append('pending_passwords', {
				'password': password
			})

	def process(self):
		report = []

		password_matched = []

		customer_found_object_list = []
		password_matched_object_list = []


		for user in self.pending_users:
			registration = frappe.db.sql(
				"""
				select name, customer_code from `tabOMC Customer Registration`
				where with_effect_from <= "{today}"
				and customer = "{customer}"
				and omc = 'HPCL'
				and docstatus = 1
				order by with_effect_from desc
				limit 1
				""".format(today=today(), customer=user.customer),
				as_dict=True
			)[0]

			valid_password = None
			for password in self.pending_passwords:
				# If password is already matched an customer account, skip it
				if password.password in password_matched:
					continue

				try:
					portal = HPCLCustomerPortal(registration.customer_code, password.password)
					portal.login()
					valid_password = password
				except LoginError:
					continue
				except ServerBusy:
					pass

			if not valid_password:
				continue

			password_matched.append(valid_password.password)

			customer_found_object_list.append(user)
			password_matched_object_list.append(valid_password)

			frappe.db.sql(
			"""
			update
			`tabAccount` acc left join `tabOMC Customer Registration Credit Account` ca
			on ca.credit_account = acc.name
			set acc.username = "{}", acc.password = "{}"
			where ca.parent = "{}"
			and ca.type = "Customer Code"
			""".format(registration.customer_code, valid_password.password, registration.name),
			as_dict=True
			)

			report.append([user.customer, registration.customer_code, valid_password.password])

		for c in customer_found_object_list:
			self.remove(c)

		for p in password_matched_object_list:
			self.remove(p)

		print report

	def load_customers(self, date):
		# pending_users = [c.customer for c in self.pending_users]

		for c in frappe.db.sql(
			"""
			select customer from `tabHPCL Customer Balance`
			where date="{}"
			and error_type = "LoginError"
			and ifnull(customer, '') != ''
			""".format(date)
		):
			print c[0]
			# if c[0] not in pending_users:
			self.append('pending_users', {
				'customer': c[0]
			})