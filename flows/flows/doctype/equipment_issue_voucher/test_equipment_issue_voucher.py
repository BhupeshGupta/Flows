# Copyright (c) 2013, Arun Logistics and Contributors
# See license.txt

import unittest

import frappe


test_records = frappe.get_test_records('Equipment Issue Voucher')


class TestEquipmentIssueVoucher(unittest.TestCase):
	pass
