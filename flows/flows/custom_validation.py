import frappe
from frappe.utils import cint, today


def journal_voucher_autoname(doc, method=None, *args, **kwargs):
	doc.naming_series = doc.naming_series.strip()
	if doc.voucher_type == "Cash Receipt(CR)":
		doc.name = '{}CR-{}'.format(doc.naming_series, doc.id)


def journal_voucher_validate(doc, method=None, *args, **kwargs):
	if doc.voucher_type == "Cash Receipt(CR)":
		if not doc.id:
			frappe.throw("ID is required for cash receipt")
		elif doc.name and doc.id != doc.name.split("-")[2]:
			frappe.throw("Cannot change type to Cash Receipt(CR) or id after saving voucher")


def contact_validate_for_sms(doc, method=None, *args, **kwargs):
	if cint(doc.sms_optin) == 1:
		if "Quality Manager" not in frappe.get_user(frappe.session.user).get_roles():
			frappe.throw("Quality Manager can update sms opted in contacts")


def validate_imprest_account_gl_entry_date(doc, method=None, *args, **kwargs):
	if not doc:
		account = kwargs['account']
		posting_date = kwargs['posting_date']
	else:
		account = doc.account
		posting_date = doc.posting_date

	blocked = frappe.db.sql("""
	select a.name as blocked
	from `tabSingles` s, `tabAccount` a
	where a.name="{}"
	and a.account_type='Imprest'
	and s.doctype = 'Flow Settings'
	and s.field = 'imprest_closing_date'
	and s.value >= '{}'
	""".format(account, posting_date))

	if blocked:
		if frappe.session.user == "Administrator":
			frappe.msgprint("FYI. Date for entry in imprest is closed")
		else:
			frappe.throw("Date for entry in imprest is closed for amendment/posting")


def customer_onload(doc, method=None, *args, **kwargs):
	rs = []

	omcs = frappe.db.sql('select DISTINCT omc from `tabOMC Customer Registration` where customer="{}" and docstatus != 2'.format(doc.name))
	omcs = [x[0] for x in omcs]
	for omc in omcs:
		row = frappe.db.sql("""
		select *
		from `tabOMC Customer Registration`
		where customer="{}"
		and omc="{}"
		and docstatus != 2
		order by with_effect_from desc
		limit 1
		""".format(doc.name, omc), as_dict=True)[0]
		row.setdefault('plants', [])
		rs.append(row)

		plants = [x[0] for x in frappe.db.sql("""
		select DISTINCT plant
		from `tabCustomer Plant Variables`
		where customer="{}"
		and plant like "{}%"
		""".format(doc.name, omc))]


		for plant in plants:
			last_active_entry = frappe.db.sql("""
			select * from `tabCustomer Plant Variables`
			where with_effect_from <= "{with_effect_from}"
			and customer = "{customer}"
			and plant = "{plant}"
			and docstatus != 2 order by with_effect_from desc;
			""".format(with_effect_from=today(), customer=doc.name, plant=plant), as_dict=True)

			if last_active_entry:
				row['plants'].append(last_active_entry[0])

		passwd = frappe.db.sql(
			"""
			select a.password, a.username, a.name
				from `tabAccount` a
					join
				(
					select credit_account
					from `tabOMC Customer Registration Credit Account`
					where parent = "{}"
					and type = "{}"
				) l
			on l.credit_account = a.name
			""".format(row.name, row.default_credit_account), as_dict=True
		)

		if passwd:
			passwd = passwd[0]
			row['portal_password'] = passwd['password']
			row['credit_account'] = "{} ({})".format(passwd.name, passwd.username)

	doc.get("__onload").omc_customer_variables_list = rs


def validate_gst_number(doc, method=None, *args, **kwargs):
	address = doc.customer_address
	if address:
		gst_number = frappe.db.get_value("Address", address, 'gst_number')
		if gst_number and gst_number.strip():
			if gst_number[:2] == '03':
				return

			frappe.throw("Out of state GST billing not enabled yet.".format(doc.customer))
	frappe.throw("GST Number not found for customer {}. Can not raise invoice.".format(doc.customer))
