$(document).on('startup', function () {

    var navbar = $('.collapse')[0];
    var form = $(navbar).find('form');

    var default_transaction_date = frappe.ui.form.make_control({
        parent: form,
        df: {
            fieldtype: "Date",
            options: [],
            default: "Today",
            fieldname: "default_transaction_date"
        },
        only_input: true
    });

    default_transaction_date.refresh();
    $(default_transaction_date.input).css({
        "margin-top": "5px",
        "margin-left": "10px",
        "height": "24px",
        "border-radius": "10px",
        "background-color": "#ddd",
        "max-width": "220px",
        "min-width": "100px",
        "font-size": "85%",
        "padding": "2px 6px"
    });

    frappe.ui.toolbar.transaction_date_default = default_transaction_date;

    var super_get_default_value = frappe.model.get_default_value;

    $.extend(frappe.model, {
        get_default_value: function (df, doc, parent_doc) {
            if (df["fieldtype"] == "Date" && df["options"] == "TransactionDate") {
                var date = frappe.ui.toolbar.transaction_date_default.get_parsed_value();
                if (date == "") {
                    return dateutil.get_today();
                }
                return date;
            }
            return super_get_default_value(df, doc, parent_doc);
        }
    });


    $(document).keydown("meta+a ctrl+a", function (e) {
        var route = frappe.get_route();
        if (route[0] == 'Form') {
            frappe.set_route("Form", route[1], frappe.model.make_new_doc_and_get_name(route[1]))
        }
        return false;
    });

    $(document).bind('keydown', function (e) {
        if (cur_dialog && cur_dialog.primary_action && e.which == 89) {
            cur_dialog.primary_action();
        }
    });

});