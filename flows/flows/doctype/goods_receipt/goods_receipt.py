# coding=utf-8

# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _, throw
from flows import utils
from frappe.utils import today, now, cint, nowtime
from erpnext.accounts.utils import get_fiscal_year
from frappe.model.naming import make_autoname


class GoodsReceipt(Document):

	def autoname(self):
		if frappe.form_dict.client == "app" and not self.goods_receipt_number:
			year = '16'
			if self.transaction_date >= '2017-04-01':
				year = '17'
			self.name = make_autoname('GR-{}-.#'.format(year))

	def validate_book(self):
		if not self.goods_receipt_number:
			return

		verify_book_query = """
		SELECT * FROM `tabGoods Receipt Book` WHERE serial_start <= {0} AND serial_end >= {0};
		""".format(self.goods_receipt_number)

		rs = frappe.db.sql(verify_book_query, as_dict=True)

		if len(rs) == 0:
			throw(
				_("Invalid serial. Can not find any receipt book for this serial {}").format(self.goods_receipt_number)
			)
		elif cint(rs[0].gr_enabled) == 0:
			throw(
				_("Receipt Book ({} - {}) Is Not Marked For GR. Please Contact Book Manager").
					format(rs[0].serial_start, rs[0].serial_end)
			)
		elif rs[0].state == "Closed/Received":
			throw(
				_("GR Book has been closed, amendment prohibited").format(self.goods_receipt_number)
			)

		self.warehouse = rs[0].warehouse

	def validate(self):
		self.sms_tracker = None
		self.sms_response = None
		self.sms_status = None
		self.validate_book()
		self.validate_unique()
		self.deduplicate()
		self.update_trip()

	def update_trip(self):
		if self.trip_id:
			return

		trip = frappe.db.sql("""
		select name
		from `tabVehicle Trip`
		where vehicle = '{}'
		and ifnull(in_gatepass, '') = ''
		""".format(self.vehicle))

		if not trip:
			return

		self.trip_id = trip[0][0]

	def deduplicate(self):
		if frappe.form_dict.client == "app":
			# Get current time - 1 hour
			vars = self.as_dict()
			time = nowtime()
			time = time.split(':')
			time[0] = str(int(time[0]) - 1)
			time = ':'.join(time)

			# set creation time to 1 hour back from current time
			vars['creation'] = time

			voucher = frappe.db.sql(
				"""
				select name
				from `tabGoods Receipt`
				where creation >= "{creation}"
				and posting_date = "{posting_date}"
				and customer = "{customer}"
				and vehicle = "{vehicle}"
				and item_delivered = "{item_delivered}"
				and delivered_quantity = "{delivered_quantity}"
				and item_received = "{item_received}"
				and received_quantity = "{received_quantity}"
				""".format(**vars), as_dict=True
			)

			if voucher:
				frappe.throw( "Entry OK. Challan Number {}".format(voucher[0].name))


	def validate_date(self):
		gr_eod = frappe.db.get_single_value("End Of Day", "gr_eod")
		if self.posting_date <= gr_eod and not frappe.session.user == "Administrator":
			frappe.throw("Day Closed: {}. Day has been closed for GR. No amendment is allowed in closed days".format(gr_eod))

		# Skip future check if posting is from app
		if frappe.form_dict.client == "app":
			return

		if utils.get_next_date(gr_eod) < self.posting_date:
			frappe.throw("Day Closed: {}. Date is disabled for entry, will be allowed when previous day is closed".format(gr_eod))

	def validate_unique(self):
		if not self.goods_receipt_number:
			return

		rs = frappe.db.sql("select name from `tabPayment Receipt` where name=\"{0}\" or name like \"{0}-%\"".format(self.goods_receipt_number))
		if len(rs) > 0:
			throw("Payment Receipt with this serial already exists {}".format(self.goods_receipt_number))

	def validate_item(self):
		def scrub(item):
			return 'item_' + item.replace('EC', 'FC').lower().replace('.', '_') if item else ''

		if not self.customer:
			return

		validity_hash = frappe.db.sql("""
		select item_fc19, item_fc35, item_fc47_5, item_fc47_5l from `tabCustomer` where name = "{}"
		""".format(self.customer), as_dict=True)[0]

		if cint(validity_hash.get(scrub(self.item_delivered), 1)) == 0\
			or cint(validity_hash.get(scrub(self.item_received), 1)) == 0:
			frappe.throw("""
			Item is not enabled for customer {} GR({}). Please verify item or contact admin.
			""".format(self.customer, self.name))

	def on_submit(self):
		self.validate_date()
		self.validate_item()
		if self.warehouse == '' or not self.warehouse:
			throw(
				_("Warehouse Not Linked With Book. Please Contact Receipt Book Manager")
			)
		self.transfer_stock()

		if frappe.form_dict.client == "app":
			try:
				self.send_sms()
			except Exception as e:
				print(e)

	def on_cancel(self):
		self.validate_date()
		self.validate_book()
		self.transfer_stock()

	def transfer_stock(self):

		if cint(self.cancelled) == 1:
			return

		from erpnext.stock.stock_ledger import make_sl_entries

		self.set_missing_values()

		# Commented for staggered phase 1
		# transportation_vehicle_warehouse = utils.get_or_create_vehicle_stock_account(self.vehicle, self.company)
		# transportation_vehicle_warehouse_name = transportation_vehicle_warehouse.name

		transportation_vehicle_warehouse_name = self.warehouse

		# TODO: write a method to find the same
		customer_warehouse_name = utils.get_or_create_customer_stock_account(self.customer, self.company).name

		sl_entries = []

		if self.item_delivered and self.delivered_quantity:
			sl_entries.append(
				self.get_sl_entry({
				"item_code": self.item_delivered,
				"actual_qty": -1 * self.delivered_quantity,
				"warehouse": transportation_vehicle_warehouse_name
				})
			)

			sl_entries.append(
				self.get_sl_entry({
				"item_code": self.item_delivered,
				"actual_qty": self.delivered_quantity,
				"warehouse": customer_warehouse_name
				})
			)

		if self.item_received and self.received_quantity:

			if self.item_received.startswith('E'):

				empty_cylinders_available_at_customers_warehouse = frappe.db.sql("""
                SELECT sum(actual_qty) AS current_quantity FROM `tabStock Ledger Entry` WHERE docstatus < 2
                AND item_code="{}" AND warehouse="{}";
                """.format(self.item_received, customer_warehouse_name), as_dict=1)[0]['current_quantity']

				empty_cylinders_available_at_customers_warehouse = empty_cylinders_available_at_customers_warehouse \
					if empty_cylinders_available_at_customers_warehouse else 0

				filled_cylinders_available_at_customers_warehouse = frappe.db.sql("""
                SELECT sum(actual_qty) AS current_quantity FROM `tabStock Ledger Entry` WHERE docstatus < 2
                AND item_code="{}" AND warehouse="{}";
                """.format(self.item_received.replace('E', 'F'), customer_warehouse_name), as_dict=1)[0][
					'current_quantity']

				filled_cylinders_available_at_customers_warehouse = filled_cylinders_available_at_customers_warehouse \
					if filled_cylinders_available_at_customers_warehouse else 0

				new_empty_cylinder_quantity = empty_cylinders_available_at_customers_warehouse - self.received_quantity

				if new_empty_cylinder_quantity < 0:
					cylinders_consumed_from_last_gr_entry = min(
						-1 * new_empty_cylinder_quantity,
						filled_cylinders_available_at_customers_warehouse
					)
				else:
					cylinders_consumed_from_last_gr_entry = 0

				if cylinders_consumed_from_last_gr_entry > 0:

					for sl_e in self.convert_items_empty_in_place(
							self.item_received.replace('E', 'F'),
							self.item_received,
							cylinders_consumed_from_last_gr_entry,
							customer_warehouse_name
					):
						sl_e['process'] = 'Consumption'
						sl_entries.append(sl_e)

			sl_entries.append(
				self.get_sl_entry({
				"item_code": self.item_received,
				"actual_qty": -1 * self.received_quantity,
				"warehouse": customer_warehouse_name
				})
			)

			sl_entries.append(
				self.get_sl_entry({
				"item_code": self.item_received,
				"actual_qty": 1 * self.received_quantity,
				"warehouse": transportation_vehicle_warehouse_name
				})
			)

		make_sl_entries(sl_entries)

	def convert_items_empty_in_place(self, from_item, to_item, item_quantity, in_warehouse):
		conversion_sl_entries = []

		conversion_sl_entries.append(
			self.get_sl_entry({
			"item_code": from_item,
			"actual_qty": -1 * item_quantity,
			"warehouse": in_warehouse
			})
		)
		conversion_sl_entries.append(

			self.get_sl_entry({
			"item_code": to_item,
			"actual_qty": 1 * item_quantity,
			"warehouse": in_warehouse
			})
		)

		return conversion_sl_entries

	def get_sl_entry(self, args):
		sl_dict = frappe._dict(
			{
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"actual_qty": 0,
			"incoming_rate": 0,
			"company": self.company,
			"fiscal_year": self.fiscal_year,
			"is_cancelled": self.docstatus == 2 and "Yes" or "No"
			})

		sl_dict.update(args)
		return sl_dict

	def set_missing_values(self):
		for fieldname in ["posting_date", "posting_time" "transaction_date"]:
			if not self.get(fieldname):
				self.set(fieldname, today())

		if not self.get("posting_time"):
			self.posting_time = now()

		if not self.get("fiscal_year"):
			self.fiscal_year = get_fiscal_year(self.posting_date)[0]

	def add_comment(self, comment_type, text=None):
		result = super(GoodsReceipt, self).add_comment(comment_type, text)

		client = frappe.form_dict.client
		exec_attach = comment_type == "Attachment" and client == "app"
		if exec_attach:
			file_field = frappe.form_dict.file_field
			file_url = text.split("'")[1]

			frappe.db.sql("""
			UPDATE `tabGoods Receipt` set {key}="{value}" where name = "{name}";
			""".format(key=file_field, value=file_url, name=self.name))

		return result

	def send_sms(self):
		from frappe.utils.data import getdate

		template = """Dear Customer {delivered_quantity} no of {item_delivered} kg cylinders delivered against the GR
		No {name} Dt {txn_date} & {received_quantity} no of {item_received} kg empty cylinder received
		from your premises."""

		txn_date = getdate(self.transaction_date).strftime("%d/%m/%y")
		context = self.as_dict()

		# `0` Int Keys
		for key in ['delivered_quantity', 'received_quantity']:
			context[key] = context[key] if context[key] else 0

		# empty string keys
		for key in ['item_delivered', 'item_received']:
			context[key] = context[key].replace('FC', '').replace('EC', '').replace('L', '') if context[key] else ''

		msg = template.format(txn_date=txn_date, **context)

		receiver_list = [
			c[0] for c in frappe.db.sql("""
			SELECT phone FROM `tabContact` WHERE ifnull(sms_optin, 0) = 1 AND customer = "{customer}"
			""".format(customer=self.customer)) if str(c[0]).strip() != ''
		]

		if not receiver_list:
			return

		success, return_value = self.send_sms_via_gateway(receiver_list, msg)

		if success:
			frappe.db.sql("""
			UPDATE `tabGoods Receipt` SET sms_tracker="{sms_tracker}" WHERE name = "{id}"
			""".format(sms_tracker=return_value['data']['group_id'], id=self.name))
		else:
			frappe.db.sql("""
			UPDATE `tabGoods Receipt` SET sms_response="{sms_response}" WHERE name = "{id}"
			""".format(sms_response=str(return_value), id=self.name))

		return success


	def send_sms_via_gateway(self, receiver_list, msg):
		from erpnext.setup.doctype.sms_settings.sms_settings import validate_receiver_nos, send_via_gateway, \
			get_sender_name
		import json

		receiver_list = validate_receiver_nos(receiver_list)

		arg = {
		'receiver_list': [','.join(receiver_list)],
		'message': msg,
		'sender_name': get_sender_name()
		}

		if frappe.db.get_value('SMS Settings', None, 'sms_gateway_url'):
			ret = send_via_gateway(arg)
			try:
				ret_json = json.loads(ret[0])

				if ret_json['status'] == 'OK':
					return True, ret_json
			except (ValueError, TypeError) as e:
				frappe.msgprint("Unable to send Msg {} {} {}".format(msg, ret, e))
				return False, ret
		else:
			frappe.msgprint("Please Update SMS Settings")

		return False, None

	def send_email(self):
		context = self.as_dict()
		email_list = [
			c[0] for c in frappe.db.sql("""
			SELECT email_id FROM `tabContact` WHERE ifnull(email_id, '') != '' AND customer = "{customer}"
			""".format(**context))
		]

		email_list = 'bhupesh00gupta@gmail.com'

		frappe.msgprint("Sending GR email to {}".format(email_list))
		from frappe.utils.email_lib.email_body import get_email
		from frappe.utils.email_lib.smtp import send

		from premailer import transform

		email_content = frappe.get_print_format('Goods Receipt', self.name, 'Goods Receipt Email')

		email = transform(email_content, base_url=frappe.conf.host_name + '/')

		import base64

		# u'सिलिंडर पूर्ति रिपोर्ट: अरुण गॅस दिनाक
		subject = '\n'.join([
			'=?utf-8?B?{}?='.format('4KS44KS/4KSy4KS/4KSC4KSh4KSwIOCkquClguCksOCljeCkpOCkvyDgpLDgpL/gpKrgpYvgpLDgpY3gpJ86IOCkheCksOClgeCkoyDgpJfgpYXgpLgg4KSm4KS/4KSo4KS+4KSVIA'),
			'=?utf-8?B?{}?='.format(base64.b64encode(frappe.format_value(self.transaction_date, {'fieldtype': 'Date'})))
		])

		subject = subject
		send(
			get_email(
				email_list, sender='',
				msg='',
				subject=subject,
				formatted=False, print_html=email
			)
		)