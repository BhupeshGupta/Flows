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
from frappe.utils import today, now, add_days, get_first_day, get_last_day
from flows.flows.hpcl_interface import HPCLCustomerPortal
from flows.flows.iocl_interface import IOCLPortal
from flows.flows.controller.utils import get_portal_user_password
from frappe.utils import cint

class Indent(Document):
	def __init__(self, *args, **kwargs):
		super(Indent, self).__init__(*args, **kwargs)
		self.set_missing_values()

	def onload(self):
		"""Load Gatepasses `__onload`"""
		self.load_gatepasses()

	def validate(self):
		self.validate_customer()
		self.validate_registration_and_customer_plant_variables()
		self.validate_cross_sale_limit()

		# If document is new or vehicle is changed in this document
		if (self.get("__islocal") or not self.get("name")) or \
			self.vehicle != frappe.db.get_value("Indent", self.name, 'vehicle'):
			if self.vehicle not in get_allowed_vehicle(self.vehicle, self.name):
				frappe.throw("""Indent is not allowed to be placed on this vehicle until previous bills are
				entered for this vehicle. You can place indent on `Self` for time being.""")

		for indent_item in self.indent:
			validate_bill_to_ship_to(indent_item.customer, indent_item.ship_to, self.posting_date)
			if not indent_item.ship_to:
				indent_item.ship_to = indent_item.customer
			validate_c_form(indent_item.customer, self.plant, self.posting_date)

		for i, indent in  enumerate(sorted(self.indent, key=lambda x: (x.credit_account, x.item))):
			indent.idx = i + 1

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

	def validate_cross_sale_limit(self):
		indent_amount = {}
		errors = []

		default_aggr_dict = {'amt': 0, 'qty_in_kg': 0}

		for indent_item in self.indent:
			if indent_item.cross_sold:
				indent_amount.setdefault(indent_item.customer, default_aggr_dict.copy())
				indent_amount[indent_item.customer]['amt'] += indent_item.amount
				indent_amount[indent_item.customer]['qty_in_kg'] += float(indent_item.item.replace('FC', '').replace('L', '')) * indent_item.qty

		month_end = get_last_day(self.posting_date)
		month_start = get_first_day(self.posting_date)

		for customer in indent_amount.keys():
			invoice_sum_value = frappe.db.sql("""
			select ifnull(sum(inv.actual_amount), 0) + ifnull(sum(sal.grand_total_export), 0)
			from `tabIndent Invoice` inv
			LEFT JOIN `tabSales Invoice` sal
			on inv.transportation_invoice = sal.name
			where inv.customer = "{customer}"
			and inv.docstatus = 1
			and inv.cross_sold = 1
			and inv.transaction_date between "{month_start}" and "{month_end}"
			""".format(customer=customer, month_end=month_end, month_start=month_start))[0][0]

			indent_sum = frappe.db.sql("""
			select ifnull(sum(replace(replace(itm.item, 'FC' ,''), 'L', '')*itm.qty), 0) as qty,
			ifnull(sum(itm.amount), 0) as amount
			from `tabIndent Item` itm left join `tabIndent` ind
			on itm.parent = ind.name
			where itm.name not in (
				select ifnull(indent_item, '')
				from `tabIndent Invoice`
				where docstatus = 1
			)
			and itm.parent != "{self_indent}"
			and itm.docstatus != 2
			and itm.customer = "{customer}"
			and itm.cross_sold = 1
			and ind.posting_date  between "{month_start}" and "{month_end}"
			""".format(customer=customer, month_end=month_end, month_start=month_start, self_indent=self.name), as_dict=True)[0]

			sales_rate = frappe.db.sql(
				"""
				SELECT applicable_transport_rate
				FROM `tabCustomer Sale`
				WHERE customer="{customer}"
				AND with_effect_from <= "{invoice_date}"
				AND ifnull(valid_up_to, "{invoice_date}") <= "{invoice_date}"
				AND docstatus = 1
				ORDER BY with_effect_from DESC LIMIT 1
				""".format(invoice_date=today(), customer=customer)
			)

			sales_rate = sales_rate[0][0] if sales_rate else 0

			limit = frappe.db.get_value("Customer", {'name': customer}, 'cross_sale_limit')
			limit = limit if limit else 0

			available_limit = limit - invoice_sum_value - indent_sum.amount - (float(indent_sum.qty) * float(sales_rate))

			cur_dict = indent_amount.get(customer, default_aggr_dict)
			diff = round(available_limit - cur_dict['amt'] - cur_dict['qty_in_kg'] * sales_rate, 2)

			if diff < 0:
				errors.append(
					"Cross sold limit exceeded for customer `{}` by {}. Get it increased or place indent for other customer"
						.format(customer, abs(diff))
				)

		if errors:
			errors.insert(0, 'Did not save')
			frappe.throw('\n'.join(errors))

	def validate_customer(self):
		errors = []
		customer_list = ', '.join(['"{}"'.format(i.customer) for i in self.indent])

		disabled_customers = [x.name for x in frappe.db.sql("""
		select name from `tabCustomer`
		where name in ({})
		and (enabled = 0 or purchase_enabled = 0)
		""".format(customer_list), as_dict=True)]

		for x in disabled_customers:
			errors.append("Customer Purchase Disabled. {}".format(x))

		if errors:
			frappe.throw('\n'.join(errors))

	def validate_registration_and_customer_plant_variables(self):
		errors = []

		all_customer_set = set([i.customer for i in self.indent])
		omc = self.plant.split(" ")[0].lower()

		for customer in all_customer_set:
			omc_registration = get_applicable_omc_registration(omc, customer, self.posting_date)

			if not omc_registration:
				errors.append("{}'s Registration is missing.".format(customer))
			else:
				if omc_registration.docstatus == 0:
					errors.append("{}'s Registration is pending for approval.".format(customer))
				if cint(omc_registration.enabled) == 0:
					errors.append("{}'s Registration is disabled.".format(customer))

			cpv = get_applicable_customer_plant_variable(self.plant, customer, self.posting_date)

			if not cpv:
				errors.append("{}'s Plant Variables are missing.".format(customer))
			else:
				if cint(cpv.enabled) == 0:
					errors.append("{}'s Plant Variables are disabled.".format(customer))

		if errors:
			errors.insert(0, 'Did not save')
			frappe.throw('\n'.join(errors))



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
		AND voucher_type = "ERV"
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


