# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe.model.document import Document

import frappe
from frappe.utils import today, now
from erpnext.accounts.utils import get_fiscal_year
from flows import utils
from frappe.model.naming import make_autoname


class Gatepass(Document):
	def autoname(self):
		if self.id and self.id != '':
			self.name = '{}-{}'.format(self.id, self.gatepass_type)
			return

		name_series = 'GP+.DD.MM.YY.###'
		self.name = make_autoname(name_series)
		self.name = self.name.replace('+', self.dispatch_destination[0].upper())
		self.name = '{}-{}'.format(self.name, self.gatepass_type)

	def on_submit(self):
		self.transfer_stock()

	def on_cancel(self):
		self.transfer_stock()

	def transfer_stock(self):

		self.set_missing_values()

		from flows import utils as flow_utils

		stock_owner = flow_utils.get_stock_owner_via_sales_person_tree(self.driver)
		stock_owner = stock_owner if stock_owner else self.vehicle

		stock_owner_act = utils.get_or_create_vehicle_stock_account(stock_owner, self.company)
		stock_owner_act_name = stock_owner_act.name

		sl_entries = []

		for d in self.items:
			sl_entries.append(
				self.get_sl_entry({
					"item_code": d.item,
					"actual_qty": -1 * d.quantity,
					"warehouse": self.warehouse if self.gatepass_type.lower() == 'out' else
					stock_owner_act_name
				})
			)

			sl_entries.append(
				self.get_sl_entry({
					"item_code": d.item,
					"actual_qty": 1 * d.quantity,
					"warehouse": self.warehouse if self.gatepass_type.lower() == 'in' else
					stock_owner_act_name
				})
			)

		from erpnext.stock.stock_ledger import make_sl_entries

		make_sl_entries(sl_entries)

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
		for fieldname in ["posting_date", "transaction_date"]:
			if not self.get(fieldname):
				self.set(fieldname, today())

		self.fiscal_year = get_fiscal_year(self.posting_date)[0]

		if not self.get("posting_time"):
			self.posting_time = now()


def get_indent_list(doctype, txt, searchfield, start, page_len, filters):
	indent = frappe.db.sql("""
	select indent from `tabGatepass`
	where name like '{doc_id}%' and
	vehicle = '{vehicle}'""".format(**filters))

	subquery = '"{}"'.format(indent[0][0]) if indent \
	else """
	SELECT name FROM `tabIndent`
	WHERE posting_date >= '2015-05-01'
	AND vehicle = '{vehicle}'
	AND name NOT IN (
		SELECT ifnull(indent, '')
		FROM `tabGatepass`
		WHERE gatepass_type = "{gatepass_type}"
		AND docstatus = 1
	)
	AND name like '%{txt}%'""".format(txt=txt, **filters)


	# posting_date >= '2015-05-01' // feature start date
	rs = frappe.db.sql("""
	SELECT ind.name as name,
	init.item as item,
	sum(init.qty) as qty,
	ind.plant as plant,
	ind.posting_date as posting_date
	FROM `tabIndent` ind, `tabIndent Item` init
	WHERE ind.name in (
		{subquery}
	)
	AND ind.name = init.parent
	GROUP BY ind.name, init.item;
	""".format(subquery=subquery, **filters), as_dict=True)

	rs_map = {}
	for r in rs:
		rs_map.setdefault(r.name, frappe._dict({}))
		rs_dict = rs_map[r.name]
		rs_dict.setdefault('items', [])

		rs_dict.plant = r.plant
		rs_dict.posting_date = frappe.utils.formatdate(r.posting_date)
		rs_dict['items'].append('{} X {}'.format(int(r.qty), r.item))

	result = []
	for key, rs_dict in rs_map.items():
		result.append([key, '{} {} [{}]'.format(rs_dict.posting_date, rs_dict.plant, ','.join(rs_dict['items']))])

	return result
