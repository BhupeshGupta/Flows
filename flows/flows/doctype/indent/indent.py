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
from frappe.utils import today, now, add_days
from flows.flows.hpcl_interface import HPCLCustomerPortal, LoginError, ServerBusy


class Indent(Document):
	def __init__(self, *args, **kwargs):
		super(Indent, self).__init__(*args, **kwargs)
		self.set_missing_values()

	def onload(self):
		"""Load Gatepasses `__onload`"""
		self.load_gatepasses()

	def validate(self):
		for indent_item in self.indent:
			validate_bill_to_ship_to(indent_item.customer, indent_item.ship_to, self.posting_date)
			if not indent_item.ship_to:
				indent_item.ship_to = indent_item.customer

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

	def load_gatepasses(self):
		self.get("__onload").gp_list = frappe.get_all("Gatepass",
													  fields="*", filters={'indent': self.name, 'docstatus': 1})


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


def get_indent_list(doctype, txt, searchfield, start, page_len, filters):
	# posting_date >= '2015-05-01' // feature start date
	rs = frappe.db.sql("""
	SELECT gp.name as name,
	gpi.item as item,
	sum(gpi.quantity) as qty,
	gp.posting_date as posting_date,
	gp.route as route
	FROM `tabGatepass` gp, `tabGatepass Item` gpi
	WHERE gp.name in (
		SELECT name FROM `tabGatepass`
		WHERE posting_date >= '2015-05-01'
		AND vehicle = '{vehicle}'
		AND ifnull(indent, '') = ''
		AND name like '%{txt}%'
		AND docstatus = 1
	)
	AND gp.name = gpi.parent
	GROUP BY gp.name, gpi.item;
	""".format(txt=txt, **filters), as_dict=True)

	rs_map = {}
	for r in rs:
		rs_map.setdefault(r.name, frappe._dict({}))
		rs_dict = rs_map[r.name]
		rs_dict.setdefault('items', [])

		rs_dict.route = r.route
		rs_dict.posting_date = frappe.utils.formatdate(r.posting_date)
		rs_dict['items'].append('{} X {}'.format(int(r.qty), r.item))

	result = []
	for key, rs_dict in rs_map.items():
		result.append([key, '{} {} [{}]'.format(rs_dict.posting_date, rs_dict.route, ','.join(rs_dict['items']))])

	return result


@frappe.whitelist()
def link_with_gatepass(gatepass, indent):
	frappe.db.sql("""UPDATE `tabGatepass` SET indent = '{indent}' WHERE name = '{name}'""".
					  format(indent=indent, name=gatepass))
	frappe.msgprint("Linked Gatepass")


@frappe.whitelist()
def get_allowed_vehicle(doctype, txt, searchfield, start, page_len, filters):
	superset_of_vehicles = set([x[0] for x in frappe.db.sql("""
		select name from `tabTransportation Vehicle`
		where {} like '%{}%';
		""".format(searchfield, txt))])

	from flows.flows.report.purchase_cycle_report.purchase_cycle_report import get_data

	vehicles_with_state = get_data(frappe._dict())
	bad_vehicles_set = set([x.indent.vehicle for x in vehicles_with_state if x.bill_state == 'Pending'] + ['Self'])

	rs = list(superset_of_vehicles - bad_vehicles_set)

	return [[x] for x in rs]


def validate_bill_to_ship_to(bill_to, ship_to, date):
	def raise_error():
		frappe.throw("{}'s material is not allowed to be shipped to {}".format(bill_to, ship_to))

	if not ship_to:
		return True
	if ship_to.strip() == '':
		return True
	if bill_to == ship_to:
		return True

	rs = frappe.db.sql("""
	SELECT DISTINCT ri.customer, ri.parent
	FROM `tabBill To Ship To Rules Item` ri, `tabBill To Ship To Rules` r
	WHERE (
		ri.customer="{bill_to}"
		OR ri.customer = "{ship_to}"
	)
	AND ri.parent=r.name
	AND r.valid_from <= "{date}"
	ORDER BY parent;
	""".format(bill_to=bill_to, ship_to=ship_to, date=date), as_dict=True)

	map = {}
	for i in rs:
		map.setdefault(i.parent, 2)
		map[i.parent] -= 1

	for i in map.values():
		if i == 0:
			return True

	raise_error()


@frappe.whitelist()
def fetch_account_balance_with_omc(plant, customer):
	if 'hpcl' in plant.lower():
		erpcode = frappe.db.sql('SELECT hpcl_erp_number FROM `tabCustomer` WHERE name = "{}"'.format(customer))
		return {'status': 'OK', 'balance': HPCLCustomerPortal(erpcode[0], '').get_current_balance_as_on_date()}
	return {'status': 'Not Implemented', 'balance': 0}


def fetch_and_record_hpcl_balance(for_date=None):
	from flows.stdlogger import root
	for_date = for_date if for_date else add_days(today(), -1)
	run = 0
	max_run = 2

	exception_list = []
	# from frappe.utils import now_datetime

	customer_list = frappe.db.sql("""
	SELECT name, hpcl_erp_number, hpcl_payer_password
	FROM `tabCustomer`
	WHERE ifnull(hpcl_erp_number, '') != ''
	and enabled = 1
	""", as_dict=True)

	customer_defer_list = []

	while run < max_run:
		root.debug("Run Level {}".format(run))
		for customer in customer_list:
			portal = HPCLCustomerPortal(customer.hpcl_erp_number, customer.hpcl_payer_password)
			total_debit = total_credit = 0
			msg = ''
			error = ''
			try:
				portal.login()
				total_debit, total_credit = portal.get_debit_credit_total(for_date, for_date)
			except LoginError as e:
				error = 'LoginError'
				exception_list.append((customer.name, customer.hpcl_erp_number, e))
				msg = e
			except ServerBusy as e:
				customer_defer_list.append(customer)
				error = 'TimeOut'
				if run < max_run-1:
					continue
			except Exception as e:
				exception_list.append((customer.name, customer.hpcl_erp_number, e))
				msg = e

			doc = frappe.get_doc({
			'customer': customer.name,
			'date': for_date,
			'balance': portal.get_current_balance_as_on_date(),
			'doctype': 'HPCL Customer Balance',
			'total_debit': total_debit,
			'total_credit': total_credit,
			'msg': msg,
			})

			if error:
				doc.error_type = error

			doc.ignore_permissions = True
			doc.save()
			frappe.db.commit()

		if customer_defer_list:
			customer_list = customer_defer_list
			customer_defer_list = []
			run += 1
		else:
			run = max_run