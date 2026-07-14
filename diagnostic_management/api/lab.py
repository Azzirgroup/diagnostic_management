"""Lab Hub / Verification Queue / Peer Review endpoints.

Marley v16 doctype status fields use the SELECT options below — none of
which match the friendly names I had originally:
  Sample Collection:    Pending / Partly Collected / Collected
  Diagnostic Report:    Open / Pending Review / Partially Approved / Approved / Rejected
  Lab Test:             Draft / Completed / Approved / Rejected / Cancelled

Filters and writes throughout this module use those actual values.
"""

import frappe
from frappe.utils import now_datetime


# Diagnostic Report's "verifiable / pending" set — anything not yet Approved.
DR_PENDING = ["Open", "Pending Review", "Partially Approved"]

# Roles permitted to roll a verified Lab Report back to Draft (and re-open
# the underlying Lab Test docs for value editing). System Manager covers
# "Administration" — see Peer Review Amendment flow.
AMEND_ROLES: frozenset[str] = frozenset({"System Manager", "Lab Manager"})


def _require_role(allowed: frozenset[str]) -> None:
	"""Reject the call when the session user holds none of `allowed`."""
	have = set(frappe.get_roles(frappe.session.user))
	if not (have & allowed):
		frappe.throw(
			f"This action is restricted to: {', '.join(sorted(allowed))}.",
			frappe.PermissionError,
		)


@frappe.whitelist()
def hub_summary() -> dict:
	"""Counts the Lab Hub home page renders as quick-glance KPIs.
	Branch-scoped where the underlying doctype has a `patient` link."""
	from diagnostic_management.api.branches import patient_branch_filter
	bf = patient_branch_filter("patient")
	def _count(dt: str, filters: dict | None = None, scoped: bool = True) -> int:
		try:
			f = dict(filters or {})
			if scoped and bf: f.update(bf)
			return frappe.db.count(dt, f)
		except Exception:
			return 0
	return {
		"pending_accession": _count("Sample Collection", {"status": "Pending"}),
		"in_analysis": _count("Sample Collection", {"status": "Partly Collected"}),
		"pending_verification": _count("Diagnostic Report", {"status": ["in", DR_PENDING]}),
		# QC / Calibration / Peer Review are not patient-linked — keep global.
		"qc_open": _count("QC Run", {"status": "Pending Review"}, scoped=False),
		"calibration_due": _count("Calibration Run", {"status": "Scheduled"}, scoped=False),
		"peer_review_open": _count("Peer Review Case", {"status": ["in", ["Open", "In Review", "Discussion"]]}, scoped=False),
	}


