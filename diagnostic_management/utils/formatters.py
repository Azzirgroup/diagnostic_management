"""Jinja helpers for ADMS print formats.

Registered in hooks.py under `jinja.methods`, so the names below are callable
directly inside any Print Format's HTML (e.g. `{{ generate_barcode_svg(doc.name) }}`).
Ported from the previous Genetest system so the diagnostic labels carry a
real, scannable barcode rather than plain text.
"""

from __future__ import annotations

import frappe
from frappe.utils import get_datetime, getdate, today


def generate_barcode_svg(data, barcode_type: str = "code128") -> str:
	"""Return an inline SVG barcode for `data` (empty string on any failure).

	Uses python-barcode's SVGWriter. `write_text=False` keeps the glyph
	clean so the label template can render its own human-readable id below.
	"""
	if not data:
		return ""
	try:
		import io

		import barcode
		from barcode.writer import SVGWriter

		barcode_class = barcode.get_barcode_class(barcode_type)
		code = barcode_class(str(data), writer=SVGWriter())
		buffer = io.BytesIO()
		code.write(
			buffer,
			options={
				"module_width": 0.25,
				"module_height": 8,
				"quiet_zone": 1,
				"font_size": 0,
				"write_text": False,
			},
		)
		svg = buffer.getvalue().decode("utf-8")
		# Drop the XML declaration so the SVG embeds inline cleanly.
		if "<?xml" in svg:
			svg = svg.split("?>", 1)[1].strip()
		return svg
	except Exception:
		frappe.log_error(title="ADMS: barcode SVG generation failed")
		return ""


def generate_barcode_base64(data, barcode_type: str = "code128") -> str:
	"""Return a data: URI PNG barcode for `data` (for <img src=...>)."""
	if not data:
		return ""
	try:
		import base64
		import io

		import barcode
		from barcode.writer import ImageWriter

		barcode_class = barcode.get_barcode_class(barcode_type)
		code = barcode_class(str(data), writer=ImageWriter())
		buffer = io.BytesIO()
		code.write(buffer, options={"module_height": 8, "font_size": 0, "write_text": False})
		encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
		return f"data:image/png;base64,{encoded}"
	except Exception:
		frappe.log_error(title="ADMS: barcode PNG generation failed")
		return ""


def generate_qr_code_base64(data, size: int = 100) -> str:
	"""Return a data: URI PNG QR code for `data` (for <img src=...>).

	Uses pyqrcode + pypng (both shipped in the bench env); resizes to `size`px
	with Pillow when available. Empty string when data is blank or on error.
	"""
	if not data:
		return ""
	try:
		import base64
		import io

		import pyqrcode

		qr = pyqrcode.create(str(data))
		buffer = io.BytesIO()
		qr.png(buffer, scale=4, quiet_zone=2)
		buffer.seek(0)
		try:
			from PIL import Image

			img = Image.open(buffer).convert("RGB").resize((int(size), int(size)))
			out = io.BytesIO()
			img.save(out, format="PNG")
			payload = out.getvalue()
		except Exception:
			payload = buffer.getvalue()
		encoded = base64.b64encode(payload).decode("utf-8")
		return f"data:image/png;base64,{encoded}"
	except Exception:
		frappe.log_error(title="ADMS: QR PNG generation failed")
		return ""


def format_report_datetime(dt, format_str: str = "dd-MMM-yyyy HH:mm") -> str:
	"""Format a datetime using simple dd/MMM/yyyy/HH/mm tokens. '-' when empty."""
	if not dt:
		return "-"
	try:
		d = get_datetime(dt)
		tokens = {
			"dd": d.strftime("%d"),
			"MMM": d.strftime("%b"),
			"MM": d.strftime("%m"),
			"yyyy": d.strftime("%Y"),
			"yy": d.strftime("%y"),
			"HH": d.strftime("%H"),
			"mm": d.strftime("%M"),
			"ss": d.strftime("%S"),
		}
		out = format_str
		for token, value in tokens.items():
			out = out.replace(token, value)
		return out
	except Exception:
		return str(dt) if dt else "-"


