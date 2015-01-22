# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document


class Gatepass(Document):
    def autoname(self):

        self.name = 'GP#{}#{}'.format(
            str(self.vehicle).strip(),
            self.date
        )
