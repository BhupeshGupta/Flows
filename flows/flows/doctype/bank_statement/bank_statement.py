# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
from cStringIO import StringIO
import datetime

import pandas as pd

from frappe.model.document import Document
import frappe
from flows.stdlogger import root
from frappe.utils import nowdate, flt
from frappe.utils.file_manager import get_uploaded_content

class BankStatement(Document):
	def save(self, ignore_permissions=None):
		if self.bank_statement_lines and not self.bank_statement_lines[0].name:
			for bank_statement_line in self.bank_statement_lines:
				bank_statement_line.name = bank_statement_line.bank_txn_id

		return super(BankStatement, self).save(ignore_permissions)


def compute_hash(bank_statement_line):
	return str(bank_statement_line.txn_date) + \
		   str(hash(''.join(
			   [
				   str(i) for i in [
				   bank_statement_line.txn_date,
				   bank_statement_line.description,
				   bank_statement_line.txn_amt,
				   bank_statement_line.cr_dr
			   ]
			   ]
		   )))


@frappe.whitelist()
def recon(bank_txn_id, voucher_id, account, ref):
	bank_txn = frappe.get_doc('Bank Statement Line', bank_txn_id)

	if bank_txn.gl_entry:
		frappe.throw("Bank Txn Already Linked To {}".format(bank_txn.gl_entry))

	if voucher_id:
		frappe.db.set_value("Journal Voucher", voucher_id, "clearance_date", bank_txn.txn_date)
		frappe.db.sql("""update `tabJournal Voucher` set clearance_date = %s, modified = %s
			where name=%s""", (bank_txn.txn_date, nowdate(), voucher_id))

	else:
		account_obj = frappe.get_doc('Account', account)

		# entries
		jv_doc_json = {
		"doctype": "Journal Voucher",
		"docstatus": 1,
		"posting_date": bank_txn.txn_date,
		"clearance_date": bank_txn.txn_date,
		"user_remark": ref,
		"voucher_type": "Bank Voucher",
		"series": "JV-",
		"cheque_no": bank_txn.description,
		"cheque_date": bank_txn.txn_date,
		"company": account_obj.company,
		"entries": [
			{
			"account": account,
			"debit": bank_txn.txn_amt if bank_txn.cr_dr == 'DR' else 0,
			"credit": bank_txn.txn_amt if bank_txn.cr_dr == 'CR' else 0,
			},
			{
			"account":
				frappe.db.sql("SELECT bank FROM `tabBank Statement` WHERE name = '{}'".format(bank_txn.parent))[0][0],
			"debit": bank_txn.txn_amt if bank_txn.cr_dr == 'CR' else 0,
			"credit": bank_txn.txn_amt if bank_txn.cr_dr == 'DR' else 0,
			}
		],
		}

		jv_doc = frappe.get_doc(jv_doc_json)
		jv_doc.save()

		voucher_id = jv_doc.name

	bank_txn.jv = voucher_id
	bank_txn.save()

	return 'Success'


@frappe.whitelist()
def get_recon_list(bank):
	feed = frappe.db.sql("""
	SELECT bank_txn_id,
	 txn_amt, txn_date,
	 description, cr_dr
	 FROM `tabBank Statement Line` WHERE ifnull(jv, '') = ''
	AND parent IN (SELECT name FROM `tabBank Statement` WHERE bank = "{}")
	""".format(bank), as_dict=True)

	rs_list = []
	for line in feed:
		amt_cond = '{}={}'.format('debit' if line.cr_dr == 'CR' else 'credit', line.txn_amt)

		rs = {}
		rs['bank_txn'] = line

		rs['match'] = frappe.db.sql("""
		SELECT voucher_no AS id,
		posting_date AS date,
		remarks AS ref,
		CASE
			WHEN credit > 0 THEN 'CR'
			ELSE 'DR'
		END AS cr_dr,
		against AS against_account,
		CASE
			WHEN credit > 0 THEN credit
			ELSE debit
		END AS amount
		FROM `tabGL Entry`
		WHERE account = '{bank}'
		AND voucher_no not in (select jv from `tabBank Statement Line`)
		AND {amt_cond}
		""".format(amt_cond=amt_cond, bank=bank), as_dict=True)

		rs_list.append(rs)

	return rs_list


