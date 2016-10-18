import re
from collections import OrderedDict

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import frappe
from flows.stdlogger import root
from frappe.utils import flt
from frappe.utils.data import date_diff, today

PORTAL_STATEMENT_HEADERS = (
	'Company Name',
	'Plant',
	'Document Number',
	'Item Text',
	'Document Type',
	'Date',
	'Material Description',
	'Quantity',
	'Unit',
	'Debit',
	'Credit',
	'Balance'
)

PORTAL_STATEMENT_FTL_MEMBERS = (
	'Debit',
	'Credit',
	'Quantity',
	'Balance'
)


class IOCLPortal(object):
	@classmethod
	def parse_date(cls, date):
		return '-'.join(reversed(date.split('.')))

	@classmethod
	def parse_amount(cls, amt):
		v = flt(amt.strip())
		return v if (v or v == 0) else amt

	def __init__(self, user, passwd, debug=False):
		self.user = user
		self.passwd = passwd
		self.debug = debug
		self.session = None

	def get_session(self):
		if not self.session:
			import logging

			logging.basicConfig(level=logging.DEBUG)

			proxy_map = {}
			if frappe.conf.iocl_proxy:
				proxy_map['http'] = frappe.conf.iocl_proxy

			self.session = requests.Session()
			self.session.proxies = proxy_map
			self.session.headers.update({
				'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_0) AppleWebKit/537.36 (KHTML, like Gecko) '
							  'Chrome/54.0.2840.59 Safari/537.36'
			})

			retry = Retry(
				total=10, connect=5, read=5, redirect=5,
				method_whitelist=('GET', 'POST'), status_forcelist=None,
				backoff_factor=0.1
			)
			adapter = IOCLAdapter(max_retries=retry)
			self.session.mount('https://', adapter)
			self.session.mount('http://', adapter)

		return self.session

	def login(self):
		s = self.get_session()
		login_key = {
			'LogId': self.user,
			'LogPwd': self.passwd,
			'LogType': 2
		}
		content = s.post('http://webapp.indianoil.co.in/ioconline/iocExSignIn.jsp', data=login_key).text
		if self.debug:
			root.debug(content)

	def transactions_since_yesterday(self, form_date=None, to_date=None, mode='raw'):
		"""
		:param form_date:
		:param to_date:
		:param mode:
		:return:
		"""

		def get_date(date):
			return IOCLPortal.parse_date(date)

		if form_date and date_diff(today(), get_date(form_date)) not in (0, 1):
			raise Exception('Can only fetch data from yesterday and today')

		session = self.get_session()
		content = session.post('http://webapp.indianoil.co.in/ioconline/iocExdaily_transaction_process.jsp').text

		if self.debug:
			root.debug(content)

		if mode == 'raw':
			return content

		soup = BeautifulSoup(content, 'lxml')
		headings = [td.text.strip() for td in soup.findAll('table')[4].findAll('tr')[0].findAll('td')]

		data_map = []
		for row in soup.findAll('table')[4].findAll('tr')[1:]:
			data_row_dict = {}
			for index, td in enumerate(row.findAll('td')):
				data_row_dict[headings[index]] = td.text.strip()

			txn_date = get_date(data_row_dict['Tran. Date'])

			if form_date and to_date and not (form_date <= txn_date <= to_date):
				continue

			data_map.append(data_row_dict)

		total_debit = total_credit = 0
		for row in data_map:
			amt = IOCLPortal.parse_amount(row['Bill Amt'])
			if row['Db/Cr'] == 'D':
				total_debit += amt
			else:
				total_credit += amt

		return {
			'txns': data_map,
			'current_balance': float(soup.findAll('table')[5].text.split(':')[1].replace(',', '').strip()),
			'total_credit': total_credit,
			'total_debit': total_debit
		}

	def get_current_balance_as_on_date(self, cca='Total'):
		session = self.get_session()
		content = session.post('http://webapp.indianoil.co.in/ioconline/iocExcust_bal_process.jsp').text

		soup = BeautifulSoup(content, 'lxml')

		valid_rows = [x for x in soup.findAll('table')[3].findAll('table')[0].findAll('tr') if x.text.strip() != '']

		rows = []
		for row in valid_rows:
			data = [x.text.strip() for x in row.findAll('td')]
			rows.append(data)

		header = rows[0]
		data = rows[1:-1]
		closing = rows[-1]

		rs = {
			'balance': 0,
			'cca': {},
			'closing': 0
		}
		for data_row in data:
			cca_dict = {k: v for k, v in zip(header, data_row)}
			cca_dict['Balance'] = IOCLPortal.parse_amount(cca_dict['Balance'])
			rs['cca'][cca_dict['CCA']] = cca_dict

		rs['closing'] = IOCLPortal.parse_amount(closing[4])

		if cca == 'Total':
			rs['balance'] = rs['closing']
		else:
			rs['balance'] = rs['cca'][cca]['Balance']

		return rs

	def get_pricing(self, customer_code, plant_code, material_code, c_form=False, excise_concession=False):
		def parse_pricing_content(content):
			def txt(elem):
				return elem.text.replace('&nbsp', '').strip()

			soup = BeautifulSoup(content, 'lxml')
			pricing_table = soup.findAll('b', text=re.compile('.*Pricing Element.*'))

			rs = OrderedDict()
			if pricing_table:
				pricing_table = pricing_table[0].parent.parent.parent.parent
				for i in pricing_table.find_all_next('tr'):
					if i.findAll('td'):
						rs[txt(i.find_all_next('td')[0])] = IOCLPortal.parse_amount(txt(i.find_all_next('td')[1]))

			return rs

		session = self.get_session()
		data = {
			'LogId': customer_code,
			'custcode': customer_code,
			'sold_to': customer_code,
			'ship_to': customer_code,
			'plant': plant_code,
			'matnr': material_code,
			'DISTCHAN': 'CO',
		}
		if c_form:
			data.update({'CFORM': 'C'})
		if excise_concession:
			data.update({'EXCISE': 3})

		content = session.post('http://webapp.indianoil.co.in/ioconline/iocExPriceElement_process.jsp', data=data).text
		return parse_pricing_content(content)

	def retrieve_statement(self, from_date, to_date):
		"""
		Retrieve account statement of logged in user from `from_date` & `to_date`
		:param from_date: '2016-10-01'
		:param to_date:  '2016-10-30'
		:return:
		"""
		session = self.get_session()

		data = {
			'fromDate': from_date.replace('-', ''),
			'toDate': to_date.replace('-', '')
		}

		content = session.post('http://webapp.indianoil.co.in/ioconline/RetriveData', data=data).text\
			.split('#########')

		soup = BeautifulSoup(content[0], 'lxml')

		data = [{PORTAL_STATEMENT_HEADERS[index]: col.text.strip() for index, col in enumerate(row.find_all('td'))} for
				row in soup.find_all('tr')]

		# Data normalisation, parse amounts and dates in to flt and standard date format
		for row in data:
			for m in PORTAL_STATEMENT_FTL_MEMBERS:
				if row[m]:
					row[m] = IOCLPortal.parse_amount(row[m])
			if row['Date']:
				row['Date'] = '20{}'.format(IOCLPortal.parse_date(row['Date']))

		return data


class IOCLAdapter(HTTPAdapter):
	def send(self, request, timeout=None, **kwargs):
		return super(IOCLAdapter, self).send(request, timeout=(10, 20), **kwargs)
