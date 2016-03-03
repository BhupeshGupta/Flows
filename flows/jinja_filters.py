from collections import OrderedDict

import frappe
from frappe.utils import cint


def indent_refill_qty(indent_items):
	sum = 0
	for indent_item in indent_items:
		if indent_item.load_type == "Refill":
			sum += float(indent_item.item.replace('FC', '').replace('L', '')) * indent_item.qty

	return sum/1000


def indent_oneway_qty(indent_items):
	sum = 0
	for indent_item in indent_items:
		if indent_item.load_type == "Oneway":
			sum += float(indent_item.item.replace('FC', '').replace('L', '')) * indent_item.qty

	return sum/1000


def compute_erv_for_refill_in_indent(indent_items):
	item_desc_map = {}
	def get_desc(item):
		if item not in item_desc_map:
			item_desc_map[item] = frappe.db.get_value("Item", indent_item.item, "description")
		return item_desc_map[item]

	map = {}
	for indent_item in indent_items:
		# if indent_item.load_type == "Refill":
			key = get_desc(indent_item.item).replace("FC", "")
			key = key.replace('LOT', 'Kg LOT').replace('VOT', 'Kg VOT') if 'OT' in key else key + ' Kg'
			key += ' ({})'.format(indent_item.load_type)
			map.setdefault(key, 0)
			map[key] += indent_item.qty

	safety_caps = 0
	for item, values in map.items():
		if 'Refill' in item:
			safety_caps += values
	if safety_caps > 0:
		map["Saf Cap."] = safety_caps

	return OrderedDict(sorted(map.items()))


def get_contract_number(customer, date, plant):
	rs = frappe.db.sql("""
	SELECT contract_number
	FROM `tabCustomer Plant Variables`
	WHERE customer = "{}"
	AND with_effect_from < "{}"
	AND plant = "{}"
	AND docstatus != 2
	ORDER BY with_effect_from DESC limit 1;
	""".format(customer, date, plant))

	return rs[0][0] if rs else ""


def get_registration_code(customer, vendor, date):
	"""
	customer: customer to get code for
	vendor: vendor to get registration code for (HPCL, BPLC, IOCL)
	"""

	vendor = vendor.lower()

	if vendor in ["hpc", "bpc", "ioc"]:
		key = vendor + 'l'
	else:
		frappe.throw("Invalid vendor")

	val = frappe.db.sql("""
	Select customer_code from
	`tabOMC Customer Registration`
	where customer = "{customer}"
	and omc = "{omc}"
	and docstatus !=2
	and with_effect_from <= "{date}"
	order by with_effect_from desc limit 1
	""".format(customer=customer, omc=key, date=date))

	if not val:
		frappe.throw("Customer {} not registred with OMC {}".format(customer, key))

	return val[0][0]


def get_customer_tin_number(customer):
	"""
	customer: customer to get code for
	vendor: vendor to get registration code for (HPCL, BPLC, IOCL)
	"""
	return get_customer_field(customer, "tin_number")


def get_customer_field(customer_name, field):
	rs = frappe.db.sql("""
    SELECT {}
    FROM `tabCustomer`
    WHERE name = "{}"
    """.format(field, customer_name)
	)

	return rs[0][0] if rs else ""


def get_cenvat_status(customer_name, date, plant):
	rs = frappe.db.sql("""
    SELECT cenvat
    FROM `tabCustomer`
    WHERE name = "{customer}"
    """.format(customer=customer_name))

	return "MODVAT" if cint(rs[0][0]) == 1 else "NONMODVAT"


def get_address_display(address_of, address_type):
	from erpnext.utilities.doctype.address.address import get_address_display as gda

	return gda("{}-{}".format(address_of.strip(), address_type))


def report_build_erv_item_map(erv_map):
	rs = set()
	for erv_map in erv_map.values():
		for items in erv_map.keys():
			rs.add(items)

	rs_list = []

	if 'FC19' in rs:
		rs_list.append('FC19')
	if 'FC35' in rs:
		rs_list.append('FC35')
	if 'FC47.5' in rs:
		rs_list.append('FC47.5')
	if 'FC47.5L' in rs:
		rs_list.append('FC47.5L')
	if 'EC19' in rs:
		rs_list.append('EC19')
	if 'EC35' in rs:
		rs_list.append('EC35')
	if 'EC47.5' in rs:
		rs_list.append('EC47.5')
	if 'EC47.5L' in rs:
		rs_list.append('EC47.5L')

	return rs_list


def get_item_qty_aggr_gatepass(data, item):
	result = 0
	for row in data:
		if row.item == item:
			result += row.quantity
	return result
