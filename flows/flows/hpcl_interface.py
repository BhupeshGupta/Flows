import requests

from bs4 import BeautifulSoup
from flows.stdlogger import root

from requests.adapters import HTTPAdapter

headers = {'User-agent': 'ALPINE ENERGY LIMITED ND Distributor/9914526902/alpineenergyhpcl@gmail.com'}


class HPCLCustomerPortal():
	def get_session(self):
		if not self.session:
			import logging

			logging.basicConfig(level=logging.DEBUG)
			self.session = requests.Session()
			self.session.mount('https://', HPCLAdapter(max_retries=5))
			self.session.mount('http://', HPCLAdapter(max_retries=5))
		return self.session

	def __init__(self, user, password, debug=False):
		self.user = user
		self.password = password
		self.session = None
		self.debug = debug

	def login(self):
		s = self.get_session()

		if not self.password or (self.password and self.password.strip() == ''):
			raise LoginError('Missing Password')

		login_key = {
		"cust_id": self.user,
		"pwd": self.password,
		"x": "14",
		"y": "0",
		"next": "html/home.html",
		"bad": "error/badlogin_en.html",
		"entityjavascript": "true",
		"entityscreensize": "unknown"
		}

		r = s.post("https://sales.hpcl.co.in/bportal/login/cust_login.jsp", data=login_key, headers=headers)
		content = r.content

		if self.debug:
			root.debug(content)

		if 'invalid' in content:
			raise LoginError('Invalid User')

		if 'lpg_select' in content:
			root.info('Login Success')

		if 'SERVER IS BUSY' in content:
			root.debug("Server busy. Will retry")
			raise ServerBusy()

	def get_account_data(self, from_date, to_date, mode='raw'):
		"""
		:param from_date: '2015-09-01'
		:param to_date: '2015-09-20'
		:param mode: 'raw' for HTML output, other for list
		:return:
		{
			'txns': [
						{
							"Cheque No./DD No.": "15178219",
							"Sales Order Reference": "15178886/RU/32002",
							"C.R/InvoiceDate": "05/06/15",
							"C.R / InvoiceReference": "15178219                 /32002/",
							"Cr Amount": "-157,000.00",
							"Bank Name": "HDFC  e RECEIPT",
							"Dr Amount ": "0.00",
							"Supply Location": "E Collection - LPG SBU- HDFC",
							"Sl.No": "1"
						},
						{
							"Cheque No./DD No.": "-",
							"Sales Order Reference": "15000978/S3/12103",
							"C.R/InvoiceDate": "05/06/15",
							"C.R / InvoiceReference": "15003383                 /RI/12121/001",
							"Cr Amount": "0.00",
							"Bank Name": "",
							"Dr Amount ": "154,599.52",
							"Supply Location": "BAHADURGARH LPG PLANT",
							"Sl.No": "2"
						}
			],
			'total_debit': 154599.52,
			'total_credit': 157000.00
		}
		"""
		s = self.get_session()
		account_data = {
		"txtfrmday": from_date.split('-')[2],
		"txtfrmmonth": from_date.split('-')[1],
		"txtfrmyear": from_date.split('-')[0],
		"txttoday": to_date.split('-')[2],
		"txttomonth": to_date.split('-')[1],
		"txttoyear": to_date.split('-')[0],
		"r2": "EXCEL"
		}
		account_data = s.post('https://sales.hpcl.co.in/bportal/lpg/accountdisp.jsp', data=account_data,
							  headers=headers, stream=True)
		content = account_data.content

		if self.debug:
			root.debug(content)

		if mode == 'raw':
			return content

		soup = BeautifulSoup(content)

		headings_list = [td.text.strip() for td in soup.body.findAll(id='Headings')[0].findAll('tr')[0].findAll('td')]
		content_rows = soup.body.findAll(id='content')[0].findAll('tr')[:-4]
		rs_list = []
		for row in content_rows:
			rs_list.append({headings_list[index]: value.text.strip() for index, value in enumerate(row.findAll('td'))})

		dr_cr = soup.findAll('tr')[-4].findAll('td')[4:6]
		dr_cr = (float(dr_cr[0].text.replace(',', '')), -1 * float(dr_cr[1].text.replace(',', '')))

		return {
		'total_debit': dr_cr[0],
		'total_credit': dr_cr[1],
		'txns': rs_list
		}

	def get_current_balance_as_on_date(self):
		s = self.get_session()

		data = s.post(
			'https://sales.hpcl.co.in/Cust_Credit_Client/CreditCheckResponseBP_Live.jsp',
			data={'custcode': self.user},
			headers=headers
		)
		content = data.content
		soup = BeautifulSoup(content)

		return float(soup.findAll('tr')[3].findAll('td')[1].text.replace("&nbsp", "").replace(',', ''))

	def get_invoice_data(self, from_date, to_date, mode='dict', ignore_empty_return=True):
		"""
		:param from_date:
		:param to_date:
		:param mode:
		:param ignore_empty_return:
		:return:
		{
			'total_price': 154599.52,
			'txns': [
				{
					"Total Pricein INR": "154,599.52",
					"Item Desc": "19 KG FILLED LPG CYLINDER",
					"Invoice Reference": "15003383  /RI/12121",
					"Item No.": "0948064",
					"Unit Pricein INR": "840.2148",
					"Ship To": "17259730 - UNITECH TEXTILES",
					"Shipping Location": "BAHADURGARH LPG PLANT",
					"Sales Order Reference": "15000978  /S3/12103/1.0",
					"Invoice Date": "05/06/15",
					"Original Order Reference": "15000183/DO/12103/1.0",
					"Sold To.": "17259730 - UNITECH TEXTILES",
					"Vehicle No.": "PB11H9297",
					"Product Type": "-",
					"ShippedQuantity": "184.000",
					"Unit": "EA",
					"Sr. No.": "1"
				},
				{
					"Total Pricein INR": "0.00",
					"Item Desc": "19 KG EMPTY LPG CYLINDER",
					"Invoice Reference": "15005845  /R3/12121",
					"Item No.": "0934064"
					"Unit Pricein INR": "0.0000",
					"Ship To": "17259730 - UNITECH TEXTILES",
					"Shipping Location": "BAHADURGARH LPG PLANT",
					"Sales Order Reference": "15000978  /S3/12103/2.0",
					"Invoice Date": "05/06/15",
					"Original Order Reference": "-",
					"Sold To.": "17259730 - UNITECH TEXTILES",
					"Vehicle No.": "",
					"Product Type": "-",
					"ShippedQuantity": "-184.000",
					"Unit": "EA",
					"Sr. No.": "2"
				}
			]
		}

		"""
		s = self.get_session()

		invoice_req_dict = {
		'cmbcat': 'ALL',
		'cmbitem': 'ALL',
		'cmbbranch': 'ALL',
		'cmbship': '{},ALL'.format(self.user),
		'r1': '0',
		'txtcusttype': '',
		'txtfrmday': from_date.split('-')[2],
		'txtfrmmonth': from_date.split('-')[1],
		'txtfrmyear': from_date.split('-')[0],
		'txttoday': to_date.split('-')[2],
		'txttomonth': to_date.split('-')[1],
		'txttoyear': to_date.split('-')[0],
		'r2': 'EXCEL'
		}

		invoices_data_response = s.post(
			'https://sales.hpcl.co.in/bportal/lpg/lpginvoicenew.jsp',
			data=invoice_req_dict
		).text

		if mode == 'raw':
			return invoices_data_response

		soup = BeautifulSoup(invoices_data_response)
		headings = [i.text.strip() for i in soup.findAll(id='Headings')[0].findAll('tr')[0].findAll('td')]

		invoices_data_map = []

		for row in soup.findAll(id='Headings')[1].findAll('tr')[:-1]:
			data_row_dict = {headings[index]: td.text.strip() for index, td in enumerate(row.findAll('td'))}

			# if empty return is ignored
			if ignore_empty_return and float(data_row_dict['ShippedQuantity']) <= 0:
				continue

			invoices_data_map.append(data_row_dict)

		return {
		'txns': invoices_data_map,
		'total_price': float(soup.findAll(id='Headings')[1].findAll('tr')[-1].findAll('td')[12].text.replace(',', ''))
		}


class LoginError(Exception):
	def __init__(self, msg):
		self.msg = msg


class ServerBusy(Exception):
	pass


class HPCLAdapter(HTTPAdapter):
	def send(self, request, timeout=None, **kwargs):
		return super(HPCLAdapter, self).send(request, timeout=3.05, **kwargs)