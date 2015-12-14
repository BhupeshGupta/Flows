# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import os
import pickle
import shutil

import requests
import requests.utils

from bs4 import BeautifulSoup
from frappe.model.document import Document
from frappe.utils import get_files_path
import frappe, frappe.utils
import time
from flows.stdlogger import root

fname = 'pextax.png'


class PextaxIntegration(Document):
	def request(self):
		c = requests.session()

		request = c.get(
			"https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise",
			params={'_nfpb': 'true', '_nfls': 'false', '_pageLabel': 'login'}
		)

		with open('/tmp/pextax_cookie', 'w') as f:
			pickle.dump(requests.utils.dict_from_cookiejar(request.cookies), f)

		response = c.get("https://www.pextax.com/PEXWAR/stickyImg", stream=True)


		public_path = get_files_path()

		frappe.create_folder(public_path)

		try:
			os.remove(get_files_path(fname))
		except OSError:
			pass

		with open(os.path.join(public_path.encode('utf-8'), fname.encode('utf-8')), 'w+') as f:
			shutil.copyfileobj(response.raw, f)
		del response

		path = os.path.relpath(get_files_path(fname), public_path)

		frappe.msgprint('Please reload to get captcha and run program')

		self.file = '/files/' + path

		self.save()

	def login(self, session):
		ocr_value = self.captcha

		if ocr_value:
			payload = {
			'username': 'ICC00022873',
			'password': '6pN@COk7m',
			'answer': ocr_value
			}

			response = session.post(
				"https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise",
				params={'_nfpb': 'true', '_windowLabel': 'HeaderController_2'},
				data=payload,
				allow_redirects=False
			)

			return 'Set-Cookie' in response.headers

		return False

	def reconcile(self):
		for icc_form in frappe.db.sql("""
			select name, invoice_no from `tabICC Form`
			where name not in (
				select icc_form
				from `tabIndent Invoice`
				where docstatus != 2
				and icc_form != ''
			)
		""", as_dict=True):

			frappe.db.sql("""
				UPDATE `tabIndent Invoice`
				SET icc_form = '{icc_form}'
				WHERE invoice_number = '{invoice_no}'
			""".format(icc_form=icc_form.name, invoice_no=icc_form.invoice_no))

		frappe.db.commit()
		frappe.msgprint("Run Success! ICC form list updated.")



	def run(self):
		f = open('/tmp/pextax_cookie', 'rb')
		session = requests.Session()
		session.cookies = requests.utils.cookiejar_from_dict(pickle.load(f))

		if self.login(session):
			total_forms = []

			# Init search page to bypass system
			session.get('https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise', params={
			'_nfpb': 'true',
			'_pageLabel': 'PunjabExcise_portal_page_90'
			})

			# Collect all ref no from search pages
			rs = get_search_html(session, self.from_date, self.to_date)
			for i in [(i - 1) * 5 for i in xrange(rs['current_page'], rs['total_pages'] + 1)]:
				data = {'IccStatusSearchController_2netui_row': 'Table;{}'.format(i)} if i > 0 else {}
				rs = get_search_html(session, self.from_date, self.to_date, data)
				total_forms.extend(rs['date_list'])

			final_data_list = []

			for ref in total_forms:
				try:
					final_data_list.append(scrape_detail_page(session, ref['Request Number']))

					common_db_dict = {'doctype': 'ICC Form'}
					for data in final_data_list:
						if frappe.db.sql("""SELECT name FROM `tabICC Form` WHERE acknowledgement_no='{}'""".format(
								data['acknowledgement_no']
						)):
							continue
						data.update(common_db_dict)
						doc = frappe.get_doc(data)
						doc.ignore_permissions = True
						doc.save()
				except Exception as e:
					root.error(e)
					root.error(ref)

			self.last_run_on = frappe.utils.now()
			self.last_run_from_date = self.from_date
			self.last_run_to_date = self.to_date

			try:
				os.remove(get_files_path(fname))
			except OSError:
				pass

			self.save()

			frappe.db.commit()

			frappe.msgprint("Run Success! Check ICC Forms for details.")

		else:
			frappe.msgprint('Login Failed!')


