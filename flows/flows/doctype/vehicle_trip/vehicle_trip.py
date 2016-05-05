# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from flows.stdlogger import root

class VehicleTrip(Document):
	def validate(self):
		name = frappe.db.sql(
			"""
			select name from `tabVehicle Trip`
			where vehicle = "{vehicle}"
			and ifnull(in_gatepass, '') = ''
			and name != "{name}"
			""".format(**self.as_dict())
		)

		if not name:
			return

		name = name[0][0]

		frappe.throw("""
		Trip {} is already open against vehicle {}
		""".format(name, self.vehicle))

@frappe.whitelist()
def get_trip_page(from_date=None, to_date=None, name=None):
	def get_conditions():
		cond = []
		if name:
			cond.append('name = "{}"'.format(name))
		if from_date and to_date:
			cond.append('date between "{}" and "{}"'.format(from_date, to_date))
		if not cond:
			cond.append('1=1')
		return ' and '.join(cond)

	rs = frappe._dict({'open': [], 'closed': [], 'notifications': []})

	rs.notifications = frappe.db.sql("""
	select * from `tabVehicle Trip`
	where date < "{from_date}" and
	ifnull(in_gatepass, '') = ''
	order by date asc
	""".format(from_date=from_date), as_dict=True)

	for trip in frappe.db.sql("""
	select * from `tabVehicle Trip`
	where {}
	order by creation desc
	""".format(get_conditions()), as_dict=True):

		trip.outGatepass = frappe.get_doc("Gatepass", trip.out_gatepass)

		if trip.in_gatepass:
			trip.inGatepass = frappe.get_doc("Gatepass", trip.in_gatepass)
			rs.closed.append(trip)
		else:
			rs.open.append(trip)

		trip.transactions = frappe.db.sql("""
		select * from `tabGoods Receipt`
		where trip_id = "{name}"
		and docstatus = 1
		""".format(name=trip.name), as_dict=True)

	return rs


@frappe.whitelist()
def create_trip(gatepass):
	gatepass = frappe._dict(json.loads(gatepass))

	gatepass.update({
		'doctype': 'Gatepass',
		'gatepass_type': 'Out'
	})
	gatepass = frappe.get_doc(gatepass)
	gatepass.save()

	trip = frappe.get_doc({
	"doctype": "Vehicle Trip",
	"vehicle": gatepass.vehicle,
	"date": gatepass.posting_date,
	"out_gatepass": gatepass.name
	})

	trip.save()

	return get_trip_page(name=trip.name)


@frappe.whitelist()
def create_trip_return(gatepass):
	gatepass = frappe._dict(json.loads(gatepass))
	gatepass.update({
		'doctype': 'Gatepass',
		'gatepass_type': 'In'
	})

	trip = frappe.get_doc("Vehicle Trip", gatepass.trip_id)

	gatepass = frappe.get_doc(gatepass)
	gatepass.id = trip.out_gatepass.split('-Out')[0]
	gatepass.save()

	trip.in_gatepass = gatepass.name
	trip.save()

	return get_trip_page(name=trip.name)