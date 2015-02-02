# Copyright (c) 2013, Arun Logistics and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

from flows import utils as flows_utils
from erpnext.stock.stock_ledger import make_sl_entries

from frappe.model.document import Document
from flows import utils as flow_utils


class Indent(Document):
    def process_material_according_to_indent(self):

        sl_entries = []

        stock_transfer_map = self.compute_items_to_be_moved_for_refill_and_return()

        self.transfer_stock_to_ba(sl_entries, stock_transfer_map)

        self.transfer_stock_to_bottling_plant(sl_entries, stock_transfer_map)

        stock_transfer_map = self.compute_items_to_be_moved_back_after_refill_and_oneway()

        self.transfer_stock_back_to_ba(sl_entries, stock_transfer_map)

        self.transfer_stock_back_to_logistics_partner(sl_entries, stock_transfer_map)

        make_sl_entries(sl_entries)

    def compute_items_to_be_moved_for_refill_and_return(self):
        map = {}

        for indent_item in self.indent:
            if indent_item.load_type == "Refill":
                item = indent_item.item.replace('F', 'E')
                map[item] = map.get(item, 0) + indent_item.qty

        # TODO: add return qty

        return map

    def compute_items_to_be_moved_back_after_refill_and_oneway(self):
        map = {}

        for indent_item in self.indent:
            if indent_item.load_type in ("Refill", "Oneway"):
                item = indent_item.item
                map[item] = map.get(item, 0) + indent_item.qty

        return map

    def transfer_stock_to_ba(self, sl_entries, stock_transfer_map):

        vehicle_warehouse_logistics_partner = flows_utils.get_or_create_vehicle_stock_account(
            self.vehicle, self.logistics_partner
        )

        vehicle_warehouse_indent_owner = flows_utils.get_or_create_vehicle_stock_account(
            self.vehicle, self.company
        )

        for item, qty in stock_transfer_map.iteritems():
            sl_entries.append(
                self.transfer_stock(
                    item, qty, vehicle_warehouse_logistics_partner,
                    vehicle_warehouse_indent_owner, process='Transfer'
                )
            )

        return sl_entries

    def transfer_stock_to_bottling_plant(self, sl_entries, stock_transfer_map):

        vehicle_warehouse_indent_owner = flows_utils.get_or_create_vehicle_stock_account(
            self.vehicle, self.company
        )

        bottling_plant_account = flow_utils.get_supplier_account(
            self.company, self.plant
        )

        for item, qty in stock_transfer_map.iteritems():
            sl_entries.append(
                self.transfer_stock(
                    item, qty, vehicle_warehouse_indent_owner,
                    bottling_plant_account, process='Transfer'
                )
            )

        return sl_entries


    def transfer_stock_back_to_ba(self, sl_entries, stock_transfer_map):

        vehicle_warehouse_ba = flows_utils.get_or_create_vehicle_stock_account(
            self.vehicle, self.company
        )

        bottling_plant_account = flow_utils.get_supplier_account(
            self.company, self.plant
        )

        for item, qty in stock_transfer_map.iteritems():
            sl_entries.append(
                self.transfer_stock(
                    item, qty, bottling_plant_account,
                    vehicle_warehouse_ba, process='Transfer'
                )
            )

        return sl_entries


    def transfer_stock_back_to_logistics_partner(self, sl_entries, stock_transfer_map):

        vehicle_warehouse_logistics_partner = flows_utils.get_or_create_vehicle_stock_account(
            self.vehicle, self.logistics_partner
        )

        vehicle_warehouse_ba = flows_utils.get_or_create_vehicle_stock_account(
            self.vehicle, self.company
        )

        for item, qty in stock_transfer_map.iteritems():
            sl_entries.append(
                self.transfer_stock(
                    item, qty, vehicle_warehouse_ba,
                    vehicle_warehouse_logistics_partner,
                    process='Transfer'
                )
            )

        return sl_entries

    def transfer_stock(self, item, item_quantity, from_warehouse, to_warehouse, process=''):
        conversion_sl_entries = []

        conversion_sl_entries.append(
            self.get_sl_entry({
                "item_code": item,
                "actual_qty": -1 * item_quantity,
                "warehouse": from_warehouse,
                "process": process
            })
        )
        conversion_sl_entries.append(
            self.get_sl_entry({
                "item_code": item,
                "actual_qty": 1 * item_quantity,
                "warehouse": to_warehouse,
                "process": process
            })
        )

        return conversion_sl_entries

