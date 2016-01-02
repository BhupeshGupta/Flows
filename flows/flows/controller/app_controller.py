import frappe
import json
from flows.stdlogger import root

@frappe.whitelist()
def create_gr(data):
	def create_hash(gr):
		return '#'.join(str(x) for x in [
			gr.goods_receipt_number,
			gr.customer,
			gr.item_delivered,
			gr.delivered_quantity if gr.delivered_quantity else '',
			gr.item_received,
			gr.received_quantity if gr.received_quantity else '',
		])
	def wrap_response(doc):
		return {
			'data': doc
		}

	doc = frappe._dict(json.loads(data))

	pk = 'goods_receipt_number' if doc.goods_receipt_number else None
	# pk = 'deduplicacy_id' if not pk and doc.deduplicacy_id else None

	root.debug("Pk: {}".format(pk))

	if pk:
		existing_gr = frappe.db.sql("""
		SELECT * FROM `tabGoods Receipt`
		WHERE {pk} = '{value}'
		AND docstatus = 1
		""".format(pk=pk, value=doc[pk]), as_dict=True)

		if existing_gr:
			root.debug("Existing hash {}".format(create_hash(existing_gr[0])))
			root.debug("New hash {}".format(create_hash(doc)))
			if create_hash(existing_gr[0]) == create_hash(doc):
				return wrap_response(existing_gr[0])
			else:
				frappe.throw("Please check voucher number."
							 "Seems like another voucher is already entered with this voucher id.")

	doc.update({'doctype': 'Goods Receipt'})

	gr = frappe.get_doc(doc)
	gr.save()

	return wrap_response(gr.as_dict())