# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from summary_aggr import get_data as get_day_summary


class EndOfDay(Document):
	def validate(self):
		old_gr_eod = frappe.db.get_single_value("End Of Day", "gr_eod")

		if self.gr_eod < old_gr_eod:
			if frappe.session.user == "Administrator":
				frappe.msgprint("Day/Days Unlocked")
			else:
				frappe.throw("Can Not Unlock Days")

	def before_save(self):
		old_gr_eod = frappe.db.get_single_value("End Of Day", "gr_eod")
		self.send_sms_from_gr_from_to_day(old_gr_eod, self.gr_eod)

	def before_print(self):
		self.summary = get_day_summary(self.report_date, self.report_warehouse)

	def send_sms_from_gr_from_to_day(self, from_day, to_day):
		for gr in frappe.db.sql("""
		SELECT gr.name
		FROM `tabGoods Receipt` gr, `tabContact` contact
		WHERE gr.customer = contact.customer
		AND ifnull(contact.sms_optin, 0) = 1
		AND gr.docstatus = 1
		AND gr.posting_date > "{from_day}" AND gr.posting_date <= "{to_day}"
		AND (gr.item_delivered like 'FC%' or gr.item_received like 'EC%')
		AND ifnull(gr.sms_tracker, '') = '';
		""".format(from_day=from_day, to_day=to_day), as_dict=True):
			gr_doc = frappe.get_doc('Goods Receipt', gr.name)
			gr_doc.send_sms()

