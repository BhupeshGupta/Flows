from frappe.utils.email_lib.email_body import get_email
import frappe
from frappe.utils.email_lib.smtp import send


def execute():
	for customer_docs in frappe.db.sql("""
	select  i.customer, group_concat(i.name)
	as docs from `tabSales Invoice` i
	where i.posting_date between '2016-03-01' and '2016-03-30'
	and customer_group not in ('pallav singla', 'BADDI', 'SANGRUR', 'HARIDIYA', 'NOIDA')
	and grand_total_export != 0
	and name like 'SCN%'
	group by i.customer;
	""", as_dict=True):

		mail = get_email(
			get_recipients(customer_docs.customer),
			sender='noreply@arungas.com',
			subject='Transportation invoices from 01.03.2016 to 30.03.2016 for Service tax, TDS Purpose: ' + customer_docs.customer,
			msg="""
We are submitting scanned copies of transportation invoices up to 30.03.2016 to calculate your service tax,
TDS (which has to be filled by today). Kindly incorporate the same.

The originals invoices will be submitted along-with products(LPG) bills further we will forward copies of
transportation invoices raised on 31.03.2016 by noon on 1st April 2016

Regards
Arun Logistics
Unit Of Arun Gas Service
			"""
		)
		mail.cc.append('arunlogistics1@gmail.com')
		mail.reply_to = 'arunlogistics1@gmail.com'

		name_list = customer_docs.docs.split(',')

		pages = []
		for id in name_list:
			pages.append(frappe.get_print_format('Sales Invoice', id, 'Consignment Note'))
		html = """<div class="page-break"></div>""".join(pages)

		mail.add_pdf_attachment('March-16 Consignment Notes.pdf', html)

		send(mail)


def get_recipients(customer):
	email_from_contacts = set([x[0] for x in frappe.db.sql("""
	select DISTINCT email_id
	from `tabContact`
	where customer = "{}"
	and ifnull(email_id, '') != '';
	""".format(customer))])

	email_from_address = set([x[0] for x in frappe.db.sql("""
	select DISTINCT email_id
	from `tabAddress`
	where customer = "{}"
	and ifnull(email_id, '') != '';
	""".format(customer))])

	emails = email_from_contacts.union(email_from_address)

	return list(emails)