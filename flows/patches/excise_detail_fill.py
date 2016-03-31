import requests
from bs4 import BeautifulSoup
import shutil
import json
import frappe

class CbecEasiestPortal:
	ACTIVE = 'ACTIVE'
	INVALID = 'INVALID'

	def __init__(self):
		self.headers = {
			# Accept all
			'Accept': '*/*',
			# Disable Gzip
			'Accept-Encoding': '',
			'Connection': 'keep-alive',
			'Host': 'cbec-easiest.gov.in',
			'Referer': 'https://cbec-easiest.gov.in/EST/AssesseeVerification.do',
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'
		}

		self.data_url = "https://cbec-easiest.gov.in/EST/AssesseeVerificationResult.do"
		self.captcha_url = "https://cbec-easiest.gov.in/EST/CaptchaFeedback"

		self.session = None
		self.captcha = ''

	def get_session(self):
		if not self.session:
			self.session = requests.session()
		return self.session

	def get_excise_info(self, excise_no):
		if not self.captcha:
			raise "Set Captcha First"

		session = self.get_session()

		content = session.post(self.data_url, data={
			'': '',
			'ask': 'getECCDetails',
			'submit': 'Get Details',
			'captchaText': self.captcha,
			'assesseeCode': excise_no

		}, headers=self.headers, verify=False).text

		success = ('validation error' not in content.lower())
		if success:
			rs = CbecEasiestPortal.__parse__(content)
			rs.update({'excise_no': excise_no})
			return rs

		return {'error': 'Unable to fetch data'}

	def init_session(self):
		session = self.get_session()

		response = session.get(self.captcha_url, headers=self.headers, verify=False, stream=True)
		with open('/tmp/excise.png', 'wb') as out_file:
			shutil.copyfileobj(response.raw, out_file)

		return '/tmp/excise.png'

	def set_captcha(self, captcha):
		self.captcha = captcha

	@classmethod
	def check_status(cls, data):
		if 'ECCDetailsValid' in data:
			if data['ECCDetailsValid'] == 'ACTIVE':
				return CbecEasiestPortal.ACTIVE
			if data['ECCDetailsValid'] == 'No records available for given Assessee Code':
				return CbecEasiestPortal.INVALID
		raise 'Unknown Excise Status'

	@classmethod
	def __parse__(cls, html_data):
		soup = BeautifulSoup(html_data, 'lxml')
		spans = soup.findAll('span')
		rs = {}
		for span in spans:
			rs[span['id'].strip()] = span.text.strip().replace('\n', '').replace('\t', '').replace('\r', '')
		return rs


def execute():
	portal = CbecEasiestPortal()
	portal.init_session()
	print "Captcha (see file `/tmp/excise.png`): "

	captcha = raw_input()
	portal.set_captcha(captcha)

	for customer in frappe.db.sql("""
	select ecc_number, name from `tabCustomer`
	where cenvat=1
	and enabled=1 and
	ifnull(ecc_number,'')!=''
	and (ifnull(excise_range_code,'')=''
	or ifnull(excise_division_code,'')='');
	""", as_dict=True):
		excise_info = portal.get_excise_info(customer.ecc_number.strip())
		frappe.db.sql("""
		update `tabCustomer` set
		ecc_number="{excise_no}",
		excise_commissionerate_code="{ECCDetailsCommCode}",
		excise_range_code="{ECCDetailsRangeCode}",
		excise_division_code="{ECCDetailsDivCode}"
		where name="{customer}"
		""".format(customer=customer.name, **excise_info))

		print(excise_info)

		frappe.db.commit()