def get_search_html(session, from_date, to_date, data={}):
	data_load = {
	'IccStatusSearchController_2{actionForm.refNo}': '',
	'IccStatusSearchController_2{actionForm.vehicle_NoSearch}': '',
	'IccStatusSearchController_2wlw-select_key:{actionForm.iccFromtype}OldValue': 'true',
	'IccStatusSearchController_2wlw-select_key:{actionForm.iccFromtype}': 'VAT-12',
	'IccStatusSearchController_2wlw-select_key:{actionForm.status}OldValue': 'true',
	'IccStatusSearchController_2wlw-select_key:{actionForm.status}': '',
	'IccStatusSearchController_2{actionForm.form_date}': '/'.join(reversed(from_date.split('-'))),
	'IccStatusSearchController_2{actionForm.to_date}': '/'.join(reversed(to_date.split('-')))
	}

	data_load.update(data)

	preview = session.post(
		"https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise",
		params={
		'_nfpb': 'true',
		'_windowLabel': 'IccStatusSearchController_2',
		'IccStatusSearchController_2_actionOverride': '/com/pex/portal/searchFormStatus/controller/submit'
		},
		data=data_load
	)

	soup = BeautifulSoup(preview.text, 'lxml')

	headings = [h.text.strip() for h in soup.find("tr", {"headrow"}).findAll('td')]

	data_map = []
	for row in soup.find('table', {'datagrid'}).findAll('tr')[:-1]:
		data_row_dict = {}
		for index, td in enumerate(row.findAll('td')):
			data_row_dict[headings[index]] = td.text.strip()
		if data_row_dict:
			data_map.append(data_row_dict)

	page_ref = soup.find('table', {'datagrid'}).findAll('tr')[-1]('td')[0].text.split('First')[0].strip().split(' ')

	return {
	'date_list': data_map,
	'current_page': int(page_ref[1]),
	'total_pages': int(page_ref[3])
	}


def scrape_detail_page(session, ack_no):
	detail_html = session.get(
		'https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise',
		params={
		'_nfpb': 'true',
		'_windowLabel': 'IccStatusSearchController_2',
		'IccStatusSearchController_2_actionOverride': '/com/pex/portal/searchFormStatus/controller/anchor',
		'IccStatusSearchController_2refNo': ack_no
		}).text
	return scrape_acknowledgement_page(detail_html)


def scrape_acknowledgement_page(page):
	def map_date(date):
		return '-'.join(reversed(date.split('/')))

	soup = BeautifulSoup(page, 'lxml')

	base_table = soup.find("table", {"frmtable"})
	goods_table = soup.find("table", {'id': 'tableId'})
	vehicle_table = soup.findAll("table", {"frmtable"})[4]

	return {
	'acknowledgement_no': base_table('tr')[0]('td')[1].text.strip(),
	'icc_name': base_table('tr')[0]('td')[3].text.strip(),
	'import_export': base_table('tr')[1]('td')[1].text.strip(),
	'date_of_issue': map_date(base_table('tr')[1]('td')[3].text.strip()),
	'consigner_tin_no': base_table('tr')[2]('td')[1].text.strip(),
	'consigner_name': base_table('tr')[2]('td')[3].text.strip(),
	'consigner_addr': base_table('tr')[3]('td')[1].text.strip(),
	'consignee_tin_no': base_table('tr')[6]('td')[1].text.strip(),
	'consignee_name': base_table('tr')[6]('td')[3].text.strip(),
	'nature_of_txn': base_table('tr')[18]('td')[1].text.strip(),
	'item_code': goods_table('tr')[0]('td')[1].text.strip(),
	'item_name': goods_table('tr')[0]('td')[2].text.strip(),
	'invoice_no': goods_table('tr')[0]('td')[4].text.strip(),
	'invoice_date': map_date(goods_table('tr')[0]('td')[6].text.strip()),
	'invoice_qty': goods_table('tr')[0]('td')[8].text.strip(),
	'invoice_amt': goods_table('tr')[0]('td')[10].text.strip(),
	'freight_amt': goods_table('tr')[0]('td')[12].text.strip(),
	'total_amt': goods_table('tr')[0]('td')[14].text.strip(),
	'total_amt_in_words': goods_table('tr')[0]('td')[16].text.strip(),
	'vehicle_number': vehicle_table('tr')[1]('td')[1].text.strip(),
	'gr_date': map_date(vehicle_table('tr')[4]('td')[3].text.strip())
	}