def result_flag(value, normal_range=None) -> str:
	"""Status for a numeric result vs its reference range: High / Low / Normal.

	Parses ranges like "13 - 17", "< 200", "> 40". Returns "" for non-numeric
	results or when no range is given.

	Handles two common data-quality issues from imported ranges:
	  * "37 -53" (no space after the dash) — normalised so the second number
	    isn't parsed as negative.
	  * Multi-line ranges like "Adult 40 - 150 U / L\\nPaed < 500 U / L" —
	    only the FIRST non-empty line is considered. `pick_reference_range`
	    already picks the age-appropriate row so multi-line text only
	    survives on legacy / pre-fix Lab Reports; taking the first line is
	    almost always the adult range, which matches genetest's convention.
	"""
	import re

	try:
		v = float(value)
	except (TypeError, ValueError):
		return ""
	if not normal_range:
		return ""
	rng = str(normal_range)
	first_line = next((ln for ln in rng.splitlines() if ln.strip()), rng)
	# Normalise `40-53`, `37 -53`, `40 - 53` → `40 53` so the number regex
	# doesn't grab the range separator as a negative sign.
	normalised = re.sub(r"(?<=\d)\s*-\s*(?=\d)", " ", first_line)
	nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", normalised)]
	low = high = None
	if re.search(r"[<≤]", first_line) and nums:
		high = nums[0]
	elif re.search(r"[>≥]", first_line) and nums:
		low = nums[0]
	elif len(nums) >= 2:
		low, high = nums[0], nums[1]
	if high is not None and v > high:
		return "High"
	if low is not None and v < low:
		return "Low"
	if low is not None or high is not None:
		return "Normal"
	return ""


# --- Banded interpretation ---------------------------------------------------
#
# Some analytes (HbA1c, ACR, Vitamin D) are read as CATEGORIES (Normal /
# Pre-diabetic / Diabetic; Optimal / Insufficient / Sufficient) instead of a
# simple in-range / out-of-range. The bands live free-text on the template's
# `normal_range`, e.g. for DCCT-HbA1c:
#
#   NORMAL GLUCOSE  4.0- 5.6%,
#   PRE-DIABETES MELLITUS 5.7 - 6.5 %,
#   DIABETES MELLITUS (Desirable Target) >6.5 %.
#
# `banded_flag` parses this into (label, matcher) pairs and returns the band
# a value falls into. The label is then normalised onto the fixed enum on
# Normal Test Result.status (Normal / Pre-diabetic / Diabetic / …) so the
# frontend saves it back without a Select validation error.

_BAND_ALIASES = (
	# order matters — first match wins. More specific patterns come first.
	("pre[- ]?diabet",        "Pre-diabetic"),
	("non[- ]?diabet",        "Normal"),
	("diabet",                "Diabetic"),
	("normal",                "Normal"),
	("optim",                 "Optimal"),
	("insufficien",           "Insufficiency"),
	("sufficien",             "Sufficiency"),
	("deficien",              "Deficiency"),
	("toxic",                 "Potential Toxicity"),
	("critical",              "Critical"),
	("intermediat|borderline","Intermediate"),
	("abnormal",              "Abnormal"),
	("high",                  "High"),
	("low",                   "Low"),
)


def _normalise_band_label(raw: str) -> str:
	"""Map a free-text band label ('PRE-DIABETES MELLITUS', 'Non Diabetic',
	'Diabetic') onto the Normal Test Result.status Select enum. Returns ""
	when nothing matches — caller falls back to numeric flag."""
	import re
	s = (raw or "").lower()
	for pat, canonical in _BAND_ALIASES:
		if re.search(pat, s):
			return canonical
	return ""


