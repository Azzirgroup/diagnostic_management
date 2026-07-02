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

	# Auto-create + link a Customer doc when the Patient has none. Without
	# this, the workflow billing UI shows the patient name in the Customer
	# box (a display fallback) but `customer` stays empty — so validation
	# says "No customer selected" and Customer Group can't auto-populate.
	# ERPNext Healthcare normally creates this on Patient.insert; restored /
	# legacy patients miss it. Idempotent: only creates when Patient.customer
	# is empty, and reuses any Customer whose name already matches.
	if not customer and (p.get("name") or patient_id):
		customer = _ensure_patient_customer(p.get("name") or patient_id, p.get("patient_name"))

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


def _ensure_patient_customer(patient_name: str, display_name: str | None) -> str | None:
	"""Create a Customer for the patient and stamp it onto Patient.customer.
	Returns the Customer.name (or None on failure). Defensive: never raises
	to the caller — a failure just leaves customer unlinked, the UI then
	prompts the user to search/pick one manually."""
	try:
		# Customer Group MUST be a leaf (is_group=0) — ERPNext rejects root
		# groups like "All Customer Groups". Try Selling Settings default,
		# then a global default, then prefer "Individual" if it exists, else
		# any leaf group we can find.
		default_group = (
			frappe.db.get_single_value("Selling Settings", "customer_group")
			or frappe.db.get_default("customer_group")
			or ""
		)
		if default_group:
			is_group = frappe.db.get_value("Customer Group", default_group, "is_group")
			if is_group is None or is_group:  # missing OR is a parent
				default_group = ""
		if not default_group:
			# Prefer "Individual" (the default ERPNext seed for individuals).
			if frappe.db.exists("Customer Group", {"customer_group_name": "Individual", "is_group": 0}):
				default_group = "Individual"
			else:
				# Fall back to any leaf customer group on this site.
				leaf = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
				if not leaf:
					return None  # site has no usable Customer Group at all
				default_group = leaf

		default_territory = frappe.db.get_default("territory") or "All Territories"
		if not frappe.db.exists("Territory", default_territory):
			default_territory = "All Territories"
		label = (display_name or patient_name).strip() or patient_name

		# Reuse a same-named Customer if one exists.
		existing = frappe.db.get_value("Customer", {"customer_name": label}, "name")
		cust_name = existing
		if not cust_name:
			doc = frappe.new_doc("Customer")
			doc.customer_name = label
			doc.customer_type = "Individual"
			doc.customer_group = default_group
			doc.territory = default_territory
			doc.insert(ignore_permissions=True)
			cust_name = doc.name

		frappe.db.set_value("Patient", patient_name, "customer", cust_name, update_modified=False)
		return cust_name
	except Exception:
		frappe.log_error(title=f"_ensure_patient_customer failed for {patient_name}")
		return None


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
	"""SPA sends each test as either a plain template_dn string OR a dict
	{lab_test_template, qty, discount_percentage, rate?}.

	`rate` is optional — it's an editable per-line override the user typed
	in the Billing step's Rate column. When present it overrides the
	template's `lab_test_rate` on the invoice line. We carry it through
	untouched here; billing.create_invoice_for_tests decides whether to
	use it (see the `override` check there).
	"""
	out = []
	for t in selected_tests or []:
		if isinstance(t, dict):
			row = {
				"template_dn": t.get("lab_test_template") or t.get("template_dn"),
				"qty": flt(t.get("qty") or 1),
				"discount_percentage": flt(t.get("discount_percentage") or 0),
			}
			# Preserve rate override when present (>0). Any falsy/missing
			# value means "no override, use the template rate".
			r = t.get("rate")
			if r is not None and r != "" and flt(r) > 0:
				row["rate"] = flt(r)
			out.append(row)
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
			# Marley reuses the same Sample Collection across orders for a
			# patient + sample type — so the Diagnostic Report linked to this
			# sample may still be `Approved`/`Authorized` from a previous
			# workflow. Reset it so the urgent gate (and verification flow)
			# fires fresh for this new clinical event.
			from diagnostic_management.api.results import reset_sample_report_state
			reset_sample_report_state(s["name"])

	# 2) One Sales Invoice for the whole set, with qty + discount + optional payment.
	include_payment = bool(bd.get("include_payment"))
	def _line(t: dict) -> dict:
		line = {
			"template_dt": "Lab Test Template",
			"template_dn": t["template_dn"],
			"qty": t["qty"],
			"discount_percentage": t["discount_percentage"],
			"label": t["template_dn"],
		}
		# Carry the user's per-line rate override through to billing.py so
		# the invoice line actually posts at the edited price. Without this
		# the SPA's Rate column would look editable but the invoice would
		# always post at the Lab Test Template's `lab_test_rate` (the bug
		# the field is reporting).
		if "rate" in t:
			line["rate"] = t["rate"]
		return line

	inv = billing_api.create_invoice_for_tests(
		patient=patient,
		items=[_line(t) for t in tests],
		service_requests=created_orders,
		mode_of_payment=bd.get("mode_of_payment") if include_payment else None,
		paid_amount=None,  # full payment handled via the dedicated payment form
		submit=1,
	)

	# 2b) Stamp the Sales Invoice link on every Lab Test fanned out from these
	# orders. This is the link Work Order auto-creation walks back through
	# (Sample → Lab Test → custom_sales_invoice → SI → BOM items) when the
	# sample reaches "Tested".
	if "custom_sales_invoice" in {df.fieldname for df in frappe.get_meta("Lab Test").fields}:
		for sr in created_orders:
			for lt_name in frappe.get_all("Lab Test", filters={"service_request": sr, "docstatus": ["!=", 2]}, pluck="name"):
				frappe.db.set_value("Lab Test", lt_name, "custom_sales_invoice", inv["invoice"], update_modified=False)

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


