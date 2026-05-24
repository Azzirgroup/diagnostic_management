"""Billing-step API for the WorkflowWizard's Billing component.

Ports the surface the previous Genetest Step2Billing relied on, mapped onto
ADMS / Marley doctypes: customer + doctor lookups, the billable test list,
and the create-invoice / record-payment actions. Creating the invoice also
spins up the lab orders (Service Requests) so the pipeline runs.
"""

import json

import frappe
from frappe.utils import flt

from diagnostic_management.api import billing as billing_api
from diagnostic_management.api import orders as orders_api
from diagnostic_management.api.collection import resolve_order_samples


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_customer_groups() -> list[str]:
	try:
		return [g.name for g in frappe.get_all("Customer Group", filters={"is_group": 0}, order_by="name")]
	except Exception:
		return []


@frappe.whitelist()
def search_customers(search_term: str = "", customer_group: str | None = None, limit: int = 15) -> list[dict]:
	filters = {}
	if customer_group:
		filters["customer_group"] = customer_group
	q = (search_term or "").strip()
	or_filters = None
	if q:
		or_filters = [
			["customer_name", "like", f"%{q}%"],
			["name", "like", f"%{q}%"],
			["mobile_no", "like", f"%{q}%"],
		]
	try:
		return frappe.get_all(
			"Customer",
			fields=["name", "customer_name", "customer_group"],
			filters=filters,
			or_filters=or_filters,
			order_by="modified desc",
			limit_page_length=int(limit),
		)
	except Exception:
		return []


@frappe.whitelist()
def get_patient_billing_info(patient_id: str) -> dict:
	p = frappe.db.get_value(
		"Patient", patient_id, ["name", "patient_name", "customer", "sex"], as_dict=True
	) or {}
	customer = p.get("customer")
	cust_name = frappe.db.get_value("Customer", customer, "customer_name") if customer else None
	cust_group = frappe.db.get_value("Customer", customer, "customer_group") if customer else None
	return {
		"patient": p.get("name") or patient_id,
		"patient_name": p.get("patient_name"),
		"customer": customer or "",
		"customer_name": cust_name or p.get("patient_name") or "",
		"customer_group": cust_group or "",
		"patient_gender": p.get("sex") or "",
	}


@frappe.whitelist()
def get_lab_tests_for_billing(tests=None, patient_gender=None) -> list[dict]:
	"""Billable Lab Test Templates (+ imaging procedures) for the test table."""
	rows = []
	try:
		rows = frappe.get_all(
			"Lab Test Template",
			fields=["name", "lab_test_name", "lab_test_code", "department", "lab_test_rate", "sample", "lab_test_template_type"],
			filters={"disabled": 0} if _has_field("Lab Test Template", "disabled") else {},
			order_by="lab_test_name",
			limit_page_length=0,
		)
	except Exception:
		rows = []
	for r in rows:
		r["template_dt"] = "Lab Test Template"
	return rows


@frappe.whitelist()
def get_user_pos_profiles() -> list[dict]:
	try:
		return frappe.get_all("POS Profile", fields=["name"], order_by="name")
	except Exception:
		return []


@frappe.whitelist()
def check_pos_profile_shift(pos_profile: str | None = None) -> dict:
	# ADMS isn't POS-shift gated; report open so invoice creation isn't blocked.
	return {"has_open_shift": True}


@frappe.whitelist()
def get_modes_of_payment() -> list[str]:
	try:
		modes = [m.name for m in frappe.get_all("Mode of Payment", fields=["name"], order_by="name")]
		return modes or ["Cash"]
	except Exception:
		return ["Cash"]


@frappe.whitelist()
def search_doctors(search_term: str = "", limit: int = 10) -> list[dict]:
	q = (search_term or "").strip()
	or_filters = [["practitioner_name", "like", f"%{q}%"], ["name", "like", f"%{q}%"]] if q else None
	try:
		rows = frappe.get_all(
			"Healthcare Practitioner",
			fields=["name", "practitioner_name", "department"],
			or_filters=or_filters,
			order_by="practitioner_name",
			limit_page_length=int(limit),
		)
	except Exception:
		rows = []
	return [{"name": r["name"], "doctor_name": r.get("practitioner_name") or r["name"], "specialty": r.get("department")} for r in rows]


@frappe.whitelist()
def create_doctor(doctor_name: str) -> dict:
	doc = frappe.get_doc({"doctype": "Healthcare Practitioner", "first_name": doctor_name}).insert(ignore_permissions=True)
	return {"name": doc.name, "doctor_name": doc.practitioner_name or doc.name}


@frappe.whitelist()
def search_insurance_providers(search_term: str = "") -> list[dict]:
	return []


@frappe.whitelist()
def search_corporate_accounts(search_term: str = "") -> list[dict]:
	return []


# ---------------------------------------------------------------------------
# Invoice + payment
# ---------------------------------------------------------------------------

