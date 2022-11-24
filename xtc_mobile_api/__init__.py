
from __future__ import unicode_literals
from fileinput import filename

import frappe
from frappe.desk.query_report import run as run_report
from frappe.utils.print_format import download_multi_pdf
from itertools import groupby
import io
from PyPDF2 import PdfFileWriter
from frappe.utils.print_format import read_multi_pdf
from frappe.utils import cint, get_site_url, get_url
import json
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.contacts.doctype.address.address import get_company_address
from erpnext.stock.doctype.item.item import get_item_defaults
from frappe.utils import   cstr, flt
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from frappe.utils.pdf import get_pdf
from frappe.desk.form.utils import get_pdf_link
from frappe.model.mapper import map_doc

__version__ = "0.0.1"

@frappe.whitelist(allow_guest=True)
def get_order_summary(**args):
    data = frappe.db.sql(
        """ SELECT
                COUNT(DISTINCT tso.customer) as clients,
                SUM(tsoi.qty) as pieces
            FROM
                `tabSales Order` as tso
            inner join `tabSales Order Item` as tsoi 
            on
                tso.name = tsoi.parent
            WHERE
                tso.docstatus = 1
                and tso.status != 'Closed'
                and tso.status != 'On Hold'                
                and tso.per_delivered < 100""",
        as_dict=True,
    )
    return {"result": data}

@frappe.whitelist(allow_guest=True)
def get_order_list(**args):
    data = frappe.db.sql(
        """SELECT
            tso.name as so_no,
            tso.customer_name as client,
            tso.delivery_date as delivery_date,
            IFNULL(tso.picker_cf,'') as picker
        FROM
            `tabSales Order` as tso
        WHERE
            tso.docstatus = 1
            and tso.status != 'Closed'
            and tso.status != 'On Hold'
            and tso.per_delivered < 100""",
        as_dict=True,
    )
    return {"result": data}

@frappe.whitelist(allow_guest=True)
def get_order_details(**args):
    args["so_no"] = args.get("so_no")
    picker=args.get("picker")
    print('picker',picker,args["so_no"])
    if picker:
        frappe.db.set_value('Sales Order', args["so_no"], 'picker_cf', picker)
        frappe.db.commit()
    so_details = frappe.db.sql(
        """
            SELECT
                tso.name as so_no,
                tso.customer_name as client,
                tso.picker_cf as picker,
                tsoi.name as so_line_no,
                tsoi.item_code ,
                tsoi.item_name ,
                tsoi.qty
            FROM
                `tabSales Order` as tso
            inner join `tabSales Order Item` as tsoi
            on tso.name=tsoi.parent
            where
                tso.name = %(so_no)s
    """,
        args,
        as_dict=True,debug=False
    )    
    for so in so_details:
        batch_details=get_batch_details_based_on_itemcode(item_code=so.item_code)
        so.update(frappe._dict({"batch_details":batch_details.get("result") or ""}))
    return {"result": so_details }


@frappe.whitelist(allow_guest=True)
def get_batch_details_based_on_so(**args):
    args["so_no"] = args.get("so_no")
    # args["item_code"] = args.get("item_code")
    args["picker_warehouse"] = frappe.db.get_single_value('XTC Settings', 'picker_warehouse')

    # from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import execute
    # default_company=frappe.defaults.get_user_default("Company")
    # year_start_date = frappe.defaults.get_global_default("year_start_date")
    # # getdate(year.year_start_date)
    # today=frappe.utils.today()
    # data = execute({'company': default_company, 'from_date': year_start_date, 'to_date': today, 'item_code': args.get("item_code")})
    data = frappe.db.sql(
        """
select
    `tabBatch`.item as item_code,
    `tabBatch`.batch_id,
    DATEDIFF(STR_TO_DATE(`tabBatch`.expiry_date, '%%Y-%%m-%%d'),CURDATE()) AS days_to_expire,
    (
    SELECT
        value
    FROM
        `tabSingles`
    where
        doctype = 'XTC Settings'
        and field = 'alert_before_days' ) as alert_before_days,
     sum(`tabStock Ledger Entry`.actual_qty) as batch_qty
from
    `tabBatch`
join `tabStock Ledger Entry` ignore index (item_code,
    warehouse)
        on
    (`tabBatch`.batch_id = `tabStock Ledger Entry`.batch_no )
where
    `tabStock Ledger Entry`.item_code in (select tsoi.item_code from `tabSales Order Item` as tsoi where tsoi.parent=%(so_no)s)
    and `tabStock Ledger Entry`.warehouse = %(picker_warehouse)s
    and `tabStock Ledger Entry`.is_cancelled = 0
group by
    batch_id
order by
    `tabBatch`.expiry_date ASC,
    `tabBatch`.creation ASC
    """,
        args,
        as_dict=True,
    )    
    return {"result": data}

