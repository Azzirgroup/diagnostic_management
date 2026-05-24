"""Lab Workflow Session API — backs the single-page WorkflowWizard.

A Lab Workflow Session ties one guided run together (Patient → Order →
Collection → Results) and persists `current_step` + `draft_data` so a
half-finished workflow can be resumed. Mirrors the previous Genetest
WorkflowWizard, adapted to the ADMS (Marley-backed) doctypes.
"""

import json

import frappe

from diagnostic_management.api import orders as orders_api
from diagnostic_management.api.collection import resolve_order_samples


def _payload(doc) -> dict:
	"""Session dict + live order detail aggregated across ALL the session's orders.

	A session may span several Service Requests (one per ordered test), tracked
	in draft_data.orders. We merge their samples / lab tests / reports so the
	Collection and Results steps show everything, not just the first order.
	"""
	out = doc.as_dict()
	out["order_detail"] = None

	order_names = []
	try:
		dd = json.loads(doc.draft_data) if doc.draft_data else {}
		order_names = dd.get("orders") or []
	except Exception:
		order_names = []
	if not order_names and doc.service_request:
		order_names = [doc.service_request]
	order_names = [o for o in order_names if o and frappe.db.exists("Service Request", o)]
	if not order_names:
		return out

	samples, lab_tests, reports = [], [], []
	seen_s, seen_lt, seen_r = set(), set(), set()
	for o in order_names:
		try:
			d = orders_api.detail(o)
		except Exception:
			continue
		for s in d["samples"]:
			if s["name"] not in seen_s:
				seen_s.add(s["name"]); samples.append(s)
		for lt in d["lab_tests"]:
			if lt["name"] not in seen_lt:
				seen_lt.add(lt["name"]); lab_tests.append(lt)
		for r in d["reports"]:
			if r["name"] not in seen_r:
				seen_r.add(r["name"]); reports.append(r)

	out["order_detail"] = {
		"name": order_names[0],
		"orders": order_names,
		"samples": samples,
		"lab_tests": lab_tests,
		"reports": reports,
		"stage": orders_api._compute_stage(samples, lab_tests, reports),
		"timeline_steps": orders_api.TIMELINE_STEPS,
	}
	return out


@frappe.whitelist()
def create_session(patient: str | None = None) -> dict:
	"""Start a new workflow session (optionally pre-set the patient)."""
	doc = frappe.get_doc({
		"doctype": "Lab Workflow Session",
		"patient": patient or None,
		"status": "In Progress",
		"current_step": 1,
	}).insert(ignore_permissions=False)
	return _payload(doc)


@frappe.whitelist()
def get_session(name: str) -> dict:
	return _payload(frappe.get_doc("Lab Workflow Session", name))


@frappe.whitelist()
def save_session(
	name: str,
	current_step: int | None = None,
	patient: str | None = None,
	service_request: str | None = None,
	draft_data: dict | str | None = None,
	status: str | None = None,
) -> dict:
	"""Persist wizard progress and re-sync the sample child rows from the order."""
	doc = frappe.get_doc("Lab Workflow Session", name)
	if patient is not None:
		doc.patient = patient
	if service_request is not None:
		doc.service_request = service_request
	if current_step is not None:
		doc.current_step = int(current_step)
	if status is not None:
		doc.status = status
	if draft_data is not None:
		doc.draft_data = draft_data if isinstance(draft_data, str) else json.dumps(draft_data)

	if doc.service_request:
		samples = resolve_order_samples(doc.service_request)
		doc.set("samples", [])
		for s in samples:
			doc.append("samples", {
				"sample": s["name"],
				"sample_label": s.get("sample"),
				"workflow_status": s.get("workflow_status") or ("Collected" if s.get("collected_time") else "To Be Collected"),
			})

	doc.save(ignore_permissions=False)
	return _payload(doc)


@frappe.whitelist()
def complete_session(name: str) -> dict:
	doc = frappe.get_doc("Lab Workflow Session", name)
	doc.status = "Completed"
	doc.current_step = 4
	doc.save(ignore_permissions=False)
	return {"ok": True, "name": name, "status": "Completed"}


@frappe.whitelist()
def list_open(limit: int = 20) -> list[dict]:
	"""Open (Draft / In Progress) sessions, for the Workflow hub's resume list."""
	return frappe.get_all(
		"Lab Workflow Session",
		fields=["name", "patient", "patient_name", "status", "current_step", "service_request", "modified"],
		filters={"status": ["in", ["Draft", "In Progress"]]},
		order_by="modified desc",
		limit_page_length=int(limit),
	)
