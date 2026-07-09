"""Reference-range selection for ADMS Lab Test Templates.

Looks up the ADMS Reference Range child rows on a template and picks the row
that best matches the patient's sex + age. Empty filters on a row mean "match
any" — so an empty/empty row acts as a catch-all default.

Selection rules:
  - A row with a non-blank `gender` that doesn't match the patient → DISQUALIFIED.
  - A row with a non-blank `age_group` whose band doesn't contain the patient's
    age → DISQUALIFIED.
  - Among qualifying rows, the one with the most non-blank filters wins
    (most-specific match). Ties broken by row order on the template.
  - For Compound templates, rows whose `analyte` matches the sub-analyte name
    take priority over rows with a blank analyte (those act as defaults).
"""

from __future__ import annotations

import frappe
from frappe.utils import getdate, today


def patient_age(patient: str | None, ref_date=None) -> dict | None:
	"""Patient's age expressed in Days / Months / Years (floats), or None when
	we can't compute it.

	Preferred source is `Patient.dob`. Many restored genetest patients don't
	have a DOB — they have `custom_age` + `custom_age_type` (Years / Months /
	Days) instead, populated at registration. Fall back to those so the age-
	scoped reference range picker actually resolves for these patients.
	"""
	if not patient:
		return None
	row = frappe.db.get_value(
		"Patient", patient, ["dob", "custom_age", "custom_age_type"], as_dict=True
	) or {}
	dob = row.get("dob")
	if dob:
		try:
			birth = getdate(dob)
			ref = getdate(ref_date) if ref_date else getdate(today())
			days = (ref - birth).days
			if days < 0:
				return None
			return {"Days": float(days), "Months": days / 30.4375, "Years": days / 365.25}
		except Exception:
			pass
	# Fallback: `custom_age` in the type the user entered — normalise to all
	# three so ADMS Age Group matching works regardless of `age_unit`.
	c_age = row.get("custom_age")
	if c_age not in (None, ""):
		try:
			amount = float(c_age)
		except (TypeError, ValueError):
			return None
		unit = (row.get("custom_age_type") or "Years").strip()
		if unit == "Days":
			days = amount
		elif unit == "Months":
			days = amount * 30.4375
		else:  # default Years
			days = amount * 365.25
		return {"Days": days, "Months": days / 30.4375, "Years": days / 365.25}
	return None


def _row_score(row, sex: str | None, age: dict | None) -> int | None:
	"""Return a score for `row` against (sex, age). None means disqualified."""
	score = 0
	if row.get("gender"):
		if not sex or row["gender"] != sex:
			return None
		score += 1
	if row.get("age_group"):
		if not age:
			return None
		ag = frappe.db.get_value(
			"ADMS Age Group", row["age_group"],
			["min_age", "max_age", "age_unit"], as_dict=True,
		)
		if not ag:
			return None
		unit = (ag.get("age_unit") or "Years")
		a = age.get(unit, age["Years"])
		lo = ag.get("min_age")
		hi = ag.get("max_age")
		if lo is not None and a < float(lo):
			return None
		if hi is not None and a > float(hi):
			return None
		score += 1
	return score


def pick_reference_range(template: str | None, analyte: str | None, patient: str | None) -> dict | None:
	"""Best matching ADMS Reference Range row, or None when nothing fits or no
	rows are configured. Returns `{'range_text', 'uom', 'notes', 'row_name'}`."""
	if not template:
		return None
	rows = frappe.get_all(
		"ADMS Reference Range",
		filters={"parent": template, "parenttype": "Lab Test Template"},
		fields=["name", "analyte", "gender", "age_group", "range_text", "uom", "notes",
		        "result_type", "result_options", "idx"],
		order_by="idx asc",
	)
	if not rows:
		return None

	# For Compound templates we ship one row per (sub-analyte, scope). Prefer
	# rows tagged with this analyte; fall back to rows with a blank analyte
	# (which act as a default for the whole template).
	clean = (analyte or "").strip()
	if clean:
		scoped = [r for r in rows if (r.get("analyte") or "").strip() == clean]
		defaults = [r for r in rows if not (r.get("analyte") or "").strip()]
		candidates = scoped if scoped else defaults
	else:
		candidates = [r for r in rows if not (r.get("analyte") or "").strip()]
		if not candidates:
			candidates = rows  # last-resort: any row on this template

	sex = frappe.db.get_value("Patient", patient, "sex") if patient else None
	age = patient_age(patient)

	best = None
	best_score = -1
	for r in candidates:
		s = _row_score(r, sex, age)
		if s is None:
			continue
		if s > best_score:
			best = r
			best_score = s

	if not best:
		return None
	return {
		"range_text": best.get("range_text"),
		"uom": best.get("uom"),
		"notes": best.get("notes"),
		"result_type": best.get("result_type") or "Numeric",
		"result_options": best.get("result_options"),
		"row_name": best.get("name"),
	}
