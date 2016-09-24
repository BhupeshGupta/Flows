import json
from frappe.utils.file_manager import upload
import frappe
import requests
from frappe.utils import cint
from flows.stdlogger import root
import shutil
import uuid
from frappe.utils.pdf import get_pdf
from frappe.utils.email_lib.email_body import get_email
from frappe.utils.email_lib.smtp import send


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
    				(select distinct m.transportation_invoice
    				from
    					(select s.transportation_invoice from
    					`tabIndent Invoice` s where s.name in
    							(select SUBSTRING_INDEX((
    								case
    									when
    					 					( l.amended_from is null)
    									then
    					 					l.name
    									else
    										l.amended_from
    								end),'-',1) as bill_number from `tabIndent Invoice` l
    								where
    								posting_date between '2016-09-01' and current_date()
    								and docstatus = 1
    							)
    				) as m where m.transportation_invoice
    				not in
    					(select distinct p.cno from documentqueue.currentstat p)
    			) a
    			where
    			r.transportation_invoice = a.transportation_invoice;
    			""")

	for i in remaining:
		print i[0]
		print len(remaining)
		doc = frappe.get_doc("Indent Invoice", i[0])
		create_docs_in_review_server(doc)
		r.append(i[0])

	print r


def url_formatter(url):
	url = url.split("proxy/alfresco/api/node/");
	temp = url[1].replace("/", "://", 1);
	url = url[0] + 'page/site/receivings/document-details?nodeRef=' + temp;
	url = url.split("/content/thumbnails/imgpreview");
	url = url[0];
	url = url.split("/share/page/site/{}/document-details?nodeRef=".format(frappe.conf.alfresco_site));
	print url
	temp = url[1].replace("://", "/", 1)
	temp = temp.split("/")
	url = url[0] + "/alfresco/s/api/node/content/{}/{}/{}".format(temp[0], temp[1], temp[2])
	return url




def generate_link_array(docs):
	link_array = []
	individual_array= {}

	for key,value in docs.items():
		print key,value
		if 'Consignment Note' in value:
			print key,value
			print "true"
			consignment_meta = frappe.db.sql("""select p.customer, p.posting_date, p.grand_total, p.receiving_file
								 from `tabSales Invoice` p
								 where '{}' = p.name;""".format(key)
								 )
			consignment_note_row = """<tr>
										<th style = "background:#222; color:#fff;text-align:left;text-transform:uppercase;font-size:13px;">Customer</th>
										<th style = "background:#222; color:#fff;text-align:left;text-transform:uppercase;font-size:13px;">Date</th>
										<th style = "background:#222; color:#fff;text-align:left;text-transform:uppercase;font-size:13px;">Amount</th>
										</tr><tr>
										<td style = "color:#666; font-size:13px;">{}</td>
										<td style = "color:#666; font-size:13px;">{}</td>
										<td style = "color:#666; font-size:13px;">{}</td>
										</tr>""".format(consignment_meta[0][0],consignment_meta[0][1],consignment_meta[0][2])
		if 'Indent Invoice' in value:
			indent_meta = frappe.db.sql("""select p.invoice_number,p.transaction_date, p.actual_amount, p.receiving_file, p.data_bank
									from `tabIndent Invoice` p
									where p.transportation_invoice= '{}';""".format(key)
								 )
			indent_meta_row = """<tr>
									<th style = "background:#222; color:#fff;text-align:left;text-transform:uppercase;font-size:13px;">Invoice Number</th>
									<th style =" background:#222; color:#fff;text-align:left;text-transform:uppercase;font-size:13px;">Date</th>
									<th style = "background:#222; color:#fff;text-align:left;text-transform:uppercase;font-size:13px;">Amount</th>
								</tr><tr>
									<td style = "color:#666; font-size:12px;">{}</td>
									<td style = "color:#666; font-size:12px;">{}</td>
									<td style = "color:#666; font-size:12px;">{}</td>
								</tr>""".format(indent_meta[0][0],indent_meta[0][1],indent_meta[0][2])

		total_rows = ""
		if consignment_note_row:
			total_rows = total_rows + consignment_note_row
		if indent_meta_row:
			total_rows = total_rows + indent_meta_row

		email_template_table = """<table style = "width: 100%;border:0; background:#efefef;cellspacing:0; cellpadding:0;">{}</table>""".format(total_rows)
		data_bank = indent_meta[0][4]
		data_bank = json.loads(data_bank)
		print data_bank
		receivings = data_bank['receivings']
		print receivings
		if "VAT Form XII" in value:
			individual_array['VAT Form XII'] = receivings['VAT Form XII']

		if "Consignment Note" in value:
			individual_array['Consignment Note'] = consignment_meta[0][3]

		if "Indent Invoice" in value:
			individual_array['Indent Invoice'] = indent_meta[0][3]

		if "Excise_Invoice" in value:
			individual_array['Excise_Invoice'] = receivings['Excise_Invoice']

		link_array.append(individual_array)

	download_images(link_array,email_template_table)



def download_images(link_array,email_table):
	local_links = {}
	html = "<style></style>"

	for each_link in link_array:
		print each_link
		for key, value in each_link.items():
			url = url_formatter(value)
			response = requests.get(url, stream=True, auth=(frappe.conf.alfresco_user, frappe.conf.alfresco_password))
			path = "/home/erpnext/frappe-bench/sites/erpnext.erpnext-vm/public/files/temp/{}.jpg".format(uuid.uuid4())
			with open(path, 'wb+') as out_file:
				shutil.copyfileobj(response.raw, out_file)
			del response
			temp_path = path.split("/home/erpnext/frappe-bench/sites/erpnext.erpnext-vm/public")
			local_links[key] = frappe.conf.host_name + temp_path[1]
		print local_links

		for link in local_links.items():
			html = html + link[0] + """<br><img src = "{}" style = "max-height:260mm;max-width:210mm"><br>""".format(
				link[1])
		pdf = get_pdf(html)
		email_list = "ankitadhimaan27@gmail.com"
		frappe.msgprint("sending email to {}".format(email_list))

		email_object = get_email(
			email_list, sender='',
			msg=email_table,
			subject='This Is The Subject Of the email',
			formatted=False, attachments=[{'fname': 'Weekly_Report.pdf', 'fcontent': pdf}]
		)

		send(email_object)