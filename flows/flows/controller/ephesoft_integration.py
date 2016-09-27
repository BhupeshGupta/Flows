import json
import shutil
import uuid

import frappe
import requests
from frappe.utils import cint
from flows.stdlogger import root
from frappe.utils.pdf import get_pdf
from frappe.utils.email_lib.email_body import get_email
from frappe.utils.email_lib.smtp import send
from frappe.utils import today, add_months, getdate
import frappe
from frappe.utils.email_lib.email_body import get_email
from frappe.utils.email_lib.smtp import send
from flows.flows.doctype.quotation_tool.quotation_tool import get_print_format
import re
import os


if not frappe.conf.document_queue_server:
	raise Exception('document_queue_server not found in config')

@frappe.whitelist(allow_guest=True)
def get_meta(doc):
	doc = json.loads(doc)

	query = {
	'doctype': 'Sales Invoice' if doc['type'] in ('Consignment Note',) else '',
	'name': doc['id']
	}

	return_doc = {}
	if doc['type'] == 'Consignment Note':
		return_doc.update(
			frappe.db.sql("""
			select invoice_number as `Bill Number`, transaction_date as `Bill Date`, item as `Bill Item`,
			qty as `Bill Quantity`, actual_amount as `Bill Amount`, supplier as `Bill Supplier`,
			vehicle as `Vehicle`, customer as `Customer`
			from `tabIndent Invoice`
			where (
				transportation_invoice = '{name}'
				or transportation_invoice like '{name}-%'
			)
			and docstatus = 1
			""".format(**query), as_dict=True)[0]
		)

		return_doc.update(
			frappe.db.sql("""
			select name as `Consignment Name`, posting_date as `Consignment Date`,
			grand_total_export as `Consignment Amount`, company as `Consignment Company`,
			amended_from as `$amended_from`
			from `tab{doctype}`
			where (
			name = '{name}'
			or name like '{name}-%'
			) and docstatus != 2
			""".format(**query), as_dict=True)[0]
		)

	return json.dumps(return_doc)


def create_docs_in_review_server(doc, method=None, *args, **kwargs):
	if frappe.conf.document_disabled:
		return
	
	docs = []

	if doc.transaction_date < '2016-06-01':
		return

	sales_invoice_amended_from = frappe.db.get_value("Sales Invoice", doc.transportation_invoice, 'amended_from')

	# Normalizations
	doc.transportation_invoice_number = '-'.join(doc.transportation_invoice.split('-')[:-1]) if (sales_invoice_amended_from and sales_invoice_amended_from.strip()) else doc.transportation_invoice

	# Material Bill / Indent Invoice
	docs.append({'cno': doc.transportation_invoice_number, 'doctype': doc.doctype, 'date': doc.transaction_date})

	# Consignment note
	docs.append({'cno': doc.transportation_invoice_number, 'doctype': "Consignment Note", 'date': doc.posting_date})

	if doc.sales_tax == 'CST':
		docs.append({'cno': doc.transportation_invoice_number, 'doctype': "VAT Form XII", 'date': doc.transaction_date})

	if 'hpcl' in doc.supplier.lower() and cint(doc.cenvat) == 1:
		docs.append({'cno': doc.transportation_invoice_number, 'doctype': "Excise Invoice", 'date': doc.transaction_date})

	for sails_doc in docs:
		data = requests.post('{}/currentstat/'.format(frappe.conf.document_queue_server), sails_doc)
		root.debug(sails_doc)

		if data.status_code not in [200, 201]:
			content = data.content
			root.debug((data.status_code, content))
			content = json.loads(content)

			if 'invalidAttributes' in content and \
				len(content['invalidAttributes'].keys()) == 1 and \
				 'unique_notes' in content['invalidAttributes']:
				continue

			raise Exception(
				'Document Queue Server returned {} \n {}'.\
					format(data.status_code, data.content)
			)


@frappe.whitelist()
def get_user():
	return json.dumps({'user': frappe.session.user})


