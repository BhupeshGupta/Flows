from requests import Session
import shutil


def login(c):
	request = c.get("https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise?_nfpb=true&_nfls=false&_pageLabel=login")

	print request.text

	response = c.get("https://www.pextax.com/PEXWAR/stickyImg", stream=True)
	with open('/tmp/pexcap.png', 'wb') as out_file:
		shutil.copyfileobj(response.raw, out_file)
	del response

	# payload = {
	# 	'username': 'ICC00022873',
	# 	'password': '6pN@COk7m',
	# }

	# response = c.post(
	# 	"https://www.pextax.com/PEXWAR/appmanager/pexportal/PunjabExcise?_nfpb=true&_windowLabel=HeaderController_2",
	# 	data=payload).text
	#
	# print(response)


session = Session()
login(session)