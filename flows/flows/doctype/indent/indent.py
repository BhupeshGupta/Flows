# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

from flows import utils as flows_utils
from erpnext.stock.stock_ledger import make_sl_entries

from frappe.model.document import Document

import frappe
import frappe.defaults
from flows import utils as flow_utils
from frappe.utils import comma_and
from erpnext.accounts import utils as account_utils

from frappe.utils import today, now


class Indent(Document):
	def __init__(self, *args, **kwargs):
		super(Indent, self).__init__(*args, **kwargs)
		self.set_missing_values()

	def on_submit(self):
		self.process_material_according_to_indent()

	def on_cancel(self):
		self.check_next_docs()
		self.process_material_according_to_indent()

	def check_next_docs(self):
		invoices = frappe.db.sql("""
        SELECT name FROM `tabIndent Invoice` WHERE docstatus = 1 AND indent = '{}'
        """.format(self.name))

		if invoices:
			frappe.throw("Invoices {} is/are attached to this indent. Cancel those first.".format(
				comma_and(invoices)
			))

	def process_material_according_to_indent(self):

		sl_entries = []

		stock_transfer_map = self.compute_items_to_be_moved_for_refill_and_return()

		self.transfer_stock_to_ba(sl_entries, stock_transfer_map)

		self.transfer_stock_to_bottling_plant(sl_entries, stock_transfer_map)

		stock_transfer_map = self.compute_items_to_be_moved_back_after_refill_and_oneway()

		self.transfer_stock_back_to_ba(sl_entries, stock_transfer_map)

		self.transfer_stock_back_to_logistics_partner(sl_entries, stock_transfer_map)

		make_sl_entries(sl_entries)

	def compute_items_to_be_moved_for_refill_and_return(self):
		map = {}

		for indent_item in self.indent:
			if indent_item.load_type == "Refill":
				item = indent_item.item.replace('F', 'E')
				map[item] = map.get(item, 0) + indent_item.qty

		# TODO: add return qty

		return map

	def compute_items_to_be_moved_back_after_refill_and_oneway(self):
		map = {}

		for indent_item in self.indent:
			if indent_item.load_type in ("Refill", "Oneway"):
				item = indent_item.item
				map[item] = map.get(item, 0) + indent_item.qty

		return map

	def transfer_stock_to_ba(self, sl_entries, stock_transfer_map):

		vehicle_warehouse_logistics_partner = flows_utils.get_or_create_vehicle_stock_account(
			self.vehicle, self.logistics_partner
		)

		vehicle_warehouse_indent_owner = flows_utils.get_or_create_vehicle_stock_account(
			self.vehicle, self.company
		)

		if vehicle_warehouse_logistics_partner.name == vehicle_warehouse_indent_owner.name:
			return

		for item, qty in stock_transfer_map.iteritems():
			for e in self.transfer_stock(
					item, qty, vehicle_warehouse_logistics_partner,
					vehicle_warehouse_indent_owner, process='Transfer'
			):
				sl_entries.append(e)

		return sl_entries

	def transfer_stock_to_bottling_plant(self, sl_entries, stock_transfer_map):

		vehicle_warehouse_ba = flows_utils.get_or_create_vehicle_stock_account(
			self.vehicle, self.company
		)

		bottling_plant_account = flow_utils.get_suppliers_warehouse_account(
			self.plant, self.company
		)

		for item, qty in stock_transfer_map.iteritems():
			for e in self.transfer_stock(
					item, qty, vehicle_warehouse_ba,
					bottling_plant_account, process='Transfer'
			):
				sl_entries.append(e)

		return sl_entries


	def transfer_stock_back_to_ba(self, sl_entries, stock_transfer_map):

		vehicle_warehouse_ba = flows_utils.get_or_create_vehicle_stock_account(
			self.vehicle, self.company
		)

		bottling_plant_account = flow_utils.get_suppliers_warehouse_account(
			self.plant, self.company
		)

		for item, qty in stock_transfer_map.iteritems():
			for e in self.transfer_stock(
					item, qty, bottling_plant_account,
					vehicle_warehouse_ba, process='Transfer'
			):
				sl_entries.append(e)

		return sl_entries


	def transfer_stock_back_to_logistics_partner(self, sl_entries, stock_transfer_map):

		vehicle_warehouse_logistics_partner = flows_utils.get_or_create_vehicle_stock_account(
			self.vehicle, self.logistics_partner
		)

		vehicle_warehouse_ba = flows_utils.get_or_create_vehicle_stock_account(
			self.vehicle, self.company
		)

		if vehicle_warehouse_logistics_partner.name == vehicle_warehouse_ba.name:
			return

		for item, qty in stock_transfer_map.iteritems():
			for e in self.transfer_stock(
					item, qty, vehicle_warehouse_ba,
					vehicle_warehouse_logistics_partner,
					process='Transfer'
			):
				sl_entries.append(e)

		return sl_entries

	def transfer_stock(self, item, item_quantity, from_warehouse, to_warehouse, process=''):
		conversion_sl_entries = []

		conversion_sl_entries.append(
			self.get_sl_entry({
			"item_code": item,
			"actual_qty": -1 * item_quantity,
			"warehouse": from_warehouse.name,
			"company": from_warehouse.company,
			"process": process
			})
		)
		conversion_sl_entries.append(
			self.get_sl_entry({
			"item_code": item,
			"actual_qty": 1 * item_quantity,
			"warehouse": to_warehouse.name,
			"company": to_warehouse.company,
			"process": process
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

	def set_missing_values(self, *args, **kwargs):
		if not self.posting_date:
			self.posting_date = today()
		if not self.posting_time:
			self.posting_time = now()
		self.fiscal_year = account_utils.get_fiscal_year(date=self.posting_date)[0]


@frappe.whitelist()
def make_gatepass(source_name, target_doc=None):
	import json

	doc = frappe.get_doc(json.loads(target_doc))
	doc.set('items', [])

	rs = frappe.db.sql("""
	SELECT item, sum(qty) FROM `tabIndent Item` WHERE parent = '{}' AND docstatus != 2 GROUP BY item""".
						   format(source_name))

	for r in rs:
		itm = r[0] if doc.gatepass_type.lower() == 'in' else r[0].replace('FC', 'EC')
		doc.append('items', {'item': itm, 'quantity': r[1]})

	doc.dispatch_destination = 'Plant'

	return doc.as_dict()