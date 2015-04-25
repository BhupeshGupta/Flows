from __future__ import unicode_literals

from __future__ import unicode_literals

import frappe
import frappe.defaults

from frappe.utils import get_first_day

def execute():
	for (invoice_id, transportation_invoice_id) in frappe.db.sql("""
		SELECT name, transportation_invoice
		FROM `tabIndent Invoice`
		WHERE docstatus = 1;
		"""):

		if transportation_invoice_id and transportation_invoice_id != '':
			doc = frappe.get_doc("Sales Invoice", transportation_invoice_id)
			landed_rate, transportation_rate = get_landed_rate_for_customer(doc.customer, doc.posting_date)

			frappe.db.sql("""
			UPDATE `tabIndent Invoice` SET transportation_invoice_rate='{}', transportation_invoice_amount='{}',
			applicable_transportation_invoice_rate = '{}'
			WHERE name = '{}'""".format(transportation_rate, doc.grand_total_export, doc.entries[0].rate, invoice_id)
			)



def get_landed_rate_for_customer(customer, date):
	month_start = get_first_day(date).strftime('%Y-%m-%d')

	rs = frappe.db.sql("""
    SELECT landed_rate, local_transport_rate
    FROM `tabCustomer Landed Rate`
    WHERE customer="{customer}" AND
    with_effect_from<="{date}"
    ORDER BY with_effect_from DESC LIMIT 1;
    """.format(customer=customer, date=date, month_start_date=month_start))
	if rs:
		return rs[0]
	frappe.throw('Landed Rate Not Found For Customer {} for date {}'.format(customer, date))