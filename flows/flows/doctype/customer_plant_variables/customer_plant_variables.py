# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document


class CustomerPlantVariables(Document):
    def autoname(self):
        self.name = '{}#{}#{}'.format(
            str(self.customer).strip(),
            str(self.plant).strip(),
            self.with_effect_from
        )
