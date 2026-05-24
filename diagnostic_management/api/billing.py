"""Billing & invoicing endpoints — list, summary, detail, and the
order → invoice creation flow that ties orders to revenue.
"""

import frappe
from frappe.utils import flt, nowdate


@frappe.whitelist()
def queue(status: str | None = None, limit: int = 100) -> list[dict]:
	"""Active billing queue. Defaults to all open (Draft / unpaid)."""
	filters: dict = {}
	if status:
		filters["status"] = status
	else:
		filters["status"] = ["in", ["Draft", "Overdue", "Unpaid", "Partly Paid", "Submitted"]]
	return frappe.get_all(
		"Sales Invoice",
		fields=[
			"name", "customer", "customer_name", "grand_total", "outstanding_amount",
			"status", "posting_date", "due_date", "currency",
		],
		filters=filters,
		order_by="posting_date desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def for_patient(patient: str, limit: int = 50) -> list[dict]:
	fields = [
		"name", "customer", "customer_name", "grand_total", "outstanding_amount",
		"status", "posting_date", "due_date",
	]
	try:
		meta = frappe.get_meta("Sales Invoice")
		if any(df.fieldname == "patient" for df in meta.fields):
			return frappe.get_all(
				"Sales Invoice",
				fields=fields,
				filters={"patient": patient},
				order_by="posting_date desc",
				limit_page_length=int(limit),
			)
	except Exception:
		pass
	# Fallback: match by patient_name → customer_name
	patient_name = frappe.db.get_value("Patient", patient, "patient_name") or ""
	if not patient_name:
		return []
	return frappe.get_all(
		"Sales Invoice",
		fields=fields,
		filters={"customer_name": ["like", f"%{patient_name}%"]},
		order_by="posting_date desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def detail(name: str) -> dict:
	"""Full invoice payload for the SPA detail page."""
	if not name:
		frappe.throw("name is required")
	doc = frappe.get_doc("Sales Invoice", name)
	out = doc.as_dict()
	# Surface line items in a flat, SPA-friendly shape.
	out["items_list"] = [
		{
			"item_code": it.item_code,
			"item_name": it.item_name,
			"description": it.description,
			"qty": flt(it.qty),
			"rate": flt(it.rate),
			"amount": flt(it.amount),
			"uom": it.uom,
		}
		for it in (doc.get("items") or [])
	]
	# Pull payment entries that reference this invoice.
	try:
		out["payments"] = frappe.get_all(
			"Payment Entry Reference",
			fields=["parent", "allocated_amount", "outstanding_amount"],
			filters={"reference_name": name, "reference_doctype": "Sales Invoice", "docstatus": 1},
		)
	except Exception:
		out["payments"] = []
	return out


@frappe.whitelist()
def create_invoice_for_order(service_request: str, submit: int = 0) -> dict:
	"""Create a draft Sales Invoice from a submitted Service Request.

	Pulls the linked Lab Test Template (or Clinical Procedure Template) to
	derive the line item, sets the patient + customer, and posts in the
	default Company's default currency. With submit=1 the invoice is
	submitted (docstatus 0 → 1) in the same call.
	"""
	if not service_request:
		frappe.throw("service_request is required")
	sr = frappe.get_doc("Service Request", service_request)

	# Avoid duplicates — one invoice per Service Request unless cancelled.
	existing = frappe.db.get_value(
		"Sales Invoice Item",
		{"reference_dt": "Service Request", "reference_dn": service_request, "docstatus": ["!=", 2]},
		"parent",
	)
	if existing:
		return {"ok": True, "name": existing, "existing": True}

	# Map Marley Patient → ERPNext Customer (created on patient insert).
	customer = frappe.db.get_value("Patient", sr.patient, "customer") or sr.patient_name
	if not customer or not frappe.db.exists("Customer", customer):
		frappe.throw(f"No Customer linked to patient {sr.patient}")

	rate = _template_rate(sr.template_dt, sr.template_dn)
	company = sr.company or frappe.defaults.get_user_default("company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw("No Company configured on the site")

	doc = frappe.get_doc({
		"doctype": "Sales Invoice",
		"customer": customer,
		"company": company,
		"posting_date": nowdate(),
		"patient": sr.patient if _has_field("Sales Invoice", "patient") else None,
		"items": [{
			"item_code": _ensure_item_for_template(sr.template_dt, sr.template_dn),
			"qty": 1,
			"rate": rate,
			"description": sr.title or sr.template_dn,
			"reference_dt": "Service Request",
			"reference_dn": sr.name,
		}],
	}).insert(ignore_permissions=False)

	if int(submit or 0):
		try:
			doc.submit()
		except Exception:
			frappe.log_error(title=f"billing.create_invoice_for_order: submit failed for {doc.name}")
			raise

	return {"ok": True, "name": doc.name, "grand_total": flt(doc.grand_total), "docstatus": doc.docstatus}


@frappe.whitelist()
def create_invoice_for_tests(
	patient: str,
	items: list | str,
	service_requests: list | str | None = None,
	mode_of_payment: str | None = None,
	paid_amount: float | None = None,
	reference_no: str | None = None,
	submit: int = 1,
) -> dict:
	"""Create ONE Sales Invoice covering several ordered tests, with per-line
	quantity + discount, and optionally record a payment.

	`items`: list of {template_dt, template_dn, qty, discount_percentage, label}.
	`service_requests`: optional list (parallel to items) to link each line back
	to its order. With `paid_amount` > 0 a Payment Entry is recorded too.
	"""
	import json

	items = json.loads(items) if isinstance(items, str) else (items or [])
	srs = json.loads(service_requests) if isinstance(service_requests, str) else (service_requests or [])
	if not items:
		frappe.throw("No tests to invoice")

	customer = frappe.db.get_value("Patient", patient, "customer") or frappe.db.get_value("Patient", patient, "patient_name")
	if not customer or not frappe.db.exists("Customer", customer):
		frappe.throw(f"No Customer linked to patient {patient}")
	company = frappe.defaults.get_user_default("company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw("No Company configured on the site")

	inv = frappe.get_doc({"doctype": "Sales Invoice", "customer": customer, "company": company, "posting_date": nowdate()})
	if _has_field("Sales Invoice", "patient"):
		inv.patient = patient
	for i, it in enumerate(items):
		base = _template_rate(it.get("template_dt"), it.get("template_dn"))
		disc = flt(it.get("discount_percentage") or 0)
		row = {
			"item_code": _ensure_item_for_template(it.get("template_dt"), it.get("template_dn")),
			"qty": flt(it.get("qty") or 1),
			# Set price_list_rate + discount_percentage so ERPNext applies the
			# discount; rate is the resulting net (kept consistent).
			"price_list_rate": base,
			"discount_percentage": disc,
			"rate": base * (1 - disc / 100),
			"description": it.get("label") or it.get("template_dn"),
		}
		if srs and i < len(srs) and srs[i]:
			row["reference_dt"] = "Service Request"
			row["reference_dn"] = srs[i]
		inv.append("items", row)
	inv.insert(ignore_permissions=False)
	if int(submit or 0):
		inv.submit()

	payment = None
	if paid_amount and flt(paid_amount) > 0 and inv.docstatus == 1:
		try:
			payment = record_payment(inv.name, flt(paid_amount), mode_of_payment)
		except Exception as e:
			frappe.log_error(title="billing.create_invoice_for_tests: payment failed")
			payment = {"error": str(e)}

	return {
		"ok": True,
		"invoice": inv.name,
		"grand_total": flt(inv.grand_total),
		"outstanding": flt(inv.outstanding_amount),
		"docstatus": inv.docstatus,
		"payment": payment,
	}


@frappe.whitelist()
def record_payment(invoice: str, amount: float, mode_of_payment: str | None = None) -> dict:
	"""Record a payment against a submitted Sales Invoice.

	Creates and submits a Payment Entry; ERPNext updates the invoice's
	outstanding_amount automatically via the reference.
	"""
	inv = frappe.get_doc("Sales Invoice", invoice)
	if inv.docstatus != 1:
		frappe.throw("Invoice must be submitted before recording payment")

	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = "Receive"
	pe.party_type = "Customer"
	pe.party = inv.customer
	pe.company = inv.company
	pe.paid_from = frappe.db.get_value("Company", inv.company, "default_receivable_account")
	pe.paid_to = frappe.db.get_value("Company", inv.company, "default_cash_account") or frappe.db.get_value("Account", {"company": inv.company, "account_type": "Cash"}, "name")
	pe.paid_amount = flt(amount)
	pe.received_amount = flt(amount)
	pe.mode_of_payment = mode_of_payment or "Cash"
	pe.append("references", {
		"reference_doctype": "Sales Invoice",
		"reference_name": invoice,
		"total_amount": inv.grand_total,
		"outstanding_amount": inv.outstanding_amount,
		"allocated_amount": flt(amount),
	})
	pe.insert(ignore_permissions=False)
	pe.submit()
	return {"ok": True, "payment_entry": pe.name, "allocated": flt(amount)}


def _template_rate(template_dt: str | None, template_dn: str | None) -> float:
	if not template_dt or not template_dn:
		return 0
	if template_dt == "Lab Test Template":
		return flt(frappe.db.get_value("Lab Test Template", template_dn, "lab_test_rate") or 0)
	if template_dt == "Clinical Procedure Template":
		return flt(frappe.db.get_value("Clinical Procedure Template", template_dn, "rate") or 0)
	return 0


def _ensure_item_for_template(template_dt: str | None, template_dn: str | None) -> str:
	"""Return an Item code suitable for a Sales Invoice line.

	Marley Lab Test Template / Clinical Procedure Template both expose an
	auto-created `Item` named after the template via Healthcare Settings.
	Falls back to a generic "Diagnostic Service" item if the link is missing.
	"""
	if template_dt and template_dn:
		linked = frappe.db.get_value(template_dt, template_dn, "item")
		if linked and frappe.db.exists("Item", linked):
			return linked
	# Fall back: reuse the template name as an item if it exists already.
	if template_dn and frappe.db.exists("Item", template_dn):
		return template_dn
	# Last resort: a generic ad-hoc service item the lab can keep using.
	generic = "Diagnostic Service"
	if not frappe.db.exists("Item", generic):
		try:
			frappe.get_doc({
				"doctype": "Item",
				"item_code": generic,
				"item_name": generic,
				"item_group": "Services" if frappe.db.exists("Item Group", "Services") else None,
				"is_stock_item": 0,
				"include_item_in_manufacturing": 0,
				"stock_uom": "Nos",
			}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(title="billing._ensure_item_for_template: Diagnostic Service create failed")
	return generic


def _has_field(doctype: str, fieldname: str) -> bool:
	try:
		return any(df.fieldname == fieldname for df in frappe.get_meta(doctype).fields)
	except Exception:
		return False


@frappe.whitelist()
def summary() -> dict:
	"""Quick KPIs for the billing dashboard card."""
	def _agg(filters: dict) -> dict:
		try:
			rows = frappe.db.sql(
				"""
				SELECT COUNT(*) AS cnt, COALESCE(SUM(outstanding_amount),0) AS total
				FROM `tabSales Invoice`
				WHERE status IN %(statuses)s
				""",
				{"statuses": tuple(filters["statuses"])},
				as_dict=True,
			)
			r = rows[0] if rows else {}
			return {"count": int(r.get("cnt") or 0), "total": float(r.get("total") or 0)}
		except Exception:
			return {"count": 0, "total": 0}
	return {
		"draft": _agg({"statuses": ["Draft"]}),
		"unpaid": _agg({"statuses": ["Unpaid", "Partly Paid", "Overdue"]}),
		"paid": _agg({"statuses": ["Paid"]}),
	}
