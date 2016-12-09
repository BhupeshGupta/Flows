import frappe
from flows.stdlogger import root
from frappe.utils import today
from frappe.utils import flt


def submit_indents():
	# Query all indents in pending/drafted status having reconciled bills
	for indent in frappe.db.sql("""
		SELECT ind.name
		FROM `tabIndent Item` iitm LEFT JOIN `tabIndent` ind
			ON ind.name = iitm.parent
		WHERE ind.docstatus = 0
		GROUP BY ind.name
		HAVING count(iitm.name) - count(iitm.invoice_reference) = 0;
		""", as_dict=True
	):
		indent = frappe.get_doc("Indent", indent[0])
		indent.docstatus = 1
		indent.workflow_state = indent.state = 'Processed'
		indent.save()


def save_and_submit_invoices(doc, method=None, *args, **kwargs):
	# Get all indents against which there are no invoices entered (submitted or drafted) in te system by using the
	# previously reconciled Txns
	root.info("Indent On Submit Ran.")
	for invoice in frappe.db.sql("""
		SELECT iitm.parent as indent,
		iitm.name AS indent_item,
		iitm.cross_sold,
		omctxn.document_no,
		omctxn.date,
		omctxn.debit
		FROM `tabIndent Item` iitm RIGHT JOIN `tabOMC Transactions` omctxn
			ON iitm.invoice_reference = omctxn.document_no
		WHERE iitm.parent = '{}'
	""".format(doc.name), as_dict=True):

		try:

			__create_and_save_invoice__({
				'invoice_number': invoice.document_no,
				'transaction_date': invoice.date,
				'posting_date': today(),
				'actual_amount': invoice.debit,
				'indent_item': invoice.indent_item,
				'cross_sold': invoice.cross_sold
			})

			root.info("Invoice {} processed.".format(invoice.document_no))

		except Exception as e:
			root.error(invoice)
			root.error(e)


def __create_and_save_invoice__(data_dict):
	doc_dict = {
		'doctype': 'Indent Invoice',
		'indent_linked': 1,
	}
	doc_dict.update(data_dict)
	doc = frappe.get_doc(doc_dict)

	# Skip checks with OMC Transaction as we just drew information from there only
	doc.ignore_omc_validation = True

	doc.save()

	try:
		doc.submit()
	except Exception as e:
		doc = frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Log",
			"comment_doctype": "Indent Invoice",
			"comment_docname": doc.name,
			"comment": e,
			"comment_by": frappe.session.user
		})
		doc.insert(ignore_permissions=True)


def validate_invoice_number(doc, method=None, *args, **kwargs):
	if getattr(doc, 'ignore_omc_validation', False):
		return

	try:
		root.info("Running Hook Validation for invoice {}".format(doc.invoice_number))
		omc_txn = frappe.get_doc("OMC Transactions", {"document_no": doc.invoice_number})

		mismatch_fields = []

		if omc_txn.customer and omc_txn.customer != doc.customer:
			mismatch_fields.append('Customer')
		if omc_txn.item and omc_txn.item.replace('L', '') != doc.item.replace('L', ''):
			mismatch_fields.append('Item')
		if omc_txn.quantity and flt(omc_txn.quantity) != flt(doc.qty):
			mismatch_fields.append('Quantity')
		if omc_txn.date and omc_txn.date != doc.transaction_date:
			mismatch_fields.append('Invoice Date')
		if omc_txn.debit and flt(omc_txn.debit) != flt(doc.actual_amount):
			mismatch_fields.append('Amount')

		if mismatch_fields:
			error_msg = mismatch_fields[0]
			if len(mismatch_fields) > 1:
				error_msg = ', '.join(mismatch_fields[:-1])
				error_msg = '{} and {}'.format(error_msg, mismatch_fields[-1])
			frappe.throw("Error. Please check {} in invoice {}".format(error_msg, doc.invoice_number))
	except Exception as e:
		root.info("Exception in Hook Validation for invoice {}".format(doc.invoice_number))
		root.error(e)
		raise
