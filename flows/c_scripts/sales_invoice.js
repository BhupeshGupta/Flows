var css = (function () {/*
   .salesInvoiceReceivingImg {
		position: fixed;
		right: 0;
		width: 120px;
		height: inherit;
		border: 1px solid #ccc;
		padding: 5px;
		top: 40%;
	}

	.salesInvoiceReceivingImg img {
		width: 100%;
	}
	.salesInvoiceReceivingImg p{
	   text-align: center;
	}

	@media screen and (max-width: 767px) {
		.salesInvoiceReceivingImg {
			width: 80px;
			top: 210px;
		}
	 }
*/}).toString().match(/[^]*\/\*([^]*)\*\/\}$/)[1];

$('body').append( $('<style>' + css + '</style>') );


function content_url(url) {
	url = url.split("proxy/alfresco/api/node/");
	url[1].replace("/", "://");
	url = url[0] + 'page/site/receivings/document-details?nodeRef=' + url[1];
	url = url.split("/content/thumbnails/imgpreview");
	url = url[0];
	console.log(url);
	return url;
}


frappe.ui.form.on_change("Sales Invoice", "refresh", function (frm) {

	console.log('Sales Invoice Refresh Event');

	var doc = frm.doc;
	var map_html_string = '';
	if (doc.receiving_file) {
		map_html_string +=
			'<a target="_blank" href="' + content_url(doc.receiving_file) + '">'+
               '<img src="' + doc.receiving_file + '"/>';
            '</a>';
	}

	if (map_html_string) {
		$(frm.fields_dict['receiving_image'].wrapper).html('<div class="salesInvoiceReceivingImg">' + map_html_string + '</div>');
	} else {
		$(frm.fields_dict['receiving_image'].wrapper).html('');
	}
});