@frappe.whitelist()
def list_stock_alerts(status: str | None = None, limit: int = 50) -> list[dict]:
	"""Return the most recent ADMS Stock Alerts for the Billing → Stock
	Alerts panel. Defaults to Open + Acknowledged so resolved ones drop off.
	Branch-scoped: only alerts tied to patients in the user's branch."""
	if not frappe.db.exists("DocType", "ADMS Stock Alert"):
		return []
	from diagnostic_management.api.branches import patient_branch_filter
	filters: dict = {}
	if status:
		filters["status"] = status
	else:
		filters["status"] = ["in", ["Open", "Acknowledged"]]
	filters.update(patient_branch_filter("patient"))
	rows = frappe.get_all(
		"ADMS Stock Alert",
		fields=[
			"name", "alert_date", "status", "severity",
			"item_code", "item_name", "warehouse",
			"required_qty", "available_qty", "shortage_qty", "stock_uom",
			"sales_invoice", "sample_collection", "stock_entry",
			"patient", "patient_name", "lab_test", "message",
			"acknowledged_by", "acknowledged_at",
		],
		filters=filters,
		order_by="alert_date desc",
		limit_page_length=int(limit),
	)
	for r in rows:
		r["alert_date"] = str(r.get("alert_date") or "")
		r["acknowledged_at"] = str(r.get("acknowledged_at") or "")
	return rows


@frappe.whitelist()
def stock_alert_summary() -> dict:
	"""Counters for the Billing stock-alerts header. Branch-scoped."""
	if not frappe.db.exists("DocType", "ADMS Stock Alert"):
		return {"open": 0, "acknowledged": 0, "critical": 0, "today": 0}
	from diagnostic_management.api.branches import patient_branch_filter
	bf = patient_branch_filter("patient")
	def _c(extra: dict) -> int:
		f = dict(extra); f.update(bf); return frappe.db.count("ADMS Stock Alert", f)
	return {
		"open": _c({"status": "Open"}),
		"acknowledged": _c({"status": "Acknowledged"}),
		"critical": _c({"status": "Open", "severity": "Critical"}),
		"today": _c({"alert_date": [">=", frappe.utils.add_to_date(frappe.utils.today(), as_string=True)]}),
	}