@frappe.whitelist(allow_guest=True)
def get_batch_details_based_on_itemcode(**args):

    args["item_code"] = args.get("item_code")
    args["picker_warehouse"] = frappe.db.get_single_value('XTC Settings', 'picker_warehouse')

    # from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import execute
    # default_company=frappe.defaults.get_user_default("Company")
    # year_start_date = frappe.defaults.get_global_default("year_start_date")
    # # getdate(year.year_start_date)
    # today=frappe.utils.today()
    # data = execute({'company': default_company, 'from_date': year_start_date, 'to_date': today, 'item_code': args.get("item_code")})
    data = frappe.db.sql(
        """
select
    `tabBatch`.item as item_code,
    `tabBatch`.batch_id,
    DATEDIFF(STR_TO_DATE(`tabBatch`.expiry_date, '%%Y-%%m-%%d'),CURDATE()) AS days_to_expire,
    (
    SELECT
        value
    FROM
        `tabSingles`
    where
        doctype = 'XTC Settings'
        and field = 'alert_before_days' ) as alert_before_days,
     sum(`tabStock Ledger Entry`.actual_qty) as batch_qty
from
    `tabBatch`
join `tabStock Ledger Entry` ignore index (item_code,
    warehouse)
        on
    (`tabBatch`.batch_id = `tabStock Ledger Entry`.batch_no )
where
    `tabStock Ledger Entry`.item_code = %(item_code)s
    and `tabStock Ledger Entry`.warehouse = %(picker_warehouse)s
    and `tabStock Ledger Entry`.is_cancelled = 0
group by
    batch_id
order by
    `tabBatch`.expiry_date ASC,
    `tabBatch`.creation ASC
    """,
        args,
        as_dict=True,
    )    
    return {"result": data}



@frappe.whitelist(allow_guest=True)
def create_dn_based_on_picked_details(*args,**kwargs):
    so=frappe.form_dict.get("message").get("result")
    if len(so)<1:
        return {"result": "error: no picked items present"}
    warehouse=frappe.db.get_single_value('XTC Settings', 'picker_warehouse')
    source_name=so[0].get("so_no")
    # dn=make_delivery_note(source_name)

    sales_order=frappe.get_doc("Sales Order",source_name)
    # dn=frappe.new_doc('Delivery Note')
    table_map= {
        "Sales Order": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
        "Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "add_if_empty": True},
        "Sales Team": {"doctype": "Sales Team",	"field_map": {
            "sales_person": "sales_person",
            "contact_no": "contact_no",
            "allocated_percentage": "allocated_percentage",
            "allocated_amount":"allocated_amount",
            "commission_rate":"commission_rate",
            "incentives":"incentives"}, "add_if_empty": True},
    }
    # table_map={"doctype": dn.doctype}
    # x=map_doc(sales_order, dn, table_map)
    dn = get_mapped_doc("Sales Order", source_name, table_map, target_doc=None)
    dn.customer=so[0].get("client")
    dn.set_warehouse=warehouse
    dn.items=[]
    for s in so:
        print('s',s)
        row=dn.append("items",{})
        row.item_code=s.get("item_code")
        row.qty=s.get("picked_qty")
        row.batch_no=s.get("picked_batch")
        row.against_sales_order=s.get("so_no")
        row.so_detail=s.get("so_line_no")
        row.warehouse=warehouse
    # # cost center
    dn.cost_center=sales_order.cost_center   
    # so_cost_center=frappe.db.get_value("Project", sales_order.project, "cost_center")
    # item_defaults=get_item_defaults( dn.items[0].item_code, sales_order.company)
    # item_group_defaults=get_item_group_defaults( dn.items[0].item_code, sales_order.company)
    # print(so_cost_center,'2',item_defaults,'3',item_group_defaults)
    # dn.cost_center=( so_cost_center or item_defaults.get("buying_cost_center") or item_group_defaults.get("buying_cost_center") )
    # print(so_cost_center , item_defaults.get("buying_cost_center") , item_group_defaults.get("buying_cost_center"))
    dn.run_method("set_missing_values")
    dn.run_method("set_po_nos")
    dn.run_method("calculate_taxes_and_totals")
    if sales_order.company_address:
        dn.update({"company_address": sales_order.company_address})
    else:
        # set company address
        dn.update(get_company_address(dn.company))

    if dn.company_address:
        dn.update(get_fetch_values("Delivery Note", "company_address", dn.company_address))    

    dn.set_onload("ignore_price_list", True)
    dn.save(ignore_permissions=True)
    dn.submit()
    url=get_deliverynote_pdf(dn.name)
    return {"result": 
        {"delivery_note": dn.name,
         "delivery_pdf_url":url
        }
    }

        


    
