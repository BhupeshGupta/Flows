# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data


def get_columns():
	return [
		"Sr.::15", "GP Out Date:Date:95", "Gatepass:Link/Gatepass:95", "Vehicle:Link/Transportation Vehicle:130",
		"Route::200", "Number Of Bills:Int:50", "Basic Route Cost:Currency:100", "Fuel Route Cost:Currency:100",
		"Advance:Currency:100", "Fuel Qty:Float:100", "Fuel Rate:Currency:100", "Fuel Amount:Currency:100",
		"Amount To Be Paid:Currency:150", "Indent Date:Date:95", "Invoice Date:Date:95", "Material in M.T.:Float:"
	]


def get_data(filters):
	gatepasses = get_gatepasses(filters)

	gatepasses_map = initialize_gatepasses_map(gatepasses)
	populate_gatepasses_map(gatepasses_map, gatepasses)

	basic_route_cost = fuel_route_cost = advance = fuel_qty = fuel_cost = amount_to_be_paid = no_of_bills = 0

	rows = []
	for vehicle, vehicle_map in gatepasses_map.items():
		for i, e in enumerate(vehicle_map.gatepasses):
			rows.append([
				i + 1, e.date, e.name, e.vehicle,
				e.route_name, e.no_of_bills, e.basic_route_cost, e.fuel_route_cost,
				e.advance, e.fuel_qty, e.fuel_rate, e.fuel_cost,
				e.amount_to_be_paid, e.indent_date, e.invoice_date, e.qty_mt
			])
		rows.append([
			 '', '', '', e.vehicle, 'Total', vehicle_map.no_of_bills,
			 vehicle_map.basic_route_cost, vehicle_map.fuel_route_cost,
			 vehicle_map.advance, vehicle_map.fuel_qty, '',
			 vehicle_map.fuel_cost, vehicle_map.amount_to_be_paid
		])
		rows.append([])

		basic_route_cost += vehicle_map.basic_route_cost
		fuel_route_cost += vehicle_map.fuel_route_cost
		advance += vehicle_map.advance
		fuel_qty += vehicle_map.fuel_qty
		fuel_cost += vehicle_map.fuel_cost
		amount_to_be_paid += vehicle_map.amount_to_be_paid
		no_of_bills += vehicle_map.no_of_bills

	rows.append([])

	rows.append([
		 '', '', '', '', 'Grand Total', no_of_bills,
		 basic_route_cost, fuel_route_cost, advance, fuel_qty,
		 '', fuel_cost, amount_to_be_paid
	])

	return rows


def get_vehicle(vehicle):
	return frappe.get_doc("Transportation Vehicle", vehicle)


route_map = {}


def get_route(route):
	if not route in route_map:
		route_map[route] = frappe.get_doc("Transportation Route", route)
	return route_map[route]


def get_route_cost(date, route, vehicle):
	vehicle_object = get_vehicle(vehicle)

	context = {
		"route": route,
		"date": date,
		"vehicle_type": vehicle_object.vehicle_make
	}

	cost = frappe.db.sql(
		"""
			select * from `tabRoute Cost`
			where route = '{route}'
			and with_effect_from <= '{date}'
			and vehicle_type='{vehicle_type}'
			order by with_effect_from
			desc limit 1;
		""".format(**context),
		as_dict=True
	)

	if not cost:
		frappe.msgprint(
			"""Unable to find transportation cost for vehicle type {vehicle_type},
			for route {route} in {date} date, assuming zero(0)""".format(**context)
		)

	if not cost:
		return 0, 0

	cost_per_l, total_cost = get_fuel_cost(date, cost[0].fuel_qty)
	return cost[0].basic_cost, total_cost


def get_route_name(route):
	return route


def initialize_gatepasses_map(gatepasses):
	gatepasses_map = frappe._dict()
	for gatepass in gatepasses:
		gatepasses_map.setdefault(gatepass.vehicle, frappe._dict({
			"gatepasses": [],
			"basic_route_cost": 0,
			"fuel_route_cost": 0,
			"advance": 0,
			"fuel_qty": 0,
			"fuel_rate": 0,
			"fuel_cost": 0,
			"amount_to_be_paid": 0,
			"no_of_bills": 0
		}))
	return gatepasses_map