def banded_flag(value, range_text) -> str:
	"""Return the interpretive band for a numeric value against a multi-band
	range text. Empty string when the range doesn't parse into ≥2 bands or the
	value doesn't fall into any recognised band.

	Recognised per-line specs (comma-separated also splits):
	  * `LABEL LOW - HIGH`         → inclusive band
	  * `LABEL < N` / `LABEL ≤ N`  → open / closed upper-bounded band
	  * `LABEL > N` / `LABEL ≥ N`  → open / closed lower-bounded band

	The label is normalised via `_normalise_band_label` onto the fixed status
	enum. Bands whose label doesn't normalise are skipped so we don't hand
	the frontend a value it can't save (e.g. "NORMAL GLUCOSE" → "Normal";
	"PRE-DIABETES MELLITUS" → "Pre-diabetic")."""
	import re

	try:
		v = float(value)
	except (TypeError, ValueError):
		return ""
	if not range_text:
		return ""

	# Split on newlines / commas / semicolons — templates use any combination.
	parts = re.split(r"[\n,;]", str(range_text))

	bands = []  # (canonical_label, matcher)
	for raw in parts:
		s = raw.strip().rstrip(".").strip()
		if not s:
			continue
		# 1. Inequality band: `<N`, `<=N`, `≤N`, `>N`, `>=N`, `≥N`
		m = re.search(r"(<=|>=|≤|≥|<|>)\s*(-?\d+(?:\.\d+)?)", s)
		if m:
			op, n = m.group(1), float(m.group(2))
			raw_label = s[:m.start()]
			label = _normalise_band_label(raw_label)
			if not label:
				continue
			if op in ("<", "≤", "<="):
				inclusive = op in ("≤", "<=")
				bands.append((label, (lambda x, h=n, incl=inclusive: (x <= h) if incl else (x < h))))
			else:
				inclusive = op in ("≥", ">=")
				bands.append((label, (lambda x, l=n, incl=inclusive: (x >= l) if incl else (x > l))))
			continue
		# 2. Range band: `LOW - HIGH` (any dash spacing). Same normalisation as
		# `result_flag` so `5.7 -6.5` isn't parsed as [5.7, -6.5].
		normalised = re.sub(r"(?<=\d)\s*-\s*(?=\d)", " ~ ", s)
		rm = re.search(r"(-?\d+(?:\.\d+)?)\s*~\s*(-?\d+(?:\.\d+)?)", normalised)
		if rm:
			low, high = float(rm.group(1)), float(rm.group(2))
			raw_label = normalised[:rm.start()]
			label = _normalise_band_label(raw_label)
			if not label:
				continue
			bands.append((label, (lambda x, l=low, h=high: l <= x <= h)))

	if len(bands) < 2:
		return ""

	for label, matcher in bands:
		if matcher(v):
			return label
	return ""


def format_patient_age(dob, reference_date=None) -> str:
	"""Human age from a date of birth: "25 Years" / "6 Months" / "15 Days"."""
	if not dob:
		return ""
	try:
		birth = getdate(dob)
		ref = getdate(reference_date) if reference_date else getdate(today())
		years = ref.year - birth.year - ((ref.month, ref.day) < (birth.month, birth.day))
		if years > 0:
			return f"{years} Year{'s' if years != 1 else ''}"
		months = (ref.year - birth.year) * 12 + ref.month - birth.month - (1 if ref.day < birth.day else 0)
		if months > 0:
			return f"{months} Month{'s' if months != 1 else ''}"
		days = (ref - birth).days
		return f"{days} Day{'s' if days != 1 else ''}"
	except Exception:
		return ""


def format_report_date(dt, format_str: str = "dd-MMM-yyyy") -> str:
	"""Format a date with simple dd/MMM/MM/yyyy/yy tokens. '-' when empty."""
	if not dt:
		return "-"
	try:
		date_obj = getdate(dt)
		tokens = {
			"dd": date_obj.strftime("%d"),
			"MMM": date_obj.strftime("%b"),
			"MM": date_obj.strftime("%m"),
			"yyyy": date_obj.strftime("%Y"),
			"yy": date_obj.strftime("%y"),
		}
		out = format_str
		for token, value in tokens.items():
			out = out.replace(token, value)
		return out
	except Exception:
		return str(dt) if dt else "-"


