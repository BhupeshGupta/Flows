# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import collections

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint
from frappe import msgprint


form_grid_templates = {
"entries": "templates/form_grid/ind_inv_receiving_details.html"
}

state_map = {
'ok': 0,
'missing values': 1,
'unchecked': 2
}


class IndentInvoiceReceiving(Document):
	fname = 'entries'

	def get_invoices(self):
		self.set('entries', [])

		if self.indent:
			alert_map = collections.OrderedDict()
			alert_map['Total'] = frappe.db.sql("""
			SELECT count(name)
			FROM `tabIndent Item`
			WHERE parent = '{}'""".format(self.indent))[0][0]
			alert_map['Submitted'] = 0
			alert_map['Draft'] = 0

		for invoice in frappe.db.sql("""
		SELECT * FROM
		`tabIndent Invoice` WHERE
		docstatus != 2 {conditions}
		""".format(conditions=self.get_conditions()), as_dict=True):

			if invoice.docstatus == 1:
				if self.indent:
					alert_map['Submitted'] += 1

				invoice_item = self.append('entries', {})

				invoice_item.indent_invoice = invoice.name

				invoice_item.invoice_date = invoice.transaction_date
				invoice_item.amount = flt(invoice.actual_amount)
				invoice_item.customer = invoice.customer
				invoice_item.item = invoice.item
				invoice_item.qty = invoice.qty

				invoice_item.handling = invoice.handling_charges
				invoice_item.cst = invoice.cst
				invoice_item.excise = invoice.excise

				invoice_item.cenvat = invoice.cenvat
				invoice_item.printable = invoice.printable
				invoice_item.workflow_state = invoice.workflow_state
				invoice_item.transportation_invoice = invoice.transportation_invoice

			else:
				if self.indent:
					alert_map['Draft'] += 1

		if self.indent:
			alert_map['Pending'] = alert_map['Total'] - alert_map['Submitted'] - alert_map['Draft']
			self.alerts = '\n'.join(['{}: {}'.format(k, v) for k, v in alert_map.items()])

	def get_conditions(self):
		conditions = []

		if hasattr(self, 'names') and self.names:
			conditions.append('name in ({})'.format(
				','.join(['"{}"'.format(x) for x in self.names])
			))
		elif self.indent:
			conditions.append('indent = "{}"'.format(self.indent))

		return " {} {}".format("and" if conditions else "", " and ".join(conditions))

	def update_invoices(self):
		vouchers = []
		for d in self.get('entries'):
			doc = frappe.get_doc("Indent Invoice", d.indent_invoice)
			invoice_current_state = state_map[
				frappe.db.get_value(
					"Indent Invoice",
					filters={'name': d.indent_invoice},
					fieldname='workflow_state'
				).lower()
			]

			if invoice_current_state >= 2:
				doc.handling_charges = d.handling
				doc.cst = d.cst
			if invoice_current_state >= 1:
				doc.excise = d.excise

				vouchers.append(d.indent_invoice)

			doc.populate_reports()

			if cint(d.checked) == 1:
				doc.update_status()

			doc.ignore_permissions = 1
			doc.ignore_validate_update_after_submit = 1
			doc.save()

		self.names = [x.indent_invoice for x in self.get('entries')]
		self.get_invoices()


		if vouchers:
			msgprint("Data Updated in: {0}".format(", ".join(vouchers)))
		else:
			msgprint("No Data Update")
