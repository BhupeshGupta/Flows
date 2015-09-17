# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe


class VendorGatepassTool(Document):
	def create_vouchers(self):
		vouchers = []

		for x in self.items:
			o = frappe._dict({})

			o.out_q = x.delivered_quantity
			o.in_q = x.received_quantity

			for gatepass_type in ('In', 'Out'):
				qty = o.get(gatepass_type.lower() + '_q')
				if qty > 0:
					vouchers.append(
						frappe.get_doc({
						'doctype': 'Gatepass',
						'voucher_type': 'Vendor',
						'gatepass_type': gatepass_type,
						'transaction_date': self.stock_date,
						'posting_date': self.stock_date,
						'vehicle': 'Self',
						'driver': x.vendor,
						'warehouse': self.warehouse,
						'dispatch_destination': 'Other',
						'remarks': x.remarks,
						'items': [
							{
							'item': self.item_received if gatepass_type == 'In' else self.delivered_item,
							'quantity': qty
							}
						]
						})
					)

		for v in vouchers:
			v.submit()

		frappe.msgprint('Created {} vendor gatepass vouchers'.format(len(vouchers)))