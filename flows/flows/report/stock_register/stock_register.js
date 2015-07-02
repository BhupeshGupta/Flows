frappe.query_reports["Stock Register"] = {
	"filters":[
		{
			"fieldname":"from_date",
			"label":__("From Date"),
			"fieldtype":"Date",
			"width":"80",
			"default":frappe.datetime.month_start(),
			"reqd":1
		},
		{
			"fieldname":"to_date",
			"label":__("To Date"),
			"fieldtype":"Date",
			"width":"80",
			"default":frappe.datetime.month_end(),
			"reqd":1
		},
		{
			"fieldname":"warehouse",
			"label":__("Warehouse"),
			"fieldtype":"Link",
			"options":"Warehouse",
			"reqd":1
		},
		{
			"fieldname":"item_code",
			"label":__("Item"),
			"fieldtype":"Link",
			"options":"Item",
			"reqd":1,
			"get_query":function () {
				return {
					filters:[
						["Item", "name", "like", "F%"]
					]
				}
			}
		},
		{
			"fieldname":"bifurcate",
			"label":__("Bifurcate"),
			"fieldtype":"Check",
			"options":"Item",
			default: 0
		}
	]
};
