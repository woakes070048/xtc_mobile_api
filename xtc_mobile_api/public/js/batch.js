frappe.ui.form.on('Batch', {
    refresh: (frm) => {
        if (!frm.is_new()) {
            frm.add_custom_button(__("Label Print"), () => {
                frappe.db.get_single_value('XTC Settings', 'url_for_label_print')
                    .then(url_for_label_print => {
                        frappe.db.get_list('Item Barcode', {
                            fields: ['barcode'],
                            filters: {
                                barcode_type: 'EAN',
                                'parent': frm.doc.item
                            }
                        }).then(records => {
                            console.log(records);
                            if (records.length > 0) {
                                let ean_code = records[0].barcode
                                // http://192.168.3.16/label.php?U=https://www.xtc-gelato.org/combQR.php?I=[Item Name]&E=[EAN Code]&B=[Batch number]&D=[Best Before Date]&P=[Production Date]
                                let company_url = 'https://www.xtc-gelato.org/combQR.php'
                                let encoded_print_url = encodeURIComponent(
                                    company_url + "?I=" + frm.doc.item_name + "&E=" + ean_code + "&B=" + frm.doc.name + "&D="
                                 + frm.doc.expiry_date + "&P="
                                 + frm.doc.manufacturing_date
                                 )
                                let print_url = url_for_label_print + "?U=" + encoded_print_url
                                console.log(print_url);
                                window.open(print_url, '_blank');
                            }
                        })
                    })
            });
        }
    }
})