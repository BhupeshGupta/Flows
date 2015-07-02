$(document).on('startup', function () {

	var navbar = $('.collapse')[0];
	var form = $(navbar).find('form');

	var default_transaction_date = frappe.ui.form.make_control({
		parent:form,
		df:{
			fieldtype:"Date",
			options:[],
			default:"Today",
			fieldname:"default_transaction_date"
		},
		only_input:true
	});

	default_transaction_date.refresh();
	$(default_transaction_date.input).css({
		"margin-top":"5px",
		"margin-left":"10px",
		"height":"24px",
		"border-radius":"10px",
		"background-color":"#ddd",
		"max-width":"220px",
		"min-width":"100px",
		"font-size":"85%",
		"padding":"2px 6px"
	});

	frappe.ui.toolbar.transaction_date_default = default_transaction_date;

	var super_get_default_value = frappe.model.get_default_value;

	$.extend(frappe.model, {
		get_default_value:function (df, doc, parent_doc) {
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


	$(document).keydown("meta+shift+a ctrl+shift+a", function (e) {
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

	$(document).keydown("meta+shift+s ctrl+shift+s", function (e) {
		e.preventDefault();
		if (cur_frm) {
			cur_frm.savesubmit();
		}
		return false;
	});


	var DocListViewOriginal = frappe.views.DocListView;


	frappe.ui.toolbar.MassPrintDialog = frappe.ui.toolbar.SelectorDialog.extend({

		init:function (execute) {
			this._super({
				title:__("Download PDF"),
				execute:execute
			});
		},

		make_dialog:function () {
			var fields = [
				{fieldtype:'Select', fieldname:'doctype', options:'Select...', label:__('Select Type')},
				{"fieldname":"no_letterhead", "label":__("Letterhead"), "fieldtype":"Check"},
				{fieldtype:'Button', label:'Go', fieldname:'go'}
			];

			this.dialog = new frappe.ui.Dialog({
				title:this.opts.title,
				fields:fields
			});

			if (this.opts.help) {
				$("<div class='help'>" + this.opts.help + "</div>").appendTo(this.dialog.body);
			}
		}
	});

	frappe.views.DocListView = DocListViewOriginal.extend({
		setup:function () {
			this.can_print = frappe.model.can_print(this.doctype);
			this._super();
		},
		init_minbar:function () {
			this._super();
			if (this.can_print) {
				this.appframe.add_icon_btn("2", 'icon-print', __('Print'),
					function () {
						var print_dialog = new frappe.ui.toolbar.MassPrintDialog(
							function () {

								var checked_items = frappe.pages[frappe.get_route()[0] + "/" + frappe.get_route()[1]].doclistview.get_checked_items();

								if (!checked_items) {
									return
								}

								checked_items = checked_items.map(function (obj) {
									return obj.name;
								});

								var name = '["' + checked_items.join('","') + '"]';
								var format = print_dialog.dialog.fields_dict.doctype.get_value();
								var no_letterhead = print_dialog.dialog.fields_dict.no_letterhead.get_parsed_value();
								if (no_letterhead == 0) {
									no_letterhead = 1;
								} else {
									no_letterhead = 0;
								}

								var w = window.open("/api/method/frappe.templates.pages.print.download_pdf?"
								+ "doctype=" + encodeURIComponent(frappe.get_route()[1])
								+ "&name=" + encodeURIComponent(name)
								+ "&format=" + encodeURIComponent(format)
								+ "&no_letterhead=" + no_letterhead);
								if (!w) {
									msgprint(__("Please enable pop-ups"));
									return;
								}
							});
						print_dialog.set_values(frappe.meta.get_print_formats(frappe.get_route()[1]));
						print_dialog.show();

					});
			}

			// Bulk Submit
			this.appframe.add_icon_btn("2", 'icon-thumbs-up', __('Submit'),
				function () {
					var checked_items = frappe.pages[frappe.get_route()[0] + "/" + frappe.get_route()[1]].doclistview.get_checked_items();
					if (!checked_items) {
						return
					}
					checked_items = checked_items.map(function (obj) {
						return obj.name;
					});
					frappe.confirm(__("Permanently Submit {0}?", [checked_items]), function () {
						console.log(checked_items);
						return frappe.call({
							method:'flows.flows.form.submit',
							type:"POST",
							args:{
								'doctype':frappe.get_route()[1],
								'name':'["' + checked_items.join('", "') + '"]'
							},
							no_spinner:false,
							callback:function (r) {
								if (r.message == "ok") {
									var view = frappe.pages[frappe.get_route()[0] + "/" + frappe.get_route()[1]].doclistview;
									view.dirty = true;
									view.refresh();
									msgprint(__("Submission Done."))
								}
							}
						});

					});
				});
		}
	});


});