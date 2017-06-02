import json

import frappe

@frappe.whitelist(allow_guest=True)
def get_customers(phone):
	customer_list = frappe.db.get_values("Contact", filters={"phone": phone}, fieldname="customer", as_dict=True)

	for cust in customer_list:
		customer = cust.customer
		pan_number = frappe.db.get_values("Customer", filters={"name": customer}, fieldname="pan_number", as_dict=True)[0]
		if pan_number:
			cust.update(pan_number)

		address = frappe.db.get_values(
			"Address",
			filters={"customer": customer, 'is_primary_address': 1},
			fieldname=[
				'address_title',
				'address_line1',
				'address_line2',
				'city',
				'state',
				'pincode'
			],
			as_dict=True
		)

		cust.update(address[0] if address else {'address_not_found': True})

	return json.dumps(customer_list)
