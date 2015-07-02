cur_frm.fields_dict['master_name'].get_query = function(doc) {
	if (doc.master_type) {
		return {
			doctype: doc.master_type,
		}
	}
};