def lab_report_grouped_sections(doc):
	"""Split a Lab Report's `grouped_results` into one section PER PANEL.

	Derived at render time rather than read from the stored `group_name`, which
	`_build_lab_report` stamps with the outer package for every row — so a
	package prints as one undifferentiated list of 70+ analytes instead of
	FBC / Lipid / Liver / Urinalysis / TFT sections.

	Doing it here means every EXISTING report regroups on its next print, with
	no data migration and nothing rewritten on released (submitted) reports.

	The grouped row doesn't store its own template, so the leaf is recovered by
	matching `test_name` back to the Lab Test's `normal_test_items` row, whose
	`.template` is the leaf; `section_map` then resolves the leaf to the panel
	that owns it. Standalone analytes fall back to the package heading.

	Returns [{"name": <heading>, "items": [row, ...]}, ...] in first-appearance
	order. Never raises — on any failure it degrades to the old stored-
	`group_name` grouping so a report still prints.
	"""
	rows = doc.get("grouped_results") or []
	if not rows:
		return []

	def _fallback(row):
		return row.get("group_name") or row.get("test_category") or "General Tests"

	order, buckets = [], {}

	def _place(row, heading):
		if heading not in buckets:
			buckets[heading] = []
			order.append(heading)
		buckets[heading].append(row)

	try:
		from diagnostic_management.overrides.lab_test_expansion import section_map

		cache = {}
		for row in rows:
			lt_name = row.get("lab_test")
			info = None
			if lt_name:
				if lt_name not in cache:
					try:
						lt = frappe.get_doc("Lab Test", lt_name)
						analytes = {}
						for r in lt.get("normal_test_items") or []:
							key = r.get("lab_test_name") or r.get("lab_test_event")
							if key and key not in analytes:
								analytes[key] = r.get("template")
						cache[lt_name] = (lt.get("template"), section_map(lt.get("template")), analytes)
					except Exception:
						cache[lt_name] = None
				info = cache[lt_name]
			if info:
				package, smap, analytes = info
				heading = smap.get(analytes.get(row.get("test_name"))) or _fallback(row) or package
			else:
				heading = _fallback(row)
			_place(row, heading)
	except Exception:
		frappe.log_error(title="formatters.lab_report_grouped_sections failed")
		order, buckets = [], {}
		for row in rows:
			_place(row, _fallback(row))

	return [{"name": h, "items": buckets[h]} for h in order]


def get_patient_test_history(patient, test_name, limit=6):
	"""Historical results for a patient+test (oldest->newest) for trend charts.

	Looks across EVERY result child table on Lab Report so trend graphs work
	regardless of template type:
	  - Lab Report Test            → Single
	  - Lab Report Numeric Result  → Compound
	  - Lab Report Grouped Result  → Grouped

	The earlier version only queried `tabLab Report Test`, which silently
	hid trend graphs on Compound / Grouped templates (the bulk of analytes).
	"""
	if not patient or not test_name:
		return []
	try:
		results = frappe.db.sql(
			"""
			SELECT date, value, reference_min, reference_max, uom FROM (
				SELECT lr.report_date as date, lrt.result_value as value,
				       lrt.reference_min, lrt.reference_max, lrt.uom
				FROM `tabLab Report Test` lrt
				JOIN `tabLab Report` lr ON lrt.parent = lr.name
				WHERE lr.patient = %s AND lrt.test_name = %s
				  AND lr.status IN ('Approved','Delivered')
				  AND lrt.result_value IS NOT NULL AND lrt.result_value != ''
				UNION ALL
				SELECT lr.report_date as date, lrn.result_value as value,
				       lrn.reference_min, lrn.reference_max, lrn.uom
				FROM `tabLab Report Numeric Result` lrn
				JOIN `tabLab Report` lr ON lrn.parent = lr.name
				WHERE lr.patient = %s AND lrn.test_name = %s
				  AND lr.status IN ('Approved','Delivered')
				  AND lrn.result_value IS NOT NULL AND lrn.result_value != ''
				UNION ALL
				SELECT lr.report_date as date, lrg.result_value as value,
				       lrg.reference_min, lrg.reference_max, lrg.uom
				FROM `tabLab Report Grouped Result` lrg
				JOIN `tabLab Report` lr ON lrg.parent = lr.name
				WHERE lr.patient = %s AND lrg.test_name = %s
				  AND lr.status IN ('Approved','Delivered')
				  AND lrg.result_value IS NOT NULL AND lrg.result_value != ''
			) merged
			ORDER BY date DESC
			LIMIT %s
			""",
			(patient, test_name, patient, test_name, patient, test_name, limit),
			as_dict=True,
		)
		# Reverse to oldest->newest (left to right on the chart).
		return list(reversed(results))
	except Exception:
		frappe.log_error(title="formatters.get_patient_test_history failed")
		return []


