"""Collection-step API for the WorkflowWizard's Collection component.

Ports the genetest Step3Collection surface onto ADMS / Marley Sample
Collection: session sample list (with department barcodes, linked lab tests
and the collected/received/processed timeline), bulk collect, per-sample
status updates, fast-track, and per-department barcode generation.
"""

import json

import frappe
from frappe.utils import now_datetime

from diagnostic_management.api.collection import STATUS_ORDER, resolve_order_samples


def _session_orders(session_id: str) -> list[str]:
	orders = []
	row = frappe.db.get_value("Lab Workflow Session", session_id, ["service_request", "draft_data"], as_dict=True) or {}
	try:
		dd = json.loads(row.get("draft_data") or "{}")
		orders = dd.get("orders") or []
	except Exception:
		orders = []
	if not orders and row.get("service_request"):
		orders = [row["service_request"]]
	return [o for o in orders if o and frappe.db.exists("Service Request", o)]


def _sample_payload(name: str) -> dict:
	sc = frappe.get_doc("Sample Collection", name)
	status = sc.get("workflow_status") or ("Collected" if sc.get("collected_time") else "To Be Collected")
	lab_tests = frappe.get_all(
		"Lab Test",
		filters={"sample": name},
		fields=["name", "template", "status", "department"],
	)
	return {
		"name": sc.name,
		"sample_id": sc.name,
		"sample_type": sc.get("sample"),
		"status": status,
		"is_urgent": sc.get("is_urgent") or 0,
		"patient": sc.get("patient"),
		"patient_name": sc.get("patient_name"),
		"collection_datetime": sc.get("collected_time"),
		"received_datetime": sc.get("received_datetime"),
		"processed_datetime": sc.get("processed_datetime"),
		"department_barcodes": [
			{
				"barcode_id": r.barcode_id,
				"department": r.department,
				"department_name": r.department_name or r.department,
				"generated_datetime": r.generated_datetime,
				"is_primary": r.is_primary,
			}
			for r in (sc.get("department_barcodes") or [])
		],
		"lab_tests": [
			{
				"lab_test": lt.name,
				"lab_test_name": lt.template,
				"template": lt.template,
				"department": lt.department,
				"status": lt.status,
			}
			for lt in lab_tests
		],
	}


@frappe.whitelist()
def get_session_lab_samples(session_id: str) -> dict:
	names = []
	for o in _session_orders(session_id):
		for s in resolve_order_samples(o):
			if s["name"] not in names:
				names.append(s["name"])
	return {"samples": [_sample_payload(n) for n in names]}


def _stamp(doc, new_status: str) -> None:
	now = now_datetime()
	fns = {df.fieldname for df in doc.meta.fields}
	doc.workflow_status = new_status
	if new_status not in ("To Be Collected", "Rejected"):
		if "collected_time" in fns and not doc.get("collected_time"):
			doc.collected_time = now
			if "collected_by" in fns and not doc.get("collected_by"):
				doc.collected_by = frappe.session.user
		if "status" in fns:
			doc.status = "Collected"
	if new_status == "Received" and "received_datetime" in fns and not doc.get("received_datetime"):
		doc.received_datetime = now
	if new_status in ("In Processing", "Tested", "Stored") and "processed_datetime" in fns and not doc.get("processed_datetime"):
		doc.processed_datetime = now


@frappe.whitelist()
def update_lab_sample_status(sample_name: str, new_status: str, is_urgent: int = 0) -> dict:
	if new_status not in (*STATUS_ORDER, "Rejected", "Disposed"):
		frappe.throw(f"Invalid status: {new_status}")
	doc = frappe.get_doc("Sample Collection", sample_name)
	_stamp(doc, new_status)
	if "is_urgent" in {df.fieldname for df in doc.meta.fields}:
		doc.is_urgent = 1 if int(is_urgent or 0) else 0
	doc.save(ignore_permissions=False)
	return {
		"success": True,
		"new_status": new_status,
		"collection_datetime": str(doc.get("collected_time") or ""),
		"received_datetime": str(doc.get("received_datetime") or ""),
		"processed_datetime": str(doc.get("processed_datetime") or ""),
	}


@frappe.whitelist()
def set_sample_urgent(sample_name: str, is_urgent: int = 0) -> dict:
	"""Persist just the urgent flag on a sample (no status/timestamp change), so
	toggling Urgent in the Collection step takes effect immediately."""
	if "is_urgent" not in {df.fieldname for df in frappe.get_meta("Sample Collection").fields}:
		return {"success": False}
	frappe.db.set_value("Sample Collection", sample_name, "is_urgent", 1 if int(is_urgent or 0) else 0, update_modified=False)
	return {"success": True, "sample_name": sample_name, "is_urgent": 1 if int(is_urgent or 0) else 0}


@frappe.whitelist()
def collect_lab_samples(session_id: str | None = None, samples_data: list | str | None = None) -> dict:
	data = json.loads(samples_data) if isinstance(samples_data, str) else (samples_data or [])
	n = 0
	for row in data:
		try:
			update_lab_sample_status(row.get("sample_name"), "Collected", row.get("is_urgent") or 0)
			n += 1
		except Exception:
			frappe.log_error(title=f"collect_lab_samples: failed {row.get('sample_name')}")
	return {"success": True, "message": f"{n} sample(s) collected", "count": n}


@frappe.whitelist()
def update_sample_processing_status(session_id=None, sample_name=None, status=None, data=None) -> dict:
	"""Fast-track / processing transition. `status` is the target (e.g. Tested)."""
	doc = frappe.get_doc("Sample Collection", sample_name)
	# Fast-track stamps the skipped received/processed times too.
	if "received_datetime" in {df.fieldname for df in doc.meta.fields} and not doc.get("received_datetime"):
		doc.received_datetime = now_datetime()
	_stamp(doc, status or "Tested")
	doc.save(ignore_permissions=False)
	return {
		"success": True,
		"new_status": status or "Tested",
		"received_datetime": str(doc.get("received_datetime") or ""),
		"processed_datetime": str(doc.get("processed_datetime") or ""),
	}


@frappe.whitelist()
def add_department_barcode(sample_name: str, department: str) -> dict:
	doc = frappe.get_doc("Sample Collection", sample_name)
	if any(r.department == department for r in (doc.get("department_barcodes") or [])):
		frappe.throw(f"A barcode for {department} already exists")
	abbr = "".join(c for c in (department or "DEP") if c.isalnum())[:4].upper() or "DEP"
	idx = len(doc.get("department_barcodes") or []) + 1
	barcode_id = f"{sample_name}-{abbr}-{idx:02d}"
	doc.append("department_barcodes", {
		"barcode_id": barcode_id,
		"department": department,
		"department_name": department,
		"generated_datetime": now_datetime(),
		"generated_by": frappe.session.user,
		"is_primary": 1 if idx == 1 else 0,
	})
	doc.save(ignore_permissions=False)
	return {"success": True, "barcode_id": barcode_id}


@frappe.whitelist()
def get_medical_departments() -> list[str]:
	try:
		return [d.name for d in frappe.get_all("Medical Department", fields=["name"], order_by="name")]
	except Exception:
		return []
