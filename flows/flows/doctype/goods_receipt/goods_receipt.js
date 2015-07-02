frappe.provide("erpnext.flows");

erpnext.flows.GoodsReceiptController = frappe.ui.form.Controller.extend({
    onload: function () {
        this.setup_queries();
    },

	refresh:function (doc, dt, dn) {
		console.log(doc);
		if (doc.location_latitude && doc.location_longitude) {
			var map_html_string = "<img src='https://maps.googleapis.com/maps/api/staticmap?zoom=15&size=600x300&maptype=roadmap&markers=color:blue|"+doc.location_latitude+","+doc.location_longitude+"'/>";
			$(this.frm.fields_dict['map_html'].wrapper).html(map_html_string);
		}
	},

    setup_queries: function () {
        var me = this;
        this.frm.set_query("warehouse", function () {
            return {
                filters: [
                    ["Warehouse", "company", "=", me.frm.doc.company]
                ]
            }
        });
    }
});

$.extend(cur_frm.cscript, new erpnext.flows.GoodsReceiptController({frm: cur_frm}));