import frappe
from frappe import _
from frappe.utils import flt, getdate

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "registration_date",
            "label": _("Registration Date"),
            "fieldtype": "Date",
            "width": 110
        },
        {
            "fieldname": "internal_patient_number",
            "label": _("Internal Patient Unique Number"),
            "fieldtype": "Link",
            "options": "Patient",
            "width": 150
        },
        {
            "fieldname": "external_patient_number",
            "label": _("External Patient Number (Hosp/Insurance etc)"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "patient_name",
            "label": _("Patient Name"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "corporate_institution",
            "label": _("Corporate/Institution Name"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "cash_credit",
            "label": _("Cash/Credit"),
            "fieldtype": "Data",
            "width": 90
        },
        {
            "fieldname": "total_billed_amount",
            "label": _("Total Billed Amount"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "discount",
            "label": _("Discount"),
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "net_amount",
            "label": _("Net Amount"),
            "fieldtype": "Currency",
            "width": 110
        },
        {
            "fieldname": "amount_received",
            "label": _("Amount Received"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "refund",
            "label": _("Refund"),
            "fieldtype": "Currency",
            "width": 90
        },
        {
            "fieldname": "balance",
            "label": _("Balance"),
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "cash",
            "label": _("Cash"),
            "fieldtype": "Currency",
            "width": 90
        },
        {
            "fieldname": "card",
            "label": _("Card"),
            "fieldtype": "Currency",
            "width": 90
        },
        {
            "fieldname": "cheque",
            "label": _("Cheque"),
            "fieldtype": "Currency",
            "width": 90
        },
        {
            "fieldname": "mpesa",
            "label": _("Mpesa"),
            "fieldtype": "Currency",
            "width": 90
        },
        {
            "fieldname": "doctor_name",
            "label": _("Doctor Name/Institution"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "uid",
            "label": _("UID"),
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 140
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)

    invoices = frappe.db.sql("""
        SELECT
            si.posting_date,
            si.patient,
            si.patient_name,
            si.customer,
            si.grand_total,
            si.discount_amount,
            si.net_total,
            si.paid_amount,
            si.outstanding_amount,
            si.name
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1
        {conditions}
        ORDER BY si.posting_date DESC
    """.format(conditions=conditions), filters, as_dict=1)

    data = []

    for inv in invoices:
        # Get patient external ID (use uid field if available)
        external_id = ""
        if inv.patient:
            # Just use the patient name as internal ID, external would need custom field
            external_id = ""

        # Determine Cash/Credit
        cash_credit = "Cash"
        corporate_name = ""
        if inv.customer:
            customer_group = frappe.db.get_value("Customer", inv.customer, "customer_group")
            if customer_group in ["Corporate", "Insurance", "Institution", "Hospital"]:
                cash_credit = "Credit"
                corporate_name = inv.customer

        # Get payment breakdowns
        cash_amt, card_amt, cheque_amt, mpesa_amt = get_payment_breakdown(inv.name)

        # Get referring doctor
        doctor_name = ""
        if inv.patient:
            lab_test = frappe.db.get_value("Lab Test", {"patient": inv.patient}, "practitioner")
            if lab_test:
                doctor_name = lab_test

        data.append({
            "registration_date": inv.posting_date,
            "internal_patient_number": inv.patient,
            "external_patient_number": external_id,
            "patient_name": inv.patient_name,
            "corporate_institution": corporate_name,
            "cash_credit": cash_credit,
            "total_billed_amount": flt(inv.grand_total),
            "discount": flt(inv.discount_amount),
            "net_amount": flt(inv.net_total),
            "amount_received": flt(inv.paid_amount),
            "refund": 0,
            "balance": flt(inv.outstanding_amount),
            "cash": cash_amt,
            "card": card_amt,
            "cheque": cheque_amt,
            "mpesa": mpesa_amt,
            "doctor_name": doctor_name,
            "uid": inv.name
        })

    return data

def get_payment_breakdown(invoice_name):
    cash = card = cheque = mpesa = 0

    payments = frappe.db.sql("""
        SELECT pe.paid_amount, pe.mode_of_payment
        FROM `tabPayment Entry` pe
        INNER JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
        WHERE per.reference_name = %s
        AND per.reference_doctype = 'Sales Invoice'
        AND pe.docstatus = 1
    """, invoice_name, as_dict=1)

    for p in payments:
        mode = (p.mode_of_payment or "").lower()
        amount = flt(p.paid_amount)

        if "cash" in mode:
            cash += amount
        elif "card" in mode or "credit" in mode or "debit" in mode:
            card += amount
        elif "cheque" in mode or "check" in mode:
            cheque += amount
        elif "mpesa" in mode or "mobile" in mode:
            mpesa += amount
        else:
            cash += amount

    return cash, card, cheque, mpesa

def get_conditions(filters):
    conditions = ""

    if filters.get("from_date"):
        conditions += " AND si.posting_date >= %(from_date)s"

    if filters.get("to_date"):
        conditions += " AND si.posting_date <= %(to_date)s"

    if filters.get("patient"):
        conditions += " AND si.patient = %(patient)s"

    if filters.get("customer"):
        conditions += " AND si.customer = %(customer)s"

    if filters.get("company"):
        conditions += " AND si.company = %(company)s"

    # Branch (Accounting Dimension auto-stamped on Sales Invoice — see
    # diagnostic_management/finance/stamp.py). Lets the Director filter
    # this report per branch (UMC / PMC / ...) or run consolidated.
    if filters.get("branch"):
        conditions += " AND si.branch = %(branch)s"

    return conditions
