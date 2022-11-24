frappe.ui.form.on('Batch', {
	refresh: (frm) => {
		if(!frm.is_new()) {
			frm.add_custom_button(__("Label Print"), () => {
                frappe.db.get_single_value('XTC Settings', 'url_for_label_print')
                .then(url_for_label_print => {
                    // http://192.168.3.16/label.php?U=https://www.xtc-gelato.org/combQR.php?I=[Item Name]&E=[EAN Code]&B=[Batch number]&D=[Best Before Date]&P=[Production Date]

                    let company_url=encodeURI('https://www.xtc-gelato.org/combQR.php')
                    let ean_code='EAN-13'
                    let print_url=url_for_label_print+"?U="+company_url+"?I="+frm.doc.item_name+"&E="+ ean_code+"&B="+frm.doc.name+"&D="+frm.doc.expiry_date+"&P="+frm.doc.manufacturing_date
                    console.log(print_url);
                    window.open(print_url, '_blank');
                })
            
			});
		}        
    }
})