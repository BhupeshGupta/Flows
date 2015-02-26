from setuptools import setup, find_packages

version = '0.0.1'

setup(
	name='flows',
	version=version,
	description='Implements custom workflows for Arun Logistics',
	author='Arun Logistics',
	author_email='bhupesh00gupta@gmail.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=("frappe",),
)
