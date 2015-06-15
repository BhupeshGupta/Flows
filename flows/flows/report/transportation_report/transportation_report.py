# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data


def get_columns():
	return [
		"Date:Date:95", "Gatepass:Link/Gatepass:95", "Vehicle:Link/Transportation Vehicle:130", "Route::200",
		"Number Of Bills:Int:50", "Route Cost:Currency:100", "Advance:Currency:100", "Fuel Qty:Float:100",
		"Fuel Rate:Currency:100", "Fuel Amount:Currency:100", "Amount To Be Paid:Currency:150"
	]


def get_data(filters):
	gatepasses = get_gatepasses(filters)

	gatepasses_map = initialize_gatepasses_map(gatepasses)
	populate_gatepasses_map(gatepasses_map, gatepasses)

	route_cost = advance = fuel_qty = fuel_cost = amount_to_be_paid = no_of_bills = 0

	rows = []
	for vehicle, vehicle_map in gatepasses_map.items():
		for e in vehicle_map.gatepasses:
			rows.append([
				e.date, e.name, e.vehicle, e.route_name,
				e.no_of_bills, e.route_cost, e.advance,
				e.fuel_qty, e.fuel_rate, e.fuel_cost,
				e.amount_to_be_paid
			])
		rows.append(['', '', e.vehicle, 'Total', vehicle_map.no_of_bills,
		             vehicle_map.route_cost, vehicle_map.advance, vehicle_map.fuel_qty,
		             '',
		             vehicle_map.fuel_cost, vehicle_map.amount_to_be_paid])
		rows.append([])

		route_cost += vehicle_map.route_cost
		advance += vehicle_map.advance
		fuel_qty += vehicle_map.fuel_qty
		fuel_cost += vehicle_map.fuel_cost
		amount_to_be_paid += vehicle_map.amount_to_be_paid
		no_of_bills += vehicle_map.no_of_bills

	rows.append([])

	rows.append(['', '', '', 'Grand Total', no_of_bills,
	             route_cost, advance, fuel_qty,
	             '',
	             fuel_cost, amount_to_be_paid])

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
			select * from `tabRoute Cost` where
			route = '{route}' and
			with_effect_from <= '{date}' and
			vehicle_type='{vehicle_type}' order by with_effect_from desc limit 1;
		""".format(**context),
		as_dict=True
	)

	if not cost:
		frappe.msgprint(
			"""Unable to find transportation cost for vehicle type {vehicle_type},
			for route {route} in {date} date, assuming zero(0)""".format(**context)
		)

	return cost[0].route_cost if cost else 0


def get_route_name(route):
	return route


def initialize_gatepasses_map(gatepasses):
	gatepasses_map = frappe._dict()
	for gatepass in gatepasses:
		gatepasses_map.setdefault(gatepass.vehicle, frappe._dict({
			"gatepasses": [],
			"route_cost": 0,
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
	and posting_date between "{from_date}" and "{to_date}"
	{cond}
	order by posting_date asc;
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
	entry = frappe._dict({
		"date": gatepass.posting_date,
		"name": gatepass.name,
		"vehicle": get_vehicle(gatepass.vehicle).name,
		"route_name": get_route_name(gatepass.route),
		"route_cost": get_route_cost(gatepass.posting_date, gatepass.route, gatepass.vehicle),
		"advance": gatepass.advance if gatepass.advance else 0,
		"fuel_qty": gatepass.fuel_quantity if gatepass.fuel_quantity else 0,
		"no_of_bills": frappe.db.sql("""
		select count(name) from `tabIndent Item` where parent = "{}"
		""".format(gatepass.indent))[0][0]
	})
	entry["fuel_rate"], entry["fuel_cost"] = get_fuel_cost(gatepass.posting_date, gatepass.fuel_quantity)
	entry.amount_to_be_paid = entry["route_cost"] - entry["advance"] - entry["fuel_cost"]
	return entry


def populate_gatepasses_map(gatepasses_map, gatepasses):
	for gatepass in gatepasses:
		gatepass_entry = get_gatepass_entry(gatepass)
		gatepasses_map[gatepass.vehicle].gatepasses.append(gatepass_entry)

		route_cost = gatepass_entry["route_cost"]
		fuel_quantity = gatepass_entry["fuel_qty"]
		fuel_cost = gatepass_entry["fuel_cost"]
		advance = gatepass_entry["advance"]
		amount_to_be_paid = gatepass_entry["amount_to_be_paid"]

		gatepasses_map[gatepass.vehicle].route_cost += route_cost
		gatepasses_map[gatepass.vehicle].fuel_qty += fuel_quantity
		gatepasses_map[gatepass.vehicle].fuel_cost += fuel_cost
		gatepasses_map[gatepass.vehicle].advance += advance
		gatepasses_map[gatepass.vehicle].amount_to_be_paid += amount_to_be_paid
		gatepasses_map[gatepass.vehicle].no_of_bills += gatepass_entry.no_of_bills

	return gatepasses_map
