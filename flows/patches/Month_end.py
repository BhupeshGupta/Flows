from frappe.utils.email_lib.email_body import get_email
import frappe
from frappe.utils.email_lib.smtp import send


def execute():
	for customer_docs in frappe.db.sql("""
	select DISTINCT gr.customer
	from `tabGoods Receipt` gr left join `tabCustomer` c on c.name=gr.customer
	where gr.posting_date between '2015-01-01' and '2015-03-31'
	and c.customer_group not in ('pallav singla', 'BADDI', 'SANGRUR', 'HARIDIYA', 'NOIDA');
	""", as_dict=True):

		mail = get_email(
			get_recipients(customer_docs.customer),
			sender='noreply@arungas.com',
			subject='Shifting to Paper-less transactions / e-challans from 01.04.2016',
			msg="""
We are thankful to you for supporting us in last financial year. We request you to please give the same support in the new Financial year 2016-17 to achieve new heights as a team.

AS EARLIER COMMUNICATED TO YOUR GOOD SELF THAT WE ARE SHIFTING OUR DELIVERY SYSTEM TO PAPER-LESS TRANSACTIONS / E-CHALLANS FROM 01.04.2016 FOR BETTER TRANSPARENCY & ACCOUNTING, WE SEEK YOUR SUPPORT IN ORDER TO IMPLEMENT THE SAME.
IN ORDER TO MAINTAIN THE RECORD AT YOUR PREMISES, WE HAD ALREADY DELIVERED THE LOG-BOOK TO YOUR GOOD SELF. PLEASE INSTRUCT THE CONCERNED TO NOTE & ENTER EACH & EVERY TRANSACTION OF CYLINDERS & INVOICES ALONG-WITH SIGNATURE OF OUR FIELD BOY / DELIVERY STAFF.
A COPY / SAMPLE OF LOG-BOOK ENCLOSED FOR YOUR READY REFERENCE.

SMS SERVICE HAD ALREADY BEEN STARTED FOR EACH & EVERY TRANSACTION OF FILLED & EMPTY CYLINDER. FOR FURTHER STRENGTHEN THE E-CHALLAN SYSTEM WE ARE GOING TO START EMAIL SERVICE FOR THE SAME. A DRAFT PERFORMA IS ATTACHED FOR AVAILING THE SMS & EMAIL SERVICES.
PLS FILL & PRINT THE SAME ON YOUR LETTER HEAD & SEND THE SOFT COPY VIA EMAIL & ORIGINAL BY POST.
IN CASE OF ANY QUERY / DIFFICULTY / PROBLEM PLS FEEL FREE TO CALL AT - 84375-03222, 84375-05222 OR EMAIL AT - arunlogistics1@gmail.com
			"""
		)
		mail.cc.append('arunlogistics1@gmail.com')
		mail.reply_to = 'arunlogistics1@gmail.com'

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