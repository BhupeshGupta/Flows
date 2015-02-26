# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data


def get_columns():
	return [
		"Date:Date:95", "Slip No::100", "Vehicle:Link/Transportation Vehicle:130",
		"Fuel Qty:Float:100", "Fuel Rate:Float:100", "Amount To Be Paid:Float:150",
		# "Reserved Space::100", "Reserved Space::100", "Reserved Space::100",
	]


def get_data(filters):
	gatepasses = get_gatepasses(filters)
	vehicle_map = init_vehicle_map(gatepasses, filters)
	rows = flatten_to_rows(vehicle_map, filters)
	# rows = add_budget_analytics(rows, vehicle_map)
	return rows


def get_gatepasses(filters=None):
	return frappe.db.sql("""
    SELECT *
    FROM `tabGatepass`
    WHERE
    fuel_pump IS NOT Null AND
    fuel_pump != ''
    ORDER BY posting_date ASC;
    """, as_dict=True)


def init_vehicle_map(gatepasses, filters):
	vehicle_map = frappe._dict()
	for gatepass in gatepasses:
		vehicle_map.setdefault(gatepass.vehicle, frappe._dict({
			'gatepasses': [],
			'total_qty': 0.0,
			'total_amount': 0.0
		}))

		entry = get_gatepass_entry(gatepass)
		vehicle_map[gatepass.vehicle].gatepasses.append(entry)

		vehicle_map[gatepass.vehicle].total_qty += entry.qty
		vehicle_map[gatepass.vehicle].total_amount += entry.amount

	return vehicle_map


def get_gatepass_entry(gatepass):
	e = frappe._dict({
		'date': gatepass.posting_date,
		'slip_no': gatepass.fuel_slip_id,
		'qty': gatepass.fuel_quantity,
		'dest': gatepass.dispatch_destination,
	})
	e.rate, e.amount = get_fuel_cost(gatepass.posting_date, gatepass.fuel_quantity)
	return e


def flatten_to_rows(vehicle_map, filters):
	grand_total_qty = grand_total_amount = 0

	rows = []
	for vehicle, vehicle_map_item in vehicle_map.items():
		for item in vehicle_map_item.gatepasses:
			rows.append([item.date, item.slip_no, vehicle, item.qty, item.rate, item.amount])
		rows.extend([['', '', 'Total', vehicle_map_item.total_qty, '', vehicle_map_item.total_amount], []])

		grand_total_qty += vehicle_map_item.total_qty
		grand_total_amount += vehicle_map_item.total_amount

	rows.extend([[], ['', '', 'Grand Total', grand_total_qty, '', grand_total_amount]])

	return rows


def add_budget_analytics(rows, vehicle_map):
	budget_map = frappe._dict()

	for vehicle, vehicle_map_item in vehicle_map.items():

		vehicle_object = get_vehicle(vehicle)
		budget_map.setdefault(vehicle_object.vehicle_owner_company, frappe._dict())

		for gatepass in vehicle_map_item.gatepasses:
			budget_map[vehicle_object.vehicle_owner_company].setdefault(gatepass.dest, 0.0)
			budget_map[vehicle_object.vehicle_owner_company][gatepass.dest] += gatepass.amount

	rows.extend([
		[],
		['', '', '', '', '', '', 'Amount Breakup']
	])
	for company in budget_map:
		for dest in budget_map[company]:
			rows.append(
				[
					'', '', '', '', '', '',
					company,
					dest,
					budget_map[vehicle_object.vehicle_owner_company][gatepass.dest]
				]
			)

	return rows


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


def get_vehicle(vehicle):
	return frappe.get_doc("Transportation Vehicle", vehicle)