def get_gatepasses(filters):
	cond = ''
	if filters.supplier:
		cond = """
		and vehicle in (
			select name from `tabTransportation Vehicle`
			where vehicle_owner_company = "{supplier}"
		)""".format(**filters)


	return frappe.db.sql(
		"""
	select * from tabGatepass
	where docstatus = 1
	and voucher_type='ERV' and
	gatepass_type='Out'
	and transaction_date between "{from_date}" and "{to_date}"
	{cond}
	order by transaction_date asc;
	""".format(cond=cond, **filters),
		as_dict=True
	)


def get_fuel_cost(date, fuel_qty):
	if not fuel_qty:
		return 0, 0

	context = {
		"date": date,
	}

	cost = frappe.db.sql(
		"""
			select * from `tabFuel Cost` where
			with_effect_from <= '{date}'
			order by with_effect_from desc limit 1;
		""".format(**context),
		as_dict=True
	)

	if not cost:
		frappe.msgprint(
			"""Unable to find fuel cost for {date} date, assuming zero(0)""".format(**context)
		)

	cost_per_liter = cost[0].price_per_liter if cost else 0

	return cost_per_liter, cost_per_liter * fuel_qty


def get_gatepass_entry(gatepass):
	basic_route_cost, fuel_route_cost = get_route_cost(gatepass.transaction_date, gatepass.route, gatepass.vehicle)

	if not gatepass.indent:
		frappe.msgprint("Indent not found with gatepass {}".format(gatepass.name))

	entry = {
		"date": gatepass.transaction_date,
		"name": gatepass.name,
		"vehicle": get_vehicle(gatepass.vehicle).name,
		"route_name": get_route_name(gatepass.route),
		"basic_route_cost": basic_route_cost,
		"fuel_route_cost": fuel_route_cost,
		"advance": gatepass.advance if gatepass.advance else 0,
		"fuel_qty": gatepass.fuel_quantity if gatepass.fuel_quantity else 0,
		"no_of_bills": frappe.db.sql("""
		select count(name) from `tabIndent Item` where parent = "{}"
		""".format(gatepass.indent))[0][0],
		"indent_date": frappe.db.get_value("Indent", filters=gatepass.indent, fieldname="posting_date"),
		"invoice_date": frappe.db.get_value("Indent Invoice", filters={'indent': gatepass.indent}, fieldname="transaction_date"),
	}

	try:
		entry["qty_mt"] = frappe.db.sql(
			"""
			select sum(replace(replace(item, 'FC', ''), 'L', '') * qty) from `tabIndent Item`
			where parent = "{}"
			""".format(gatepass.indent)
		)[0][0] / 1000 if gatepass.indent else 0
	except:
		entry["qty_mt"] = 0
		frappe.msgprint("Error while accessing indent for gatepass {}".format(gatepass.name))

	entry = frappe._dict(entry)

	entry["fuel_rate"], entry["fuel_cost"] = get_fuel_cost(gatepass.transaction_date, gatepass.fuel_quantity)
	entry.amount_to_be_paid = entry["basic_route_cost"] + entry["fuel_route_cost"] - entry["advance"] - entry["fuel_cost"]
	return entry


def populate_gatepasses_map(gatepasses_map, gatepasses):
	for gatepass in gatepasses:
		gatepass_entry = get_gatepass_entry(gatepass)
		gatepasses_map[gatepass.vehicle].gatepasses.append(gatepass_entry)

		basic_route_cost = gatepass_entry["basic_route_cost"]
		fuel_route_cost = gatepass_entry["fuel_route_cost"]
		fuel_quantity = gatepass_entry["fuel_qty"]
		fuel_cost = gatepass_entry["fuel_cost"]
		advance = gatepass_entry["advance"]
		amount_to_be_paid = gatepass_entry["amount_to_be_paid"]

		gatepasses_map[gatepass.vehicle].basic_route_cost += basic_route_cost
		gatepasses_map[gatepass.vehicle].fuel_route_cost += fuel_route_cost
		gatepasses_map[gatepass.vehicle].fuel_qty += fuel_quantity
		gatepasses_map[gatepass.vehicle].fuel_cost += fuel_cost
		gatepasses_map[gatepass.vehicle].advance += advance
		gatepasses_map[gatepass.vehicle].amount_to_be_paid += amount_to_be_paid
		gatepasses_map[gatepass.vehicle].no_of_bills += gatepass_entry.no_of_bills

	return gatepasses_map
