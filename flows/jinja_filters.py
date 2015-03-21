from collections import OrderedDict

import frappe


def indent_refill_qty(indent_items):
	sum = 0
	for indent_item in indent_items:
		if indent_item.load_type == 'Refill':
			sum += indent_item.qty

	return sum


def indent_oneway_qty(indent_items):
	sum = 0
	for indent_item in indent_items:
		if indent_item.load_type == 'Oneway':
			sum += indent_item.qty

	return sum


def compute_erv_for_refill_in_indent(indent_items):
	map = {}
	for indent_item in indent_items:
		if indent_item.load_type == 'Refill':
			key = indent_item.item.replace('FC', '') + ' Kg'
			map.setdefault(key, 0)
			map[key] += indent_item.qty

	safety_caps = 0
	for values in map.values():
		safety_caps += values
	if safety_caps > 0:
		map['Safety Caps'] = safety_caps

	return OrderedDict(sorted(map.items()))


def get_contract_number(customer, date, plant):
	rs = frappe.db.sql("""
    SELECT contract_number
    FROM `tabCustomer Plant Variables`
    WHERE customer = '{}'
    AND with_effect_from < '{}'
    AND plant = '{}'
    ORDER BY with_effect_from DESC limit 1;
    """.format(customer, date, plant))

	return rs[0][0] if rs else ''


def get_registration_code(customer, vendor):
	"""
	customer: customer to get code for
	vendor: vendor to get registration code for (HPCL, BPLC, IOCL)
	"""

	from stdlogger import root

	root.debug((customer, vendor))

	vendor = vendor.lower()

	if vendor == 'hpc':
		key = 'hpcl_erp_number'
	elif vendor == 'bpc':
		key = 'bpcl_sap_code'
	elif vendor == 'ioc':
		key = 'iocl_sap_code'

	val = get_customer_field(customer, key)
	return val if val else ''


def get_customer_tin_number(customer):
	"""
	customer: customer to get code for
	vendor: vendor to get registration code for (HPCL, BPLC, IOCL)
	"""
	return get_customer_field(customer, 'tin_number')


def get_customer_field(customer_name, field):
	rs = frappe.db.sql("""
    SELECT {}
    FROM `tabCustomer`
    WHERE name = "{}"
    """.format(field, customer_name)
	)

	return rs[0][0] if rs else ''


def get_cenvat_status(customer_name, date, plant):
	rs = frappe.db.sql("""
    SELECT {key}
    FROM `tabCustomer Plant Variables`
    WHERE customer = '{customer}'
    AND with_effect_from < '{date}'
    AND plant = '{plant}'
    ORDER BY with_effect_from DESC limit 1;
    """.format(key='cenvat', customer=customer_name, date=date, plant=plant)
	)

	if not rs:
		return ''

	return 'MODVAT' if rs[0][0] == 1 else 'NONMODVAT'


def get_address_display(address_of, address_type):
	from erpnext.utilities.doctype.address.address import get_address_display as gda

	return gda('{}-{}'.format(address_of.strip(), address_type))