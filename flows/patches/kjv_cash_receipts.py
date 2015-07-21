from __future__ import unicode_literals

from __future__ import unicode_literals

import frappe
import frappe.defaults

from frappe.model.rename_doc import rename_doc


def execute():
	for cr in frappe.db.sql("SELECT name, id FROM `tabJournal Voucher` WHERE voucher_type = 'Cash Receipt(CR)'"
							"AND docstatus = 1", as_dict=True):
		rename_doc('Journal Voucher', cr.name, 'KJV-CR-{}'.format(cr.name.split('-')[0]), force=True)