@frappe.whitelist()
def push_remaining():
	remaining = {}
	r = []
	remaining = frappe.db.sql("""
	select r.name
	from `tabIndent Invoice` r,
	(
		select distinct m.transportation_invoice
		from (
				select s.transportation_invoice from
				`tabIndent Invoice` s
				where s.name in
				(
					select SUBSTRING_INDEX(
						(
							case
								when
									(l.amended_from is null)
									then l.name
									else l.amended_from
								end
						),
						'-',
						1
					) as bill_number
					from `tabIndent Invoice` l
					where posting_date between '2016-09-01' and current_date() and
						docstatus = 1
				)
		) as m
		where
			m.transportation_invoice not in
			(
				select distinct cno
				from documentqueue.currentstat
			)
	) a
	where r.transportation_invoice = a.transportation_invoice;
	""")

	for i in remaining:
		print i[0]
		print len(remaining)
		doc = frappe.get_doc("Indent Invoice", i[0])
		create_docs_in_review_server(doc)
		r.append(i[0])

	print r



def make_tracking_table():
	end_date = today()
	start_date = add_months(end_date, -1)
	if getdate(start_date) < getdate('2016-09-01'):
		start_date = '2016-09-23'

	scn_numbers = frappe.db.sql("""
	select m.name as sales_invoice,
	m.amended_from as sales_invoice_amended_from,
	q.name as indent_invoice
	from (
		select si.name, si.posting_date, si.amended_from
		from `tabSales Invoice` si left join `tabSales Invoice Email Tracking` t
		on t.sales_invoice_number = IF(
			ifnull(si.amended_from, '') = '',
			si.name,
			REPLACE(si.name, CONCAT('-', SUBSTRING_INDEX(si.name, '-', -1)), '')
		)
		where t.sales_invoice_number is null and
			si.posting_date between "{start_date}" and "{end_date}"
			and si.docstatus = 1
	) m	left join `tabIndent Invoice` q
	on q.transportation_invoice = m.name
	""".format(start_date=start_date, end_date=end_date),
	as_dict=True)


	for scn_tupple in scn_numbers:
		print scn_tupple
		sales_invoice = scn_tupple['sales_invoice']
		if scn_tupple['sales_invoice_amended_from']:
			sales_invoice = sales_invoice.rsplit("-",1)[0]
		else :
			sales_invoice = scn_tupple['sales_invoice']

			doc = frappe.get_doc({
				"doctype": "Sales Invoice Email Tracking",
				"document_type": "Consignment Note",
				"sales_invoice_number": "{}".format(sales_invoice),
				"email": "0",
			})
			doc.save()

		if scn_tupple['indent_invoice']:
			doc = frappe.get_doc({
				"doctype": "Sales Invoice Email Tracking",
				"document_type": "Indent Invoice",
				"sales_invoice_number": "{}".format(sales_invoice),
				"email": "0",
			})
			doc.save()

			q = frappe.db.get_values("Indent Invoice",
									 {"transportation_invoice": sales_invoice},
									 "*"
									 )
			data = q[0]

			if data["sales_tax"] == 'CST':
				doc = frappe.get_doc({
					"doctype": "Sales Invoice Email Tracking",
					"document_type": "VAT Form XII",
					"sales_invoice_number": "{}".format(sales_invoice),
					"email": "0"
				})
				doc.save()

			if 'hpcl' in data["supplier"].lower() and cint(data["cenvat"]) == 1:
				doc = frappe.get_doc({
					"doctype": "Sales Invoice Email Tracking",
					"document_type": "Excise_Invoice",
					"sales_invoice_number": "{}".format(sales_invoice),
					"email": "0",
				})
				doc.save()

		else:
			doc = frappe.get_doc({
				"doctype": "Sales Invoice Email Tracking",
				"document_type": "Sales Invoice",
				"sales_invoice_number": "{}".format(sales_invoice),
				"email": "0",
			})
			doc.save()


