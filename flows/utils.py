import frappe
from erpnext.accounts.party import get_party_account


def get_or_create_vehicle_stock_account(vehicle_name, stock_owner_company_name):
    try:
        warehouse_name = transport_vehicle_to_warehouse_name(vehicle_name, stock_owner_company_name)
        warehouse_account = frappe.get_doc("Warehouse", warehouse_name)
        return warehouse_account
    except frappe.DoesNotExistError as e:
        warehouse_account = frappe.get_doc(
            {
                "doctype": "Warehouse",
                "company": stock_owner_company_name,
                "warehouse_name": vehicle_name
            })
        warehouse_account.save()
        return warehouse_account


def transport_vehicle_to_warehouse_name(vehicle_name, stock_owner_company):
    stock_owner_company_abbr = frappe.db.get_value(
        "Company", stock_owner_company, "abbr")
    return '{} - {}'.format(vehicle_name, stock_owner_company_abbr.strip())


def get_or_create_customer_stock_account(customer_name, company_name_to_find_account_under):
    try:
        warehouse_name = customer_to_warehouse_account_name(customer_name, company_name_to_find_account_under)
        warehouse_account = frappe.get_doc("Warehouse", warehouse_name)
        return warehouse_account
    except frappe.DoesNotExistError as e:
        warehouse_account = frappe.get_doc(
            {
                "doctype": "Warehouse",
                "company": company_name_to_find_account_under,
                "warehouse_name": customer_name
            })
        warehouse_account.save()
        return warehouse_account


def customer_to_warehouse_account_name(customer, company_name_to_find_account_under):
    company_abbr = frappe.db.get_value(
        "Company", company_name_to_find_account_under, "abbr"
    )

    return '{} - {}'.format(customer, company_abbr)


def get_supplier_account(company, supplier):
    if ',' in supplier:
        supplier = supplier.split(',')[0].strip()

    get_party_account(company, supplier, "Supplier")