def _normalise_selected(selected_tests) -> list[dict]:
	"""Genetest sends each test as a str OR {lab_test_template, qty, discount_percentage}."""
	out = []
	for t in selected_tests or []:
		if isinstance(t, dict):
			out.append({
				"template_dn": t.get("lab_test_template") or t.get("template_dn"),
				"qty": flt(t.get("qty") or 1),
				"discount_percentage": flt(t.get("discount_percentage") or 0),
			})
		else:
			out.append({"template_dn": t, "qty": 1, "discount_percentage": 0})
	return [x for x in out if x["template_dn"]]


@frappe.whitelist()
def create_sales_invoice_for_tests(session_id: str | None = None, billing_data: dict | str | None = None) -> dict:
	"""Create the lab orders + one Sales Invoice (qty/discount) + optional payment.

	Returns {success, invoice_id, grand_total, payment_entry_id, orders}.
	"""
	bd = json.loads(billing_data) if isinstance(billing_data, str) else (billing_data or {})
	patient = None
	if session_id and frappe.db.exists("Lab Workflow Session", session_id):
		patient = frappe.db.get_value("Lab Workflow Session", session_id, "patient")
	if not patient:
		frappe.throw("No patient on the workflow session")

	tests = _normalise_selected(bd.get("selected_tests"))
	if not tests:
		frappe.throw("Select at least one test")

	# 1) Create one Service Request per test so the lab pipeline runs.
	res = orders_api.create_order(
		patient=patient,
		practitioner=bd.get("custom_doctor") or None,
		priority="Urgent" if bd.get("mark_urgent") else "Routine",
		tests=[{"template_dt": "Lab Test Template", "template_dn": t["template_dn"]} for t in tests],
		submit=1,
	)
	created_orders = res.get("orders") or []

	# 1b) Reset this workflow's samples to "To Be Collected". Marley reuses the
	# same specimen doc across orders for a patient + sample type, so a reused
	# tube can carry a prior workflow's terminal status (Tested/Stored) — which
	# would make Collection look already-done and let "Continue to Results"
	# appear before the user processes it. Start each fresh for this workflow.
	seen: set[str] = set()
	for o in created_orders:
		for s in resolve_order_samples(o):
			if s["name"] in seen:
				continue
			seen.add(s["name"])
			frappe.db.set_value(
				"Sample Collection",
				s["name"],
				{
					"workflow_status": "To Be Collected",
					"collected_time": None,
					"collected_by": None,
					"received_datetime": None,
					"processed_datetime": None,
					# Propagate the billing "Mark as Urgent" choice onto the sample
					# so Collection / Lab Sample / Results all show it as urgent.
					"is_urgent": 1 if bd.get("mark_urgent") else 0,
				},
				update_modified=False,
			)

	# 2) One Sales Invoice for the whole set, with qty + discount + optional payment.
	include_payment = bool(bd.get("include_payment"))
	inv = billing_api.create_invoice_for_tests(
		patient=patient,
		items=[{
			"template_dt": "Lab Test Template",
			"template_dn": t["template_dn"],
			"qty": t["qty"],
			"discount_percentage": t["discount_percentage"],
			"label": t["template_dn"],
		} for t in tests],
		service_requests=created_orders,
		mode_of_payment=bd.get("mode_of_payment") if include_payment else None,
		paid_amount=None,  # full payment handled via the dedicated payment form
		submit=1,
	)

	# 3) Link to the session.
	if session_id and frappe.db.exists("Lab Workflow Session", session_id):
		try:
			s = frappe.get_doc("Lab Workflow Session", session_id)
			s.service_request = created_orders[0] if created_orders else None
			s.draft_data = json.dumps({"invoice": inv["invoice"], "orders": created_orders})
			s.save(ignore_permissions=True)
		except Exception:
			frappe.log_error(title="billing_workflow: failed to link session")

	return {
		"success": True,
		"invoice_id": inv["invoice"],
		"grand_total": inv["grand_total"],
		"outstanding_amount": inv["outstanding"],
		"payment_entry_id": (inv.get("payment") or {}).get("payment_entry"),
		"orders": created_orders,
	}


@frappe.whitelist()
def get_invoice_outstanding(invoice_id: str) -> dict:
	row = frappe.db.get_value("Sales Invoice", invoice_id, ["grand_total", "outstanding_amount"], as_dict=True) or {}
	return {"grand_total": flt(row.get("grand_total")), "outstanding_amount": flt(row.get("outstanding_amount"))}


@frappe.whitelist()
def create_payment_entry_for_invoice(
	invoice_id: str,
	mode_of_payment: str,
	paid_amount: float,
	reference_no: str | None = None,
	reference_date: str | None = None,
) -> dict:
	out = frappe.db.get_value("Sales Invoice", invoice_id, "outstanding_amount")
	if flt(out) <= 0:
		return {"success": True, "already_paid": True, "paid_amount": 0}
	pe = billing_api.record_payment(invoice_id, flt(paid_amount), mode_of_payment)
	return {"success": True, "payment_entry_id": pe.get("payment_entry"), "paid_amount": flt(paid_amount)}


def _has_field(doctype: str, fieldname: str) -> bool:
	try:
		return any(df.fieldname == fieldname for df in frappe.get_meta(doctype).fields)
	except Exception:
		return False