def get_customer():

	def render(doc, format='Invoice Receiving Email'):
		jenv = frappe.get_jenv()
		template = jenv.from_string(get_print_format('Invoice Receiving Email Tool', format))
		return template.render(**doc)

	scn_documents_map = frappe.db.sql("""
	select q.sales_invoice_number, group_concat(q.document_type) as docs
	from `documentqueue`.`currentstat` p join `tabSales Invoice Email Tracking` q
	on p.cno = q.sales_invoice_number and p.doctype = q.document_type
	where p.status = 1 and
	q.email = 0
	group by q.sales_invoice_number
	""")

	scn_documents_map = {x[0]: x[1].split(',') for x in scn_documents_map}

	condition = ' or\n'.join(["(name = '{0}' or name like '{0}-%')".format(scn) for scn in scn_documents_map.keys()])

	customer_scn_map = frappe.db.sql("""
	select customer, group_concat(
		  IF(
			ifnull(si.amended_from, '') = '',
			si.name,
			REPLACE(si.name, CONCAT('-', SUBSTRING_INDEX(si.name, '-', -1)), '')
		  )
		) as doc
	from `tabSales Invoice` si
	where {}
	and docstatus = 1
	group by customer
	""".format(condition))

	customer_scn_map = {x[0]: {y: scn_documents_map[y] for y in x[1].split(',')} for x in customer_scn_map}

	# from premailer import transform

	for customer, docs in customer_scn_map.items():
		pdf_pages = []
		meta_rows = []

		for scn, scn_docs in docs.items():
			links, rows = get_links_and_metadata(scn, scn_docs)
			meta_rows.extend(rows)

			for key, value in links.items():
				print key, value
				links[key] = url_formatter(value)

			rs_links = get_local_links(links)
			data = render({'doc': {'links': rs_links}}, format='Invoice Receiving PDF')
			pdf_pages.append(data)

		email = render({'doc': {'invoices': meta_rows}})
		# email = transform(email, base_url=frappe.conf.host_name + '/')
		pdf = get_pdf(''.join(pdf_pages))

		# email_list = [
		# 	c[0] for c in frappe.db.sql("""
		# 	SELECT email_id FROM `tabContact` WHERE ifnull(email_id, '') != '' AND customer = "{}"
		# 	""".format(customer))
		# ]

		email_list = 'bhupesh00gupta@gmail.com'

		frappe.msgprint("sending email to {}".format(email_list))
		email_object = get_email(
			email_list,
			sender='',
			msg="",
			subject='Right one',
			formatted=False,
			print_html=email,
			attachments=[{'fname': 'Weekly_Report.pdf', 'fcontent': pdf}]
		)
		send(email_object)


def get_local_links(links):

	rs_links = []
	directory = os.path.join(frappe.local.site_path, "public/files/temp")
	if not os.path.exists(directory):
		os.makedirs(directory)

	for key, value in links.items():
		response = requests.get(value, stream=True, auth=(frappe.conf.alfresco_user, frappe.conf.alfresco_password))
		file_name = "{}.jpg".format(uuid.uuid4())

		with open(os.path.join(directory, file_name), 'wb+') as out_file:
			shutil.copyfileobj(response.raw, out_file)
		del response

		rs_links.append('{}/files/temp/{}'.format(frappe.conf.host_name, file_name))

	return rs_links


def url_formatter(url):
	"""
	Input: http://docs.arungas.com:8080/share/proxy/alfresco/api/node/workspace/SpacesStore/0459abf1-38bd-45a5-97cd-f579a2ca7e8e/content/thumbnails/imgpreview
	Output: http://docs.arungas.com:8080/alfresco/s/api/node/content/workspace/SpacesStore/0459abf1-38bd-45a5-97cd-f579a2ca7e8e
	:param url:
	:return:
	"""
	link = re.findall("(.*)/share/proxy/alfresco/api/node/(.*)/content/.*", url)[0]
	return "{}/alfresco/s/api/node/content/{}".format(*link)


def get_links_and_metadata(scn, docs_array):
	links = {}
	rows = []

	if 'Consignment Note' in docs_array:
		consignment_meta = frappe.db.sql("""
			select customer,
			name,
			posting_date as date,
			grand_total as amount,
			receiving_file
			from `tabSales Invoice`
			where name='{0}' or name like '{0}-%'
		""".format(scn), as_dict=True)[0]
		links['Consignment Note'] = consignment_meta.receiving_file

		rows.append(consignment_meta)

	indent_meta = frappe.db.sql("""
	select invoice_number as name,
	transaction_date as date,
	actual_amount as amount,
	receiving_file,
	data_bank
	from `tabIndent Invoice`
	where transportation_invoice = '{0}' or transportation_invoice like '{0}-%'
	and docstatus = 1
	""".format(scn), as_dict=True)[0]

	if 'Indent Invoice' in docs_array:
		links['Indent Invoice'] = indent_meta.receiving_file
		rows.append(indent_meta)

	data_bank = json.loads(indent_meta.data_bank)

	if "VAT Form XII" in docs_array:
		links['VAT Form XII'] = data_bank['receivings']['VAT Form XII']
	if "Excise_Invoice" in docs_array:
		links['Excise_Invoice'] = data_bank['receivings']['Excise_Invoice']

	return links, rows