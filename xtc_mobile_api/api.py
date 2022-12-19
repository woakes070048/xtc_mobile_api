import frappe

def on_save_submit_quality_inspection(self,method):
    if self.submit_on_save_cf==1 and self.docstatus==0:
        self.submit()
        frappe.msgprint(msg='Quality Inspection is submitted.')