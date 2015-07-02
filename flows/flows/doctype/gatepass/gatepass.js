frappe.provide("erpnext.flows");

cur_frm.add_fetch('vehicle', 'driver', 'driver');

erpnext.flows.GatepassController = frappe.ui.form.Controller.extend({
	onload:function () {
		this.setup_queries();
	},

	set_plant_query:function (field) {
		if (this.frm.fields_dict[field]) {
			this.frm.set_query(field, function () {
				return {
					filters:{'supplier_type':'Gas Plant'}
				}
			});
		}
	},

	set_pump_query:function (field) {
		if (this.frm.fields_dict[field]) {
			this.frm.set_query(field, function () {
				return {
					filters:{'supplier_type':'Fuel Pump'}
				}
			});
		}
	},

	setup_queries:function () {
		this.set_plant_query("plant");
		this.set_pump_query("fuel_pump");

		this.frm.set_query("indent", function (doc, cdt, cdn) {
			frappe.model.validate_missing(doc, "gatepass_type");
			frappe.model.validate_missing(doc, "vehicle");
			frappe.model.validate_missing(doc, "id");
			return {
				query:"flows.flows.doctype.gatepass.gatepass.get_indent_list",
				filters:{
					gatepass_type:doc.gatepass_type,
					vehicle:doc.vehicle,
					doc_id:doc.id
				}
			};
		});

	},


	fuel_pump:function (doc, cdt, cdn) {
		this.frm.set_df_property("fuel_quantity", "reqd", doc.fuel_pump != "");
		this.frm.set_df_property("fuel_slip_id", "reqd", doc.fuel_pump != "");
	},

	dispatch_destination:function (doc, cdt, cdn) {
		this.frm.set_df_property("route", "reqd", doc.dispatch_destination == "Plant");
	},

	indent:function (doc, cdt, cdn) {
		if (doc.indent) {
			frappe.model.map_current_doc({
				method:"flows.flows.doctype.indent.indent.make_gatepass",
				source_name:doc.indent
			});
		}
	}

});

$.extend(cur_frm.cscript, new erpnext.flows.GatepassController({frm:cur_frm}));