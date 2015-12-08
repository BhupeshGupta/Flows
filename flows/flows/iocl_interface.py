import requests
from bs4 import BeautifulSoup
from flows.stdlogger import root
import json
from frappe.utils.data import date_diff, today

class IOCLPortal(object):
	@classmethod
	def parse_date(cls, date):
		return '-'.join(reversed(date.split('.')))

	def __init__(self, user, passwd, debug=False):
		self.user = user
		self.passwd = passwd
		self.debug = debug
		self.session = None

	def get_session(self):
		if not self.session:
			self.session = requests.Session()
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
			amt = float(row['Bill Amt'].replace(',', '').strip())
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

	def get_current_balance_as_on_date(self, mode='raw'):
		return self.transactions_since_yesterday(mode='dict')['current_balance']

def get_iocl_user_pass():
	return [{
		"customer": "Mosaic",
		"id": "605251",
		"pass": "605251",
	}]