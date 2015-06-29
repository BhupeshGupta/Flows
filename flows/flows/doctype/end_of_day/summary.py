from __future__ import unicode_literals

from collections import OrderedDict

import frappe


def get_data(date, warehouse):
	filters = frappe._dict({'date': date, 'warehouse': warehouse})

	voucher_map = {
	'Goods Receipt': [],
	'erv': [],
	'Gatepass': [],
	'Payment Receipt': []
	}

	sle_list_map = get_sl_entries(filters)

	for sle in sle_list_map:
		if sle.voucher_type == 'Goods Receipt':
			voucher_map['Goods Receipt'].append(sle)
		elif sle.voucher_type == 'Payment Receipt':
			voucher_map['Payment Receipt'].append(sle)
		elif sle.voucher_type == 'Gatepass':
			doc = frappe.get_doc(sle.voucher_type, sle.voucher_no)
			if doc.voucher_type == 'ERV':
				voucher_map['erv'].append(sle)
			else:
				voucher_map['Gatepass'].append(sle)

	gr_map = compute_grs(voucher_map, filters)
	erv_in_map, erv_out_map = compute_erv(voucher_map, filters)
	gatepass_in_map, gatepass_out_map = compute_gatepass(voucher_map, filters)
	pr_map = compute_pr(voucher_map, filters)


	result_map = frappe._dict({
	'gr_map': gr_map,
	'erv_in_map': erv_in_map,
	'erv_out_map': erv_out_map,
	'gatepass_in_map': gatepass_in_map,
	'gatepass_out_map': gatepass_out_map,
	'pr_map': pr_map,
	'sle_list': sle_list_map,
	})

	return result_map


def get_sl_entries(filters):
	filtered_sl_entries = []

	warehouse_list, warehouse_list_srt = get_warehouse_list(filters.warehouse)

	sl_enteries = frappe.db.sql("""
	SELECT voucher_type, voucher_no,
	CASE WHEN warehouse IN ({warehouse_list_srt}) THEN '{warehouse}' ELSE warehouse END AS ware_house,
	item_code,
	CASE WHEN voucher_type='Payment Receipt' THEN sum(actual_qty) ELSE -1 * sum(actual_qty) END AS actual_qty
	FROM `tabStock Ledger Entry`
	WHERE voucher_no IN (
		SELECT DISTINCT(voucher_no)
		FROM `tabStock Ledger Entry`
		WHERE posting_date = "{date}"
		AND warehouse IN ({warehouse_list_srt})
	)
	AND ifnull(process, '') IN ('', 'Refill', 'New Connection', 'TV Out')
	GROUP BY voucher_type, voucher_no, ware_house, item_code
	HAVING ((voucher_type='Payment Receipt') OR ware_house != '{warehouse}')
	AND actual_qty != 0;
	""".format(warehouse_list_srt=warehouse_list_srt, **filters), as_dict=True)

	for sle in sl_enteries:
		sle.warehouse = sle.ware_house

	filtered_sl_entries.extend(sl_enteries)

	return filtered_sl_entries


def compute_grs(voucher_map, filters):
	def get_gr_item_map():
		return frappe._dict({
		'item_delivered': '',
		'delivered_quantity': 0,
		'item_received': '',
		'received_quantity': 0,
		'voucher': ''
		})

	gr_map = {}

	for gr_sle in voucher_map['Goods Receipt']:
		gr_map.setdefault(gr_sle.voucher_no, get_gr_item_map())
		gr_dict = gr_map[gr_sle.voucher_no]

		if gr_sle.actual_qty < 0:
			gr_dict.item_delivered = gr_sle.item_code
			gr_dict.delivered_quantity = int(abs(gr_sle.actual_qty))
		elif gr_sle.actual_qty > 0:
			gr_dict.item_received = gr_sle.item_code
			gr_dict.received_quantity = int(abs(gr_sle.actual_qty))

		if not gr_dict.voucher:
			gr_dict.voucher = frappe.get_doc(gr_sle.voucher_type, gr_sle.voucher_no)

	gr_map = OrderedDict(
		sorted(gr_map.items(), key=lambda x: (x[1]['item_delivered'] + x[1]['item_received']))
	)

	return gr_map


def compute_erv(voucher_map, filters):
	def erp_map_item():
		return frappe._dict({'voucher': '', 'warehouse': ''})

	erv_in_map = {}
	erv_out_map = {}
	for erv_voucher in voucher_map['erv']:
		active_map = erv_in_map if erv_voucher.actual_qty > 0 else erv_out_map
		active_map.setdefault(erv_voucher.voucher_no, erp_map_item())
		active_map[erv_voucher.voucher_no][erv_voucher.item_code] = int(abs(erv_voucher.actual_qty))
		active_map[erv_voucher.voucher_no]['warehouse'] = erv_voucher.warehouse

		if not active_map[erv_voucher.voucher_no]['voucher']:
			active_map[erv_voucher.voucher_no]['voucher'] = \
				frappe.get_doc(erv_voucher.voucher_type, erv_voucher.voucher_no)

	return erv_in_map, erv_out_map


def compute_gatepass(voucher_map, filters):
	def gatepass_map_item():
		return frappe._dict({
		'voucher': '',
		'warehouse': ''
		})

	gatepass_in_map = {}
	gatepass_out_map = {}
	for gatepass_voucher in voucher_map['Gatepass']:
		active_map = gatepass_in_map if gatepass_voucher.actual_qty > 0 else gatepass_out_map
		active_map.setdefault(gatepass_voucher.voucher_no, gatepass_map_item())
		active_map[gatepass_voucher.voucher_no][gatepass_voucher.item_code] = int(abs(gatepass_voucher.actual_qty))
		active_map[gatepass_voucher.voucher_no]['warehouse'] = gatepass_voucher.warehouse

		if not active_map[gatepass_voucher.voucher_no]['voucher']:
			active_map[gatepass_voucher.voucher_no]['voucher'] = \
				frappe.get_doc(gatepass_voucher.voucher_type, gatepass_voucher.voucher_no)

	return gatepass_in_map, gatepass_out_map


def compute_pr(voucher_map, filters):
	def pr_map_item():
		return frappe._dict({
		'r_qty': 0,
		'd_qty': 0,
		'item': '',
		'voucher': ''
		})

	pr_map = {}
	for pr_voucher in voucher_map['Payment Receipt']:
		pr = frappe.get_doc(pr_voucher.voucher_type, pr_voucher.voucher_no)
		pr_map.setdefault(pr.name, pr_map_item())

		if pr_voucher.actual_qty < 0:
			pr_map[pr.name]['d_qty'] = int(abs(pr_voucher.actual_qty))
		else:
			pr_map[pr.name]['r_qty'] = int(abs(pr_voucher.actual_qty))

		pr_map[pr.name]['item'] = pr.item
		pr_map[pr.name]['voucher'] = pr

	return pr_map


def get_warehouse_list(warehouse):
	warehouse = frappe.db.sql("SELECT lft, rgt FROM `tabWarehouse` WHERE name = '{}';"
								  .format(warehouse), as_dict=True)[0]
	warehouse_list = [
		x[0] for x in frappe.db.sql(
			"SELECT name FROM `tabWarehouse` WHERE lft >= '{}' AND rgt <= '{}';".format(warehouse.lft, warehouse.rgt)
		)
	]
	warehouse_list_srt = '"{}"'.format('","'.join(warehouse_list))

	return warehouse_list, warehouse_list_srt