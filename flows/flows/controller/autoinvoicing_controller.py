import frappe
from frappe.utils import today, cint
from flows.stdlogger import root

def save_and_submit_invoices():
	for invoice in frappe.db.sql("""
	SELECT iitm.parent as indent, iitm.name AS indent_item, iitm.cross_sold, omctxn.document_no, omctxn.date, omctxn.debit
	FROM `tabIndent Item` iitm LEFT JOIN `tabOMC Transactions` omctxn
	ON iitm.invoice_reference = omctxn.document_no
	WHERE ifnull(iitm.invoice_reference, '') != ''
	AND iitm.name NOT IN (
		SELECT ifnull(indent_item, '')
		FROM `tabIndent Invoice`
		WHERE docstatus != 2
	)
	AND iitm.docstatus != 2
	""", as_dict=True):

		docstatus = frappe.db.get_value("Indent", invoice.indent, 'docstatus')
		if cint(docstatus) == 0:
			indent = frappe.get_doc("Indent", invoice.indent)
			indent.docstatus = 1
			indent.workflow_state = indent.state = 'Processed'
			indent.save()

		__create_and_save_invoice__({
		'invoice_number': invoice.document_no,
		'transaction_date': invoice.date,
		'posting_date': today(),
		'actual_amount': invoice.debit,
		'indent_item': invoice.indent_item,
		'cross_sold': invoice.cross_sold
		})


def __create_and_save_invoice__(data_dict):
	doc_dict = {
	'doctype': 'Indent Invoice',
	'indent_linked': 1,
	}
	doc_dict.update(data_dict)
	doc = frappe.get_doc(doc_dict)

	doc.save()
	try:
		doc.submit()
	except Exception as e:
		root.error(e)
