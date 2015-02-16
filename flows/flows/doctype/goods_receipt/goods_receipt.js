//cur_frm.add_fetch('item', 'item_name', 'item_name');
//cur_frm.add_fetch('item', 'description', 'description');
//cur_frm.add_fetch('gatepass', 'plant', 'plant');
//
//frappe.provide("erpnext.flows");
//
//erpnext.flows.GoodsReceiptController = frappe.ui.form.Controller.extend({
//    onload: function () {
//        this.setup_queries();
//    },
//
//    setup_queries: function () {
//        if (this.frm.fields_dict["delivered_from"]) {
//            this.frm.set_query("delivered_from", function () {
//                return{
//                    filters: [
//                        ["Gatepass", "docstatus", "<", "2"]
//                    ]
//                }
//            });
//        }
//
//        this.set_plant_query("plant");
//    }
//
//});
//
////$.extend(cur_frm.cscript, new erpnext.flows.GoodsReceiptController({frm: cur_frm}));