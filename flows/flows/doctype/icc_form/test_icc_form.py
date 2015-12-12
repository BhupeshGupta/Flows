# Copyright (c) 2013, Arun Logistics and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

test_records = frappe.get_test_records('ICC Form')

class TestICCForm(unittest.TestCase):
	pass
