# Copyright (c) 2013, Arun Logistics and Contributors
# See license.txt

import frappe
import unittest

test_records = frappe.get_test_records('Field Officer')

class TestFieldOfficer(unittest.TestCase):
	pass
