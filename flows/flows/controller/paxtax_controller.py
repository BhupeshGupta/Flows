import requests

from bs4 import BeautifulSoup


def login(c):
	request = c.get(
		"https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise",
		params={'_nfpb': 'true', '_nfls': 'false', '_pageLabel': 'login'}
	)
	captcha_img = c.get("https://www.pextax.com/PEXWAR/stickyImg")
	# Push image to decaptcha service
	response = requests.post('http://128.199.122.18:9000/', files={'image': ('pex.png', captcha_img.content)})
	# Extract captcha value
	ocr_value = response.json()['value'].strip()

	if ocr_value:
		payload = {
		'username': 'ICC00022873',
		'password': '6pN@COk7m',
		'answer': ocr_value
		}

		response = c.post(
			"https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise",
			params={'_nfpb': 'true', '_windowLabel': 'HeaderController_2'},
			data=payload,
			allow_redirects=False
		)

		return 'Set-Cookie' in response.headers

	return False


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

	print soup

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


session = requests.Session()
if login(session):
	total_forms = []

	rs = get_search_html(session, '2015-12-10', '2015-12-10')

	for i in [(i - 1) * 5 for i in xrange(rs['current_page'], rs['total_pages'])]:
		data = {'IccStatusSearchController_2netui_row': 'Table;{}'.format(i)} if i > 0 else {}
		rs = get_search_html(session, '2015-12-10', '2015-12-10', data)
		total_forms.extend(rs['date_list'])

	print(total_forms)

else:
	print('login failed')

# search_html = open('/tmp/pex_search', mode='r').read()

# https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise?_nfpb=true&_windowLabel=IccStatusSearchController_2
# &IccStatusSearchController_2_actionOverride=%2Fcom%2Fpex%2Fportal%2FsearchFormStatus%2Fcontroller%2Fanchor
# &IccStatusSearchController_2refNo=18210301497748


#
# detail_html = open('/tmp/pex_detail', mode='r').read()
#
#
# def scrape_acknowledgement_page(page):
# soup = BeautifulSoup(page, 'lxml')
#
# base_table = soup.find("table", {"frmtable"})
# 	goods_table = soup.find("table", {'id': 'tableId'})
# 	vehicle_table = soup.findAll("table", {"frmtable"})[4]
#
# 	return {
# 		'acknowledgement_no': base_table('tr')[0]('td')[1].text.strip(),
# 		'icc_name': base_table('tr')[0]('td')[3].text.strip(),
# 		'import_export': base_table('tr')[1]('td')[1].text.strip(),
# 		'date_of_issue': base_table('tr')[1]('td')[3].text.strip(),
# 		'consigner_tin_no': base_table('tr')[2]('td')[1].text.strip(),
# 		'consigner_name': base_table('tr')[2]('td')[3].text.strip(),
# 		'consigner_addr': base_table('tr')[3]('td')[1].text.strip(),
# 		'consignee_tin_no': base_table('tr')[6]('td')[1].text.strip(),
# 		'consignee_name': base_table('tr')[6]('td')[3].text.strip(),
# 		'nature_of_txn': base_table('tr')[18]('td')[1].text.strip(),
# 		'item_code': goods_table('tr')[0]('td')[1].text.strip(),
# 		'item_name': goods_table('tr')[0]('td')[2].text.strip(),
# 		'invoice_no': goods_table('tr')[0]('td')[4].text.strip(),
# 		'invoice_date': goods_table('tr')[0]('td')[6].text.strip(),
# 		'invoice_qty': goods_table('tr')[0]('td')[8].text.strip(),
# 		'invoice_amt': goods_table('tr')[0]('td')[10].text.strip(),
# 		'freight_amt': goods_table('tr')[0]('td')[12].text.strip(),
# 		'total_amt': goods_table('tr')[0]('td')[14].text.strip(),
# 		'total_amt_in_words': goods_table('tr')[0]('td')[16].text.strip(),
# 		'vehicle_number': vehicle_table('tr')[1]('td')[1].text.strip(),
# 		'gr_date': vehicle_table('tr')[4]('td')[3].text.strip()
# 	}
#

# print json.dumps(scrape_acknowledgement_page(detail_html), indent=2)








