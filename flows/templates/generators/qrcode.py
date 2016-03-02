import json

import requests
from lxml import etree
import logging

SERVER_URL = 'http://192.168.1.139:8080/'
FILE_BASE_PATH = '/Sites/test-site/documentLibrary'
ATOM_URL = 'http://192.168.1.200:8080/alfresco/api/-default-/public/cmis/versions/1.1/atom'
USER = 'admin'
PASSWORD = 'CoolerMaster'

def process_batch_file(file_path):
	processes_rs = []
	with open(file_path, mode='r') as file:
		root = etree.XML(file.read())
		docs = root.xpath("/Batch/Documents/Document")
		for doc in docs:
			barcode = doc.xpath("DocumentLevelFields/DocumentLevelField[Name='Barcode']/Value")[0].text
			pdf_file = doc.xpath("MultiPagePdfFile")[0].text
			properties = json.loads(json.loads(requests.post('https://erp.arungas.com/', data={
				'cmd': 'flows.flows.controller.ephesoft_integration.get_meta',
				'doc': barcode
			}).content)['message'])

			# Map it to alfresco data type and push to alfresco server
			processes_rs.append((properties, pdf_file))
	return processes_rs


def upload_batch_to_alfresco(files):
	from cmislib import CmisClient

	def map_to_alfresco(prop):
		return {'ag:{}'.format(k.lower().replace(' ', '_')): str(v) for k, v in prop.iteritems()}

	client = CmisClient(ATOM_URL, USER, PASSWORD)
	repo = client.getDefaultRepository()
	folder = repo.getObjectByPath(FILE_BASE_PATH)

	for index, (_properties, upload_file_path) in enumerate(files):
		try:
			properties = map_to_alfresco(_properties)

			properties.update({'cmis:objectTypeId': 'D:ag:consignment_note'})

			upload_file = open(upload_file_path, 'rb')
			file_name = '{}.pdf'.format(properties['ag:consignment_name'])
			doc = folder.createDocument(file_name, properties, contentFile=upload_file)
			upload_file.close()

			print('File Uploaded ({} of {}) {}'.format(index + 1, len(files), properties))
		except Exception as e:
			logging.error("Failed to upload file {} \n caused by {}".format(properties, e))
			raise


files = process_batch_file('/Users/karan/Documents/finaldrop.xml')
print files
upload_batch_to_alfresco(files)