def generate_trend_chart_svg(data_points, ref_min=None, ref_max=None, width=200, height=80):
	"""Inline SVG line chart of result trends, with reference-range shading."""
	if not data_points or len(data_points) < 2:
		return ""
	try:
		values = []
		for point in data_points:
			try:
				values.append(float(point.get("value", 0)))
			except (ValueError, TypeError):
				continue
		if len(values) < 2:
			return ""

		padding_x = 25
		padding_y = 15
		chart_width = width - (padding_x * 2)
		chart_height = height - (padding_y * 2)

		min_val = min(values)
		max_val = max(values)
		if ref_min is not None:
			min_val = min(min_val, float(ref_min))
		if ref_max is not None:
			max_val = max(max_val, float(ref_max))

		value_range = max_val - min_val
		if value_range == 0:
			value_range = 1
		min_val -= value_range * 0.1
		max_val += value_range * 0.1
		value_range = max_val - min_val

		points = []
		for i, val in enumerate(values):
			x = padding_x + (i / (len(values) - 1)) * chart_width
			y = padding_y + chart_height - ((val - min_val) / value_range * chart_height)
			points.append((x, y, val))

		svg_parts = [
			f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
		]

		if ref_min is not None and ref_max is not None:
			try:
				ref_y_max = padding_y + chart_height - ((float(ref_max) - min_val) / value_range * chart_height)
				ref_y_min = padding_y + chart_height - ((float(ref_min) - min_val) / value_range * chart_height)
				svg_parts.append(
					f'<rect x="{padding_x}" y="{ref_y_max}" width="{chart_width}" height="{ref_y_min - ref_y_max}" '
					f'fill="#e8f5e9" stroke="none" opacity="0.7"/>'
				)
				svg_parts.append(
					f'<line x1="{padding_x}" y1="{ref_y_max}" x2="{padding_x + chart_width}" y2="{ref_y_max}" '
					f'stroke="#4caf50" stroke-width="1" stroke-dasharray="3,3"/>'
				)
				svg_parts.append(
					f'<line x1="{padding_x}" y1="{ref_y_min}" x2="{padding_x + chart_width}" y2="{ref_y_min}" '
					f'stroke="#4caf50" stroke-width="1" stroke-dasharray="3,3"/>'
				)
			except (ValueError, TypeError):
				pass

		svg_parts.append(
			f'<line x1="{padding_x}" y1="{padding_y}" x2="{padding_x}" y2="{padding_y + chart_height}" '
			f'stroke="#999" stroke-width="1"/>'
		)
		svg_parts.append(
			f'<line x1="{padding_x}" y1="{padding_y + chart_height}" x2="{padding_x + chart_width}" y2="{padding_y + chart_height}" '
			f'stroke="#999" stroke-width="1"/>'
		)

		if len(points) >= 2:
			path_d = f"M {points[0][0]},{points[0][1]}"
			for x, y, _ in points[1:]:
				path_d += f" L {x},{y}"
			svg_parts.append(
				f'<path d="{path_d}" fill="none" stroke="#1976d2" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
			)

		for x, y, val in points:
			color = "#1976d2"
			if ref_min is not None and ref_max is not None:
				try:
					if val < float(ref_min) or val > float(ref_max):
						color = "#e74c3c"
				except (ValueError, TypeError):
					pass
			svg_parts.append(
				f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" stroke="white" stroke-width="1.5"/>'
			)

		for x, y, val in points:
			svg_parts.append(
				f'<text x="{x}" y="{y - 8}" text-anchor="middle" font-size="8" fill="#333">{val:.1f}</text>'
			)

		svg_parts.append(
			f'<text x="{padding_x - 3}" y="{padding_y + 4}" text-anchor="end" font-size="7" fill="#666">{max_val:.1f}</text>'
		)
		svg_parts.append(
			f'<text x="{padding_x - 3}" y="{padding_y + chart_height}" text-anchor="end" font-size="7" fill="#666">{min_val:.1f}</text>'
		)

		svg_parts.append("</svg>")
		return "".join(svg_parts)
	except Exception:
		frappe.log_error(title="formatters.generate_trend_chart_svg failed")
		return ""
