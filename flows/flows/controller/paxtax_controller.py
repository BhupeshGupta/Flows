from requests import Session
import shutil
from subprocess import call

def login(c):
	request = c.get("https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise?_nfpb=true&_nfls=false&_pageLabel=login")

	response = c.get("https://www.pextax.com/PEXWAR/stickyImg", stream=True)
	with open('/tmp/pexcap.png', 'wb') as out_file:
		shutil.copyfileobj(response.raw, out_file)
	del response

	call(['/usr/bin/tesseract', '/tmp/pexcap.png', '/tmp/pexcap'])

	ocr_file = open('/tmp/pexcap.txt', mode='r')
	ocr_value = ocr_file.read()
	ocr_file.close()

	if ocr_value:

		payload = {
			'username': 'ICC00022873',
			'password': '6pN@COk7m',
			'answer': ocr_value
		}

		response = c.post(
			"https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise?_nfpb=true&_windowLabel=HeaderController_2",
			data=payload
		)

		return 'userdetail' in response.text




session = Session()
print login(session)