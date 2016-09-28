import json
import requests
from frappe.utils import cint
from flows.stdlogger import root
from frappe.utils import today, add_months, getdate
import frappe


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