@frappe.whitelist()
def upload_bank_statement():
	def get_data_from_file(dataframe, format):
		if format == 'J K Bank':
			return process_jk_format(dataframe)
		if format == 'SBI Bank':
			return process_sbi_format(dataframe)

	bs_doc = json.loads(frappe.form_dict['params'])
	fname, fcontent = get_uploaded_content()
	f = StringIO(fcontent)

	rows = get_data_from_file(f, bs_doc['format'])
	root.debug(rows)
	headers = rows[0]
	data = rows[1:]

	sanatize_header(headers)

	data_list = [frappe._dict(zip(headers, data_row)) for data_row in data]
	normalize_data(data_list)

	## Trick to assign diff ids for same params for two transactions
	hash_map = {}
	for data_row in data_list:
		hash = compute_hash(data_row)
		hash_map.setdefault(hash, [])
		hash_map[hash].append(data_row)

	bank_txn_with_ids = []
	for hash in hash_map.keys():
		for index, bank_txn in enumerate(hash_map[hash]):
			bank_txn.bank_txn_id = '@' + str(index) + hash
			bank_txn_with_ids.append(bank_txn)

	bank_txn_ids_str = '"{}"'.format('","'.join([x.bank_txn_id for x in bank_txn_with_ids]))
	existing_set = set([x[0] for x in frappe.db.sql("""
	SELECT name FROM `tabBank Statement Line` WHERE name IN ({})
	""".format(bank_txn_ids_str))])

	final_bank_txns = []

	for bank_txn in bank_txn_with_ids:
		if bank_txn.bank_txn_id not in existing_set:
			final_bank_txns.append(bank_txn)

	if len(final_bank_txns) == 0:
		return {}

	x = [x.txn_date for x in final_bank_txns]
	bs_doc.update({
	"doctype": "Bank Statement",
	'from_date': min(x),
	'to_date': max(x),
	'txn_count': len(final_bank_txns),
	'bank_statement_lines': final_bank_txns
	})

	bs = frappe.get_doc(bs_doc)
	bs.save()

	return bs


def normalize_data(data_list):
	for data in data_list:
		root.debug(data.txn_amt)
		data['txn_amt'] = float(str(data.txn_amt).replace(',', ''))


def sanatize_header(headers):
	return [x.replace('"', '').strip() for x in headers]


def process_jk_format(f):
	import re

	data_frame = pd.read_html(f)

	regex = re.compile("BY INST (\d+) : OUTWARD CLG. MICR")

	rows = []
	for index, row in data_frame[1].iterrows():
		rows.append(row)

	rs_final = [['txn_date', 'description', 'cheque_no', 'cr_dr', 'txn_amt']]
	rs_final.extend([list(x[2:7]) for x in rows[1:]])

	for rs in rs_final[1:]:
		# Format Time
		rs[0] = datetime.datetime.strptime(rs[0], "%d/%m/%Y").strftime('%Y-%m-%d')

		# Format cq no
		if str(rs[2]) == 'nan':
			rs[2] = ''

		if regex.search(rs[1]):
			m = regex.match(rs[1])
			rs[2] = m.groups()[0]

	return rs_final


def process_sbi_format(f):
	# Txn Date                                                     23/06/2015
	# Value Date                                                   23/06/2015
	# Description                                      TO TRANSFER-INB IOCL--
	# Ref No./Cheque No.    MOSAICMARKETINGCS06504702 TRANSF...
	# Branch Code                                                       99922
	# Debit                                                 100000.00
	# Credit

	rows = [['txn_date', 'description', 'cheque_no', 'cr_dr', 'txn_amt']]
	data_frame = pd.read_csv(f, sep='\t', skiprows=18)
	for row_obj in data_frame.iterrows():
		row = row_obj[1]

		root.debug(row)

		debit = row[5].strip()
		credit = row[6].strip()
		cr_dr = 'DR' if flt(debit) > 0 else 'CR'

		rows.append([
			row['Txn Date'],
			row['Description'],
			row['Ref No./Cheque No.'],
			cr_dr,
			debit if cr_dr == 'DR' else credit
		])

	for rs in rows[1:]:
		# Format Time
		rs[0] = datetime.datetime.strptime(rs[0], "%d/%m/%Y").strftime('%Y-%m-%d')
		rs[1] = rs[1].replace('/', '').strip()
		rs[2] = rs[2].replace('/', '').strip()

	return rows