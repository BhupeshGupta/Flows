import json
import shutil
import uuid
import requests
from frappe.utils import cint
from frappe.utils.pdf import get_pdf
from frappe.utils import today, add_months, getdate
import frappe
from frappe.utils.email_lib.email_body import get_email
from frappe.utils.email_lib.smtp import send
from flows.flows.doctype.quotation_tool.quotation_tool import get_print_format
import re
import os

DOWNLOAD_DIR = os.path.join(frappe.local.site_path, "public/files/temp")


def make_tracking_table():
	end_date = today()
	start_date = add_months(end_date, -1)
	if getdate(start_date) < getdate('2016-09-01'):
		start_date = '2016-09-23'

	scn_numbers = frappe.db.sql("""
	select si.name as sales_invoice,
	si.amended_from as sales_invoice_amended_from,
	ii.name as indent_invoice
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
	) si left join `tabIndent Invoice` ii
	on ii.transportation_invoice = si.name
	""".format(
		start_date=start_date,
		end_date=end_date
	), as_dict=True)

	for scn in scn_numbers:

		normalised_sales_invoice = scn.sales_invoice.rsplit("-", 1)[0] if scn.sales_invoice_amended_from else scn.sales_invoice

		doc = frappe.get_doc({
			"doctype": "Sales Invoice Email Tracking",
			"document_type": "Consignment Note" if scn.indent_invoice else "Sales Invoice",
			"sales_invoice_number": normalised_sales_invoice,
			"email": "0",
		})
		doc.save()

		if scn.indent_invoice:
			doc = frappe.get_doc({
				"doctype": "Sales Invoice Email Tracking",
				"document_type": "Indent Invoice",
				"sales_invoice_number": normalised_sales_invoice,
				"email": "0",
			})
			doc.save()

			indent_invoice = frappe.db.get_values("Indent Invoice", {
				"transportation_invoice": scn.sales_invoice
			}, "*")[0]

			if indent_invoice.sales_tax == 'CST':
				doc = frappe.get_doc({
					"doctype": "Sales Invoice Email Tracking",
					"document_type": "VAT Form XII",
					"sales_invoice_number": normalised_sales_invoice,
					"email": "0"
				})
				doc.save()

			if 'hpcl' in indent_invoice.supplier.lower() and cint(indent_invoice.cenvat) == 1:
				doc = frappe.get_doc({
					"doctype": "Sales Invoice Email Tracking",
					"document_type": "Excise_Invoice",
					"sales_invoice_number": normalised_sales_invoice,
					"email": "0",
				})
				doc.save()

	return "Table Updated Successfully"


def email_invoices_to_customers():
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

	from premailer import transform

	for customer, docs in customer_scn_map.items():
		pdf_pages = []
		meta_rows = []
		all_links = []

		for scn, scn_docs in docs.items():
			links, rows = get_download_links_and_metadata(scn, scn_docs)
			meta_rows.extend(rows)

			for key, value in links.items():
				links[key] = get_image_download_url(value)

			rs_links = download_files_and_get_local_links(links)
			all_links.extend(rs_links)
			data = render({'doc': {'links': rs_links}}, format='Invoice Receiving PDF')
			pdf_pages.append(data)

		unique_id = uuid.uuid4()
		email = render({'doc': {'invoices': meta_rows, 'uuid': unique_id}})
		email = transform(email, base_url=frappe.conf.host_name + '/')
		pdf = get_pdf(''.join(pdf_pages), {
			'margin-top': '0mm',
			'margin-right': '0mm',
			'margin-bottom': '0mm',
			'margin-left': '0mm'
		})

		email_list = [
			c[0] for c in frappe.db.sql("""
			SELECT email_id FROM `tabContact` WHERE ifnull(email_id, '') != '' AND customer = "{}"
			""".format(customer))
		]

		email_list = 'bhupesh00gupta@gmail.com'

		frappe.msgprint("sending email to {}".format(email_list))

		email_object = get_email(
			email_list,
			sender='',
			msg="",
			subject='Scanned Invoice Receivings: {}'.format(customer),
			formatted=False,
			print_html=email,
			attachments=[{'fname': 'invoices.pdf', 'fcontent': pdf}]
		)
		send(email_object)

		set_email_sent_status(docs, unique_id)

		cleanup(all_links)


def set_email_sent_status(docs, unique_id):
	condition = " or\n".join(
		[
			'( sales_invoice_number = "{}" and ({}) )'.format(
				scn,
				' or '.join(
					['document_type = "{}"'.format(type) for type in doc]
				)
			) for scn, doc in docs.items()
		]
	)
	frappe.db.sql("""
		update `tabSales Invoice Email Tracking`
		set email = 1, tracker = "{}"
		where {}
	""".format(unique_id, condition))


def cleanup(local_links):
	for link in local_links:
		file_path = os.path.join(DOWNLOAD_DIR, re.findall('.*/files/temp/(.*)', link)[0])
		os.remove(file_path)


def download_files_and_get_local_links(links):
	rs_links = []

	if not os.path.exists(DOWNLOAD_DIR):
		os.makedirs(DOWNLOAD_DIR)

	for key, value in links.items():
		response = requests.get(value, stream=True, auth=(frappe.conf.alfresco_user, frappe.conf.alfresco_password))
		file_name = "{}.jpg".format(uuid.uuid4())

		with open(os.path.join(DOWNLOAD_DIR, file_name), 'wb+') as out_file:
			shutil.copyfileobj(response.raw, out_file)
		del response

		rs_links.append('{}/files/temp/{}'.format(frappe.conf.host_name, file_name))

	return rs_links


def get_image_download_url(url):
	"""
	Input: http://docs.arungas.com:8080/share/proxy/alfresco/api/node/workspace/SpacesStore/0459abf1-38bd-45a5-97cd-f579a2ca7e8e/content/thumbnails/imgpreview
	Output: http://docs.arungas.com:8080/alfresco/s/api/node/content/workspace/SpacesStore/0459abf1-38bd-45a5-97cd-f579a2ca7e8e
    :param url:
    :return:
    """
	link = re.findall("(.*)/share/proxy/alfresco/api/node/(.*)/content/.*", url)[0]
	return "{}/alfresco/s/api/node/content/{}".format(*link)


def get_download_links_and_metadata(scn, docs_array):
	links = {}
	rows = []

	if 'Consignment Note' in docs_array:
		consignment_meta = frappe.db.sql("""
			select name,
			posting_date as date,
			grand_total as amount,
			receiving_file
			from `tabSales Invoice`
			where name='{0}' or
			name like '{0}-%' and
			docstatus = 1
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