def get_allowed_vehicle(vehicle, indent=''):
	superset_of_vehicles = set([x[0] for x in frappe.db.sql("""
		select name from `tabTransportation Vehicle`
		where name = '{}';
		""".format(vehicle))])

	from flows.flows.report.purchase_cycle_report.purchase_cycle_report import get_data

	vehicles_with_state = get_data(frappe._dict())

	bad_vehicles_set = set([x.indent.vehicle for x in vehicles_with_state if
							(x.bill_state == 'Pending' and x.indent.name != indent)
							])

	rs = list(superset_of_vehicles - bad_vehicles_set)
	rs.append('Self')
	return rs


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

def get_lease_date(plant):
	if 'iocl' in plant.lower():
		return 60
	elif 'hpcl' in plant.lower():
		return 120
	# BPCL lease of 90 days from fy 2017
	elif 'bpcl' in plant.lower():
		return 425

def validate_c_form(customer, plant, billing_date):
	c_form_name = frappe.db.sql("""
	SELECT name FROM `tabC Form Indent Invoice`
	WHERE customer="{customer}"
	AND SUBSTRING_INDEX(`supplier`, ' ', 1)="{supplier}"
	AND docstatus = 0
	""".format(
		customer=customer,
		supplier=plant.split(' ')[0]
	))

	if c_form_name:
		c_form = frappe.get_doc("C Form Indent Invoice", c_form_name[0][0])
		c_form.load_quarter_start_end()
		days = get_lease_date(plant)

		warn_date = add_days(c_form.end_date, days - 15)

		stop_date = add_days(c_form.end_date, days + 1)

		if billing_date > stop_date:
			frappe.throw(
				"""
				Refused to save indent. \nCustomer {customer}'s c form is pending supply wont be released by {plant}!\n
				If we have received C Form, upladte it before placing indent.""".format(
					customer=customer, plant=plant
				)
			)
		elif billing_date == stop_date:
			frappe.throw(
				"""
				Last day for lifting supply. Ensure that load get through.
				Customer {customer}'s c form is pending supply wont be released by {plant} a day after!""".format(
					customer=customer, plant=plant
				)
			)
		elif billing_date > warn_date:
			frappe.msgprint(
				"""Customer {customer}'s c form is pending and its supply will be blocked by {plant} in less that 15
				days!""".format(
					customer=customer, plant=plant
				)
			)


@frappe.whitelist()
def fetch_account_balance_with_omc(plant, customer, credit_account):
	if 'hpcl' in plant.lower():
		user, passed = get_portal_user_password(customer, 'HPCL', credit_account)
		return {'status': 'OK', 'balance': HPCLCustomerPortal(user, '').get_current_balance_as_on_date()}
	elif 'iocl' in plant.lower():
		user, passwd = get_portal_user_password(customer, 'IOCL', credit_account)
		if not (passwd and passwd.strip() != ""):
			frappe.throw("Can not query balance for customer {}. Password not found!".format(customer))
		portal = IOCLPortal(user, passwd)
		portal.login()
		return {'status': 'OK', 'balance': portal.get_current_balance_as_on_date('C002')['balance']}

	return {'status': 'Not Implemented', 'balance': 0}


def get_applicable_omc_registration(omc, customer, date):
	reg = frappe.db.sql(
		"""
		select * from `tabOMC Customer Registration`
		where customer = "{}"
		and omc= "{}"
		and with_effect_from <= "{}"
		and docstatus != 2
		order by with_effect_from desc
		limit 1
		""".format(customer, omc, date), as_dict=True
	)

	if reg:
		return reg[0]

def get_applicable_customer_plant_variable(plant, customer, date):
	cpv = frappe.db.sql(
		"""
		select * from `tabCustomer Plant Variables`
		where customer = "{}"
		and plant= "{}"
		and with_effect_from <= "{}"
		and docstatus != 2
		order by with_effect_from desc
		limit 1
		""".format(customer, plant, date), as_dict=True
	)

	if cpv:
		return cpv[0]

def get_omc_so(customer, plant, item, date=None):
	"""
	:param customer:
	:param plant:
	:param item:
	:return:
	"""

	so_list = frappe.db.sql(
		"""
		select so.so_number, so.customer, so.plant, so.valid_from,
        so.valid_upto, c.item, c.qty
		from `tabOMC Sales Order` so left join `tabOMC Sales Order Table` c
		on c.parent=so.name
		where so.customer = "{}" AND
              so.plant = "{}" AND
              c.item = "{}"
        order by so.valid_upto DESC
        limit 1
		""".format(customer, plant, item),
		as_dict=True
	)

	if date and so_list:
		if so_list[0].valid_upto < date:
			# SO Expired, reject
			so_list = None

	return so_list[0] if so_list else None