# def make_delivery_note1(source_name, target_doc=None, skip_item_mapping=False):
#     def set_missing_values(source, target):
#         target.run_method("set_missing_values")
#         target.run_method("set_po_nos")
#         target.run_method("calculate_taxes_and_totals")

#         if source.company_address:
#             target.update({"company_address": source.company_address})
#         else:
#             # set company address
#             target.update(get_company_address(target.company))

#         if target.company_address:
#             target.update(get_fetch_values("Delivery Note", "company_address", target.company_address))

    # def update_item(source, target, source_parent):

    #     target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
    #     target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
    #     target.qty = flt(source.qty) - flt(source.delivered_qty)

    #     item = get_item_defaults(target.item_code, source_parent.company)
    #     item_group = get_item_group_defaults(target.item_code, source_parent.company)

    #     if item:
    #         target.cost_center = (
    #             frappe.db.get_value("Project", source_parent.project, "cost_center")
    #             or item.get("buying_cost_center")
    #             or item_group.get("buying_cost_center")
            # )

    # mapper = {
    #     "Sales Order": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
    #     "Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "add_if_empty": True},
    #     "Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
    # }

    # if not skip_item_mapping:

    #     def condition(doc):
    #         # make_mapped_doc sets js `args` into `frappe.flags.args`
    #         if frappe.flags.args and frappe.flags.args.delivery_dates:
    #             if cstr(doc.delivery_date) not in frappe.flags.args.delivery_dates:
    #                 return False
    #         return abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier != 1

    #     mapper["Sales Order Item"] = {
    #         "doctype": "Delivery Note Item",
    #         "field_map": {
    #             "rate": "rate",
    #             "name": "so_detail",
    #             "parent": "against_sales_order",
    #         },
    #         "postprocess": update_item,
    #         "condition": condition,
    #     }

    # target_doc = get_mapped_doc("Sales Order", source_name, mapper, target_doc, set_missing_values)

    # target_doc.set_onload("ignore_price_list", True)

    # return target_doc  

@frappe.whitelist(allow_guest=True)
def get_deliverynote_pdf(docname):
    format=get_default_print_format("Delivery Note")
    pdf_link=get_pdf_link('Delivery Note',docname,format,no_letterhead=0)
    return "{}{}".format(get_url(), pdf_link)   



def get_default_print_format(doctype):
    return (
        frappe.db.get_value(
            "Property Setter",
            dict(property="default_print_format", doc_type=doctype),
            "value",
        )
        or frappe.get_doc("DocType", doctype).get("default_print_format")
        or 
        "Standard"
    )  