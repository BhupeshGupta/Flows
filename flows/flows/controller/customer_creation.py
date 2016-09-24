import frappe
from frappe.utils import today, cint
from flows.stdlogger import root
import json
import requests
import os

path = os.path.abspath(os.path.dirname(__file__))
path = path + '/json_profiles/profile.json'
profile = {}
root.debug(path)
with open(path, 'r') as config_file:
    profile = json.loads(config_file.read())



def create_temp_data(data):

    doc = data['customerData']
    doc.update({'doctype': 'Customer'})
    gr = frappe.get_doc(doc)
    gr.save(ignore_permissions='true')
    customer_data = gr.as_dict()
    primary_key = customer_data['name']
    root.debug(primary_key)

    # extract contact
    root.debug("extracting contact")
    doc = data['customerContact']
    doc.update({'customer':primary_key})
    doc.update({'doctype':'Contact'})
    gr = frappe.get_doc(doc)
    gr.save(ignore_permissions='true')
    root.debug("extrcatig customer aadrrress")

    doc = data['customerAddressData']
    doc.update({'doctype':'Address'})
    doc.update({'customer':primary_key})
    root.debug(doc)
    save = frappe.get_doc(doc)
    save.save(ignore_permissions='true')

    # attach a profile with the data
    root.debug("attachinga profile")
    profile['with_effect_from'] = today()
    profile['customer'] = primary_key
    doc = profile
    save = frappe.get_doc(doc)
    save.save(ignore_permissions='true')
    omc_data = save.as_dict()
    root.debug("returning some VALUES")
    root.debug(omc_data, primary_key)
    return omc_data, primary_key

@frappe.whitelist(allow_guest=True)
def serve_html(data):
    data = json.loads(data)
    omc_data, primary = create_temp_data(data)
    frappe.session.user = "Administrator"
    customer_registration_content = frappe.get_print_format('OMC Customer Registration', omc_data['name'] ,
                                            'Customer Registration')

    frappe.response['filecontent'] = customer_registration_content
    frappe.response['type'] = 'download'
    frappe.response['filename'] = "Customer Registration.doc"
    frappe.response['content_type'] = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    frappe.db.rollback()

@frappe.whitelist()
def approve(data):
    data = json.loads(data)
    omc_data, primary = create_temp_data(data)
    root.debug(omc_data, primary)
    return primary



