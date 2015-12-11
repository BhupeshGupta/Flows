import requests

def login(c):
	request = c.get("https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise?_nfpb=true&_nfls=false&_pageLabel=login")
	captcha_img = c.get("https://www.pextax.com/PEXWAR/stickyImg")
	# Push image to decaptcha service
	response = requests.post('http://128.199.122.18:9000/', files={'image': captcha_img.content})
	# Extract captcha value
	ocr_value = response.json()['value'].strip()

	if ocr_value:
		payload = {
			'username': 'ICC00022873',
			'password': '6pN@COk7m',
			'answer': ocr_value
		}

		response = c.post(
			"https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise?_nfpb=true&_windowLabel=HeaderController_2",
			data=payload,
			allow_redirects=False
		)

		print response.text

		return 'Set-Cookie' in response.headers

	return False

session = requests.Session()
print login(session)