@frappe.whitelist()
def verification_queue(limit: int = 100) -> list[dict]:
	"""Diagnostic Reports waiting for verification."""
	return frappe.get_all(
		"Diagnostic Report",
		fields=[
			"name", "docname", "patient", "patient_name", "practitioner",
			"status", "is_critical", "critical_acknowledged", "creation", "modified",
		],
		filters={"status": ["in", DR_PENDING]},
		order_by="modified desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def verify_report(name: str, conclusion: str | None = None) -> dict:
	"""Release a Diagnostic Report to the patient — flips it to `Approved`.

	Gated by two flags on the report:
	  - `custom_peer_reviewed = 1` — a peer review case must be closed
	    with outcome Agree / Minor Disagreement. The case is auto-created
	    by `_ensure_sample_report` when the tech clicks Save & Complete
	    (see api/results.py). Same gating shape as the urgent-review
	    flow — the tech can't Verify & Release until the reviewer signs
	    off.
	  - Urgent gate stays as-is (`urgent_review_status = Authorized` for
	    urgent cases), handled by existing code paths.
	"""
	doc = frappe.get_doc("Diagnostic Report", name)
	if not doc.get("custom_peer_reviewed"):
		frappe.throw(
			"This report can't be released yet — it's awaiting Peer Review. "
			"A reviewer must close the peer review case with Agree or Minor "
			"Disagreement before Verify & Release is available.",
			title="Peer Review Pending",
		)
	doc.db_set("status", "Approved")
	if conclusion is not None and "conclusion" in {df.fieldname for df in doc.meta.fields}:
		doc.db_set("conclusion", conclusion)
	doc.add_comment(
		"Comment",
		text=f"<b>Verified &amp; Released</b><br>By: {frappe.utils.escape_html(frappe.session.user)}",
	)
	return {"ok": True, "name": name, "status": "Approved"}


def _ensure_open_peer_review_case(dr) -> str | None:
	"""Idempotent — if any non-Closed case already exists for this report,
	reuse it; otherwise insert a new Open case.

	`section` is derived from the report's linked sample type / template,
	`original_reporter` from the current session user, `priority` from the
	report's `is_urgent` flag. `assigned_reviewer` is intentionally LEFT
	BLANK so any authorised reviewer (Lab Manager / Pathologist /
	Radiologist / Radiology Manager / System Manager) can pick the case
	from the queue.
	"""
	existing = frappe.db.get_value(
		"Peer Review Case",
		{"subject_report": dr.name, "status": ["!=", "Closed"]},
		"name",
	)
	if existing:
		# Invariant: an open case means the flag MUST be 0. If a previous
		# closed case had set it to 1, and the tech re-Saved & Completed
		# (which spawned this open case), the stale 1 would let the front-
		# end button appear. Force it back to 0.
		if dr.get("custom_peer_reviewed"):
			frappe.db.set_value("Diagnostic Report", dr.name, "custom_peer_reviewed", 0)
		return existing

	section = _derive_review_section(dr)
	priority = "Urgent" if dr.get("is_urgent") else "Routine"

	case = frappe.new_doc("Peer Review Case")
	case.subject_report = dr.name
	case.patient = dr.get("patient")
	case.patient_name = dr.get("patient_name")
	case.section = section
	case.priority = priority
	case.status = "Open"
	case.original_reporter = frappe.session.user
	case.submitted_at = now_datetime()
	# `due_date`: Urgent → same day, Routine → next business day. Keeps
	# TAT dashboards honest without over-engineering scheduling.
	from frappe.utils import add_days, today
	case.due_date = today() if priority == "Urgent" else add_days(today(), 1)
	case.insert(ignore_permissions=True)

	# Same invariant on FRESH case creation: if a previously-closed case had
	# flipped the flag to 1 and this new case supersedes it (because new
	# results were entered), the flag must reset. The new case has to be
	# closed before the button re-appears.
	if dr.get("custom_peer_reviewed"):
		frappe.db.set_value("Diagnostic Report", dr.name, "custom_peer_reviewed", 0)
	return case.name


def _derive_review_section(dr) -> str:
	"""Best-effort mapping DR → Peer Review Case section enum
	(`Lab`, `Radiology`, `Histopathology`, `Cytology`, `Other`)."""
	sample = frappe.db.get_value("Sample Collection", dr.get("sample_collection"), "sample") or ""
	sample_lower = sample.lower()
	if "tissue" in sample_lower or "biopsy" in sample_lower:
		return "Histopathology"
	if "cytology" in sample_lower or "smear" in sample_lower:
		return "Cytology"
	# If it's a Radiology Pre-Auth flow or imaging modality is set on the SR,
	# fall through to Radiology; otherwise default to Lab.
	sr = frappe.db.get_value(
		"Lab Test", {"sample": dr.get("sample_collection")}, "service_request",
	)
	if sr and frappe.db.get_value("Service Request", sr, "imaging_modality"):
		return "Radiology"
	return "Lab"


@frappe.whitelist()
def amend_report(name: str, reason: str) -> dict:
	"""Send a verified report back for amendment — Pending Review."""
	doc = frappe.get_doc("Diagnostic Report", name)
	doc.db_set("status", "Pending Review")
	doc.add_comment("Comment", text=f"<b>Amendment Requested</b><br>{frappe.utils.escape_html(reason)}")
	return {"ok": True, "name": name, "status": "Pending Review"}


# -- Peer Review -----------------------------------------------------------

@frappe.whitelist()
def peer_review_list(status: str | None = None, mine: int = 0, limit: int = 100) -> list[dict]:
	filters: dict = {}
	if status:
		filters["status"] = status
	else:
		filters["status"] = ["in", ["Open", "In Review", "Discussion"]]
	if int(mine or 0):
		filters["assigned_reviewer"] = frappe.session.user
	return frappe.get_all(
		"Peer Review Case",
		fields=[
			"name", "subject_report", "patient", "patient_name", "section", "modality",
			"priority", "original_reporter", "assigned_reviewer", "due_date",
			"status", "outcome", "submitted_at",
		],
		filters=filters,
		order_by="due_date asc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def diagnostic_report_detail(name: str) -> dict:
	"""Full context for a Diagnostic Report on the verification page: DR
	metadata, sample, its linked Lab Tests, all analyte rows (shaped via the
	same reference-range picker as the workflow), the open peer review case
	if any, and enough flags for the Verify & Release button to gate itself.
	One call — no back-and-forth navigation for the verifier."""
	# Filter to fields that actually exist on this site's Diagnostic Report —
	# `conclusion` isn't always installed as a custom field, and picking a
	# missing column errors out the whole query.
	_dr_fields = {df.fieldname for df in frappe.get_meta("Diagnostic Report").fields}
	_wanted = ["name", "patient", "patient_name", "status", "conclusion",
	           "is_urgent", "urgent_review_status", "is_critical",
	           "critical_acknowledged", "custom_peer_reviewed",
	           "sample_collection", "docname", "custom_lab_tests_csv",
	           "diagnosis", "clinical_notes", "pathologist_name",
	           "signed_by", "practitioner"]
	select_fields = [f for f in _wanted if f == "name" or f in _dr_fields]
	dr = frappe.db.get_value("Diagnostic Report", name, select_fields, as_dict=True)
	if not dr:
		frappe.throw(f"Diagnostic Report {name} not found")

	sample = dr.get("sample_collection")
	# Resolve the Lab Tests bundled by this DR — prefer the CSV stamped at
	# release time; fall back to every Lab Test on the sample.
	lt_names: list[str] = []
	csv = dr.get("custom_lab_tests_csv") or ""
	if csv:
		lt_names = [n.strip() for n in csv.split(",") if n.strip()]
	elif sample:
		lt_names = frappe.get_all(
			"Lab Test", filters={"sample": sample, "docstatus": ["<", 2]},
			pluck="name", order_by="creation asc",
		)
	from diagnostic_management.api.results import _lab_test_rows
	lab_tests = []
	for lt_name in lt_names:
		if not frappe.db.exists("Lab Test", lt_name):
			continue
		lt_doc = frappe.get_doc("Lab Test", lt_name)
		lab_tests.append(_lab_test_rows(lt_doc))

	# Peer review context — one open case (if any) drives the gate.
	pr_case = frappe.db.get_value(
		"Peer Review Case",
		{"subject_report": name, "status": ["!=", "Closed"]},
		["name", "original_reporter", "status"], as_dict=True,
	)

	sample_row = None
	if sample and frappe.db.exists("Sample Collection", sample):
		sample_row = frappe.db.get_value(
			"Sample Collection", sample,
			["name", "sample", "collected_time", "workflow_status",
			 "referring_practitioner"],
			as_dict=True,
		)

	return {
		"report": dr,
		"sample": sample_row,
		"lab_tests": lab_tests,
		"peer_review_case": pr_case,
		"workflow_session": _find_workflow_session(sample, lt_names, report=name),
	}


def _find_workflow_session(
	sample: str | None,
	lt_names: list[str] | None = None,
	report: str | None = None,
) -> str | None:
	"""Walk back to the Lab Workflow Session that originally opened this
	workflow. Tried in order:

	  1. Any Lab Test in `lt_names` — read its `service_request` → match on
	     `Lab Workflow Session.service_request`.
	  2. Every Lab Test on `sample` — same match.
	  3. Diagnostic Report's `docname` (older DRs link to a Lab Test that
	     way instead of via `sample_collection`) — walk to that Lab Test's
	     service_request.
	  4. Direct LWS lookup by patient — fall back so an older DR that has
	     none of the above still surfaces a plausible workflow when the
	     patient only has one open session.

	Returns None only if nothing plausible matches.
	"""
	srs: set[str] = set()
	if lt_names:
		for name in lt_names:
			sr = frappe.db.get_value("Lab Test", name, "service_request")
			if sr:
				srs.add(sr)
	if not srs and sample:
		for sr in frappe.get_all(
			"Lab Test",
			filters={"sample": sample, "service_request": ["is", "set"]},
			pluck="service_request",
		):
			srs.add(sr)
	if not srs and report:
		# Older Diagnostic Reports point to a Lab Test via `docname` rather
		# than sitting on a Sample Collection. Walk that link.
		docname = frappe.db.get_value("Diagnostic Report", report, "docname")
		if docname and frappe.db.exists("Lab Test", docname):
			sr = frappe.db.get_value("Lab Test", docname, "service_request")
			if sr:
				srs.add(sr)
			# Also try the Lab Test's sample to catch sibling Lab Tests.
			lt_sample = frappe.db.get_value("Lab Test", docname, "sample")
			if lt_sample:
				for sr in frappe.get_all(
					"Lab Test",
					filters={"sample": lt_sample, "service_request": ["is", "set"]},
					pluck="service_request",
				):
					srs.add(sr)
	if srs:
		lws = frappe.get_all(
			"Lab Workflow Session",
			filters={"service_request": ["in", list(srs)]},
			fields=["name"],
			order_by="modified desc",
			limit_page_length=1,
		)
		if lws:
			return lws[0]["name"]
	# Final fallback: only one open LWS for this patient? Pick it.
	if report:
		patient = frappe.db.get_value("Diagnostic Report", report, "patient")
		if patient:
			lws = frappe.get_all(
				"Lab Workflow Session",
				filters={"patient": patient},
				fields=["name"],
				order_by="modified desc",
				limit_page_length=1,
			)
			if lws:
				return lws[0]["name"]
	return None


@frappe.whitelist()
def peer_review_detail(name: str) -> dict:
	"""Everything the reviewer needs to judge a case: the subject Diagnostic
	Report, its patient/sample context, and the analyte rows from every
	Lab Test the report bundles (read-only). Returned inline so the peer-
	review page shows the same numbers the reporter entered — the reviewer
	doesn't have to navigate away to see what they're approving.

	`normal_test_items` are shaped through the same reference-range picker
	the workflow uses, so ranges/status shown here match the printed PDF.
	"""
	case = frappe.db.get_value(
		"Peer Review Case", name,
		["name", "subject_report", "patient", "patient_name", "section",
		 "priority", "original_reporter", "status", "outcome", "review_notes"],
		as_dict=True,
	)
	if not case:
		frappe.throw(f"Peer Review Case {name} not found")

	dr = None
	sample = None
	lab_tests: list[dict] = []
	if case.get("subject_report") and frappe.db.exists("Diagnostic Report", case["subject_report"]):
		dr_doc = frappe.get_doc("Diagnostic Report", case["subject_report"])
		dr = {
			"name": dr_doc.name,
			"status": dr_doc.status,
			"is_urgent": dr_doc.get("is_urgent"),
			"is_critical": dr_doc.get("is_critical"),
			"conclusion": dr_doc.get("conclusion"),
			"custom_peer_reviewed": dr_doc.get("custom_peer_reviewed"),
		}
		sample = dr_doc.get("sample_collection")
		# Which Lab Tests does this report bundle? Prefer the CSV the
		# workflow stamps (authoritative for THIS release); fall back to
		# every Lab Test on the sample.
		lt_names: list[str] = []
		csv = dr_doc.get("custom_lab_tests_csv") or ""
		if csv:
			lt_names = [n.strip() for n in csv.split(",") if n.strip()]
		elif sample:
			lt_names = frappe.get_all(
				"Lab Test", filters={"sample": sample}, pluck="name", order_by="creation asc",
			)
		for lt_name in lt_names:
			if not frappe.db.exists("Lab Test", lt_name):
				continue
			lt_doc = frappe.get_doc("Lab Test", lt_name)
			lab_tests.append(_lab_test_rows_shim(lt_doc))
	return {
		"case": case,
		"diagnostic_report": dr,
		"sample": sample,
		"lab_tests": lab_tests,
		"workflow_session": _find_workflow_session(
			sample, [lt.get("name") for lt in lab_tests],
			report=case.get("subject_report"),
		),
	}


def _lab_test_rows_shim(lt_doc) -> dict:
	"""Delegate to results._lab_test_rows so the peer-review page reads
	analytes through the exact same shaping pipeline as the workflow UI
	(reference-range picker, result_type fallback, patient-scoped ranges)."""
	from diagnostic_management.api.results import _lab_test_rows
	return _lab_test_rows(lt_doc)


def _reject_self_review(case) -> None:
	"""No-self-review rule: whoever entered the results (recorded as the
	case's `original_reporter`) cannot close their own peer review case.
	Any OTHER logged-in user can — no role check, deliberately open so
	small labs can peer-review each other without a dedicated reviewer role.
	Administrator bypasses (needed for scripted fixes / bulk operations)."""
	if frappe.session.user == "Administrator":
		return
	if case.get("original_reporter") and case.original_reporter == frappe.session.user:
		frappe.throw(
			"You entered these results — someone else must peer-review this "
			"case. The reviewer must be a different user than the original "
			"reporter.",
			title="Self-Review Blocked",
		)


@frappe.whitelist()
def submit_peer_review(
	name: str,
	outcome: str = "Agree",
	review_notes: str = "",
	discrepancy_severity: str | None = None,
	concurrence: float | None = None,
) -> dict:
	"""Close a peer review case with the reviewer's verdict, and cascade the
	subject Diagnostic Report's status:

	  - `Agree` or `Minor Disagreement`  → DR flips to **Approved** (released
	    to patient / portal).
	  - `Major Disagreement`             → DR stays **Pending Review** (blocked).
	    The reviewer typically follows up with a discussion or, if the numbers
	    are actually wrong, uses the `Submit & Amend` path (see
	    `submit_peer_review_amend`) to roll Lab Tests back to Draft.

	This is the release gate for the mandatory-peer-review model — a DR
	can only leave Pending Review through a closed peer review case.
	"""
	doc = frappe.get_doc("Peer Review Case", name)
	_reject_self_review(doc)
	doc.outcome = outcome
	if review_notes:
		doc.review_notes = review_notes
	if discrepancy_severity:
		doc.discrepancy_severity = discrepancy_severity
	if concurrence is not None:
		doc.concurrence = float(concurrence)
	doc.status = "Closed"
	doc.completed_at = now_datetime()
	# The business rule (session != original_reporter) is enforced above via
	# `_reject_self_review`; the doctype-level DocPerm gate would additionally
	# require a specific reviewer role which we deliberately opened up. Save
	# with ignore_permissions so a bare user (e.g. Lab Technician) can close
	# a peer of their colleague's case.
	doc.save(ignore_permissions=True)

	# Cascade the outcome onto the subject Diagnostic Report. In this model
	# peer review is a GATE that unlocks Verify & Release — it doesn't
	# release the report itself. Agree/Minor Disagree → flip
	# `custom_peer_reviewed = 1` so the tech's Verify & Release button
	# becomes available. Major Disagreement → keep it at 0 (still blocked).
	dr_name = doc.subject_report
	if dr_name and frappe.db.exists("Diagnostic Report", dr_name):
		if outcome in ("Agree", "Minor Disagreement"):
			frappe.db.set_value("Diagnostic Report", dr_name, "custom_peer_reviewed", 1)
			frappe.get_doc("Diagnostic Report", dr_name).add_comment(
				"Comment",
				text=(
					f"<b>Peer Review passed ({outcome})</b><br>"
					f"Case: {frappe.utils.escape_html(name)}<br>"
					f"Reviewer: {frappe.utils.escape_html(frappe.session.user)}<br>"
					f"Verify &amp; Release is now available."
				),
			)
		elif outcome == "Major Disagreement":
			# Explicitly keep flag at 0 (in case a case was re-reviewed) and
			# log why so the tech knows why Verify & Release stays blocked.
			frappe.db.set_value("Diagnostic Report", dr_name, "custom_peer_reviewed", 0)
			frappe.get_doc("Diagnostic Report", dr_name).add_comment(
				"Comment",
				text=(
					f"<b>Peer Review — Major Disagreement (blocked)</b><br>"
					f"Case: {frappe.utils.escape_html(name)}<br>"
					f"Reviewer: {frappe.utils.escape_html(frappe.session.user)}<br>"
					f"Notes: {frappe.utils.escape_html(review_notes or '')}"
				),
			)

	return {"ok": True, "name": name, "status": "Closed", "outcome": outcome}


@frappe.whitelist()
def submit_peer_review_amend(
	name: str,
	review_notes: str,
	discrepancy_severity: str | None = None,
) -> dict:
	"""Close a Peer Review Case with `outcome=Amend` AND pull the underlying
	Lab Tests back to Draft so the technologist can edit the actual analyte
	values, then re-submit through the normal verify/release flow.

	Access rule: any logged-in user can amend EXCEPT the case's
	`original_reporter` (see `_reject_self_review`). Same "no self-review"
	guardrail as the normal peer-review outcomes — a small lab may not
	have dedicated Lab Managers, so we open the amend flow to peers as
	long as they didn't enter the results themselves.

	Steps:
	  1. Close the Peer Review Case with outcome=Amend and the review notes.
	  2. Flip the Diagnostic Report back to "Pending Review" and stamp a
	     comment trail explaining why.
	  3. For each Lab Test the report covers (via DR.custom_lab_tests_csv —
	     the authoritative list of which Lab Tests THIS report bundles):
	        - cancel the submitted doc (docstatus 1 → 2)
	        - copy_doc into a new draft amended_from the cancelled one
	        - re-insert as docstatus=0 so its rows become editable again
	  4. Update DR.custom_lab_tests_csv to point at the new (amended) Lab
	     Test names so the workflow's Results step shows the right batch.
	  5. Re-link the Sample Collection's workflow_status to "In Processing"
	     so the wizard's derived-step calc lands the user back on Results
	     (the docstatus=0 lab tests are already editable; this just makes
	     the wizard's "furthest reached step" calc match reality).
	"""
	case = frappe.get_doc("Peer Review Case", name)
	_reject_self_review(case)
	if case.status == "Closed" and case.outcome == "Amendment Required":
		frappe.throw("This case has already been amended.")

	# 1. Close the peer review case.
	case.outcome = "Amendment Required"
	case.review_notes = review_notes
	if discrepancy_severity:
		case.discrepancy_severity = discrepancy_severity
	case.status = "Closed"
	case.completed_at = now_datetime()
	# Same rationale as `submit_peer_review`: the self-review guard is the real
	# business rule; the DocPerm role gate is deliberately opened up so a bare
	# Lab Technician can amend a colleague's report.
	case.save(ignore_permissions=True)

	# 2. Roll the Diagnostic Report back to Pending Review.
	dr = frappe.get_doc("Diagnostic Report", case.subject_report)
	dr.db_set("status", "Pending Review")
	dr.add_comment(
		"Comment",
		text=(
			f"<b>Amendment requested via peer review {frappe.utils.escape_html(name)}</b>"
			f"<br>By: {frappe.utils.escape_html(frappe.session.user)}"
			f"<br>{frappe.utils.escape_html(review_notes or '')}"
		),
	)

	# 3. Cancel + amend each submitted Lab Test so values become editable.
	csv = (dr.get("custom_lab_tests_csv") or "").strip()
	if not csv:
		# Fallback: walk the sample's lab tests when csv was never stamped.
		csv = ",".join(
			frappe.get_all(
				"Lab Test",
				filters={"sample": dr.sample_collection, "docstatus": 1},
				pluck="name",
			)
		)
	old_names = [n.strip() for n in csv.split(",") if n.strip()]
	new_names: list[str] = []
	for lt_name in old_names:
		if not frappe.db.exists("Lab Test", lt_name):
			continue
		lt = frappe.get_doc("Lab Test", lt_name)
		if lt.docstatus == 1:
			lt.cancel()
			amended = frappe.copy_doc(lt)
			amended.amended_from = lt_name
			amended.docstatus = 0
			amended.insert(ignore_permissions=False)
			new_names.append(amended.name)
		elif lt.docstatus == 0:
			# Already a draft (rare) — keep it.
			new_names.append(lt.name)

	# 4. Update DR's csv to point at the new draft names.
	if new_names:
		dr.db_set("custom_lab_tests_csv", ",".join(new_names))

	# 5. Re-open the Results step in the workflow wizard.
	if dr.sample_collection and frappe.db.exists("Sample Collection", dr.sample_collection):
		sc = frappe.get_doc("Sample Collection", dr.sample_collection)
		if "workflow_status" in {df.fieldname for df in sc.meta.fields}:
			sc.db_set("workflow_status", "In Processing")

	return {
		"ok": True,
		"case": name,
		"report": dr.name,
		"report_status": "Pending Review",
		"amended_lab_tests": new_names,
	}


# -- Lab Reports browser ---------------------------------------------------

@frappe.whitelist()
def list_lab_reports(
	query: str = "",
	status: str | None = None,
	date_from: str | None = None,
	date_to: str | None = None,
	limit: int = 100,
) -> list[dict]:
	"""Browseable list of Lab Reports — what the SPA's Lab Reports page shows.

	Filters:
	  - `query`: substring match against report name OR patient_name (case-insensitive).
	  - `status`: exact match on Lab Report.status (e.g. 'Approved', 'Pending').
	  - `date_from` / `date_to`: inclusive bounds on report_date (YYYY-MM-DD).
	"""
	if not frappe.db.exists("DocType", "Lab Report"):
		return []
	filters: dict = {}
	or_filters = None
	if status:
		filters["status"] = status
	if date_from:
		filters["report_date"] = [">=", date_from]
	if date_to:
		# When both bounds given, merge into a between filter.
		if "report_date" in filters:
			filters["report_date"] = ["between", [date_from, date_to]]
		else:
			filters["report_date"] = ["<=", date_to]
	if query:
		q = f"%{query.strip()}%"
		or_filters = [
			["Lab Report", "name", "like", q],
			["Lab Report", "patient_name", "like", q],
			["Lab Report", "patient", "like", q],
		]
	# Branch scoping — restrict to Lab Reports whose patient lives in the
	# current user's branch. No-op for admins / unscoped users.
	from diagnostic_management.api.branches import patient_branch_filter
	filters.update(patient_branch_filter("patient"))
	fields = [
		"name", "report_date", "patient", "patient_name", "patient_sex",
		"status", "referring_doctor", "referring_doctor_name", "department",
		"pathologist_name", "approved_by", "creation", "modified",
	]
	# Only fetch fields that exist on the doctype (Lab Report has lots of
	# optional custom fields the user may not have set up).
	available = {df.fieldname for df in frappe.get_meta("Lab Report").fields}
	fields = [f for f in fields if f in available or f in {"name", "creation", "modified"}]
	rows = frappe.get_all(
		"Lab Report",
		fields=fields,
		filters=filters,
		or_filters=or_filters,
		order_by="report_date desc, modified desc",
		limit_page_length=int(limit),
	)
	# Attach the linked Sample Collection (so the UI can deep-link back).
	if rows and "samples" in {df.fieldname for df in frappe.get_meta("Lab Report").fields}:
		report_names = [r["name"] for r in rows]
		samples_by_parent: dict[str, list[str]] = {}
		for lr_sample in frappe.get_all(
			"Lab Report Sample",
			fields=["parent", "lab_sample", "sample_type"],
			filters={"parent": ["in", report_names]},
		):
			samples_by_parent.setdefault(lr_sample.parent, []).append(lr_sample.lab_sample)
		for r in rows:
			r["samples"] = samples_by_parent.get(r["name"], [])
	return rows


@frappe.whitelist()
def lab_report_summary() -> dict:
	"""KPIs for the Lab Reports page header (total / approved / pending counts).
	Branch-scoped: a user in Branch A sees counts only for Branch A's patients."""
	if not frappe.db.exists("DocType", "Lab Report"):
		return {"total": 0, "approved": 0, "pending": 0, "today": 0}
	from diagnostic_management.api.branches import patient_branch_filter
	bf = patient_branch_filter("patient")
	def c(extra=None):
		f = dict(bf)
		if extra: f.update(extra)
		return frappe.db.count("Lab Report", f)
	total = c()
	approved = c({"status": "Approved"})
	pending = total - approved
	today = c({"report_date": frappe.utils.today()})
	return {"total": total, "approved": approved, "pending": pending, "today": today}


@frappe.whitelist()
def lab_report_detail(name: str) -> dict:
	"""Full Lab Report payload for the SPA detail page — patient header, every
	result child table (numeric / lab_report_tests / grouped / descriptive /
	qualitative), reporter sign-off, and the linked samples."""
	if not name or not frappe.db.exists("Lab Report", name):
		frappe.throw(f"Lab Report {name} not found", frappe.DoesNotExistError)
	doc = frappe.get_doc("Lab Report", name)

	def _row(r, *fields):
		out = {}
		for f in fields:
			out[f] = getattr(r, f, None)
		return out

	# Compute patient age + age band for the header
	patient_info = {}
	if doc.patient and frappe.db.exists("Patient", doc.patient):
		p = frappe.db.get_value("Patient", doc.patient,
			["patient_name", "sex", "dob", "mobile", "email"], as_dict=True) or {}
		patient_info = dict(p)
		patient_info["name"] = doc.patient

	# Linked samples (Lab Report Sample child)
	samples = []
	if "samples" in {df.fieldname for df in frappe.get_meta("Lab Report").fields}:
		for s in (doc.get("samples") or []):
			samples.append(_row(s, "lab_sample", "sample_type", "collection_datetime"))

	# Build a section-comments dict so the SPA can show the same callouts the
	# printed report shows.
	try:
		comments = doc.get_section_comments_dict() or {}
	except Exception:
		comments = {}

	return {
		"name": doc.name,
		"report_date": str(doc.report_date or ""),
		"status": doc.status,
		"patient": patient_info,
		"patient_name": doc.patient_name,
		"patient_sex": doc.patient_sex,
		"referring_doctor": getattr(doc, "referring_doctor", None),
		"referring_doctor_name": getattr(doc, "referring_doctor_name", None),
		"department": getattr(doc, "department", None),
		"pathologist": getattr(doc, "pathologist", None),
		"pathologist_name": getattr(doc, "pathologist_name", None),
		"pathologist_qualification": getattr(doc, "pathologist_qualification", None),
		"accreditation_type": getattr(doc, "accreditation_type", None),
		"diagnosis": getattr(doc, "diagnosis", None),
		"clinical_notes": getattr(doc, "clinical_notes", None),
		"pathologist_remarks": getattr(doc, "pathologist_remarks", None),
		"lab_technician_signature": getattr(doc, "lab_technician_signature", None),
		"pathologist_signature": getattr(doc, "pathologist_signature", None),
		"custom_has_image_space": int(getattr(doc, "custom_has_image_space", 0) or 0),
		"custom_image_space_image": getattr(doc, "custom_image_space_image", None),
		"custom_hide_graphs": int(getattr(doc, "custom_hide_graphs", 0) or 0),
		"samples": samples,
		"section_comments": comments,
		"numeric_results": [
			_row(r, "name", "lab_test", "test_name", "test_category", "result_value", "uom",
			     "reference_range", "reference_min", "reference_max", "status", "is_abnormal",
			     "is_critical", "interpretation", "method", "instrument", "previous_value", "previous_date")
			for r in (doc.get("numeric_results") or [])
		],
		"lab_report_tests": [
			_row(r, "name", "lab_test", "test_name", "test_category", "result_value", "uom",
			     "reference_range", "reference_min", "reference_max", "status", "is_abnormal",
			     "is_critical", "interpretation", "method", "instrument")
			for r in (doc.get("lab_report_tests") or [])
		],
		"grouped_results": [
			_row(r, "name", "lab_test", "test_name", "test_category", "group_name", "result_value", "uom",
			     "reference_range", "reference_min", "reference_max", "status", "is_abnormal", "is_critical")
			for r in (doc.get("grouped_results") or [])
		],
		"descriptive_results": [
			_row(r, "name", "lab_test", "test_name", "test_category", "result_value", "interpretation")
			for r in (doc.get("descriptive_results") or [])
		],
		"qualitative_results": [
			_row(r, "name", "lab_test", "test_name", "test_category", "result_value", "result_type", "result_options", "is_abnormal")
			for r in (doc.get("qualitative_results") or [])
		],
	}


@frappe.whitelist()
def _save_image_to_files(image: str, attached_to: str, attached_field: str = "custom_image_space_image") -> str:
	"""Persist `image` and return a short file URL safe to store in an
	Attach Image field.

	`image` may be either:
	  - a base64 data URL ("data:image/png;base64,…") — decoded and written
	    as a File document, returning its `/files/<name>` URL
	  - an already-stored URL ("/files/foo.png", "/private/files/bar.jpg")
	    — passed through unchanged

	Data URLs can be megabytes long and won't fit in the underlying
	varchar column; storing the URL string instead keeps the field small
	and the binary lives on disk like every other attachment.
	"""
	if not image:
		return ""
	if not image.startswith("data:"):
		return image  # already a URL — keep as-is

	import base64, hashlib, re
	m = re.match(r"^data:(?P<mime>[^;]+);base64,(?P<b64>.+)$", image, re.DOTALL)
	if not m:
		frappe.throw("Image must be a base64 data URL or an existing file URL.")
	mime = m.group("mime")
	try:
		content = base64.b64decode(m.group("b64"))
	except Exception:
		frappe.throw("Failed to decode image data URL.")
	ext = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg",
	       "image/gif": "gif", "image/webp": "webp", "image/svg+xml": "svg"}.get(mime, "bin")
	# Dedup approach: our filename embeds a stable sha1[:12] of the content,
	# so the same bytes always produce the same filename prefix. Frappe may
	# append its own collision suffix when inserting File, but the prefix +
	# file_size pair is unique per content. Look up by that.
	digest = hashlib.sha1(content).hexdigest()[:12]
	fname = f"lab_report_imgspace_{attached_to}_{digest}.{ext}"
	prefix = f"lab_report_imgspace_{attached_to}_{digest}"
	existing = frappe.db.get_value("File", {
		"file_name": ["like", f"{prefix}%"],
		"file_size": len(content),
		"attached_to_doctype": "Lab Report",
		"attached_to_name": attached_to,
	}, "file_url")
	if existing:
		return existing

	from frappe.utils.file_manager import save_file
	file_doc = save_file(
		fname=fname, content=content, dt="Lab Report", dn=attached_to,
		folder="Home/Attachments", is_private=0, df=attached_field,
	)
	return file_doc.file_url


@frappe.whitelist()
def set_image_space(name: str, has_image_space: int = 0,
                    image: str | None = None, clear_image: int = 0,
                    hide_graphs: int | None = None) -> dict:
	"""Set the Lab Report's print-time options.

	  has_image_space: 0/1 — toggle the reserved box above signatures.
	  image:           data URL or file URL. Data URLs are decoded and saved
	                   as a File attached to the report; only the short
	                   `/files/...` URL ends up in `custom_image_space_image`.
	  clear_image:     1 → wipe the existing image; takes precedence.
	  hide_graphs:     0/1 — suppress trend charts in the print. None leaves
	                   the existing value untouched (so a caller that only
	                   cares about image space doesn't have to know about it).
	"""
	if not frappe.db.exists("Lab Report", name):
		frappe.throw(f"Lab Report {name} not found", frappe.DoesNotExistError)
	val = 1 if int(has_image_space or 0) else 0
	updates: dict = {"custom_has_image_space": val}
	if int(clear_image or 0):
		updates["custom_image_space_image"] = None
	elif image:
		updates["custom_image_space_image"] = _save_image_to_files(image, name)
	if hide_graphs is not None and hide_graphs != "":
		updates["custom_hide_graphs"] = 1 if int(hide_graphs) else 0
	frappe.db.set_value("Lab Report", name, updates)
	row = frappe.db.get_value(
		"Lab Report", name,
		["custom_has_image_space", "custom_image_space_image", "custom_hide_graphs"],
		as_dict=True,
	) or {}
	return {
		"ok": True,
		"name": name,
		"custom_has_image_space": int(row.get("custom_has_image_space") or 0),
		"custom_image_space_image": row.get("custom_image_space_image"),
		"custom_hide_graphs": int(row.get("custom_hide_graphs") or 0),
	}
