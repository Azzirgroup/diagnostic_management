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
	"""
	import re

	try:
		v = float(value)
	except (TypeError, ValueError):
		return ""
	if not normal_range:
		return ""
	rng = str(normal_range)
	nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", rng)]
	low = high = None
	if re.search(r"[<≤]", rng) and nums:
		high = nums[0]
	elif re.search(r"[>≥]", rng) and nums:
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


def get_patient_test_history(patient, test_name, limit=6):
	"""Historical results for a patient+test (oldest->newest) for trend charts.

	Reads the ported Lab Report Test child table of Approved/Delivered reports.
	"""
	if not patient or not test_name:
		return []
	try:
		results = frappe.db.sql(
			"""
			SELECT
				lr.report_date as date,
				lrt.result_value as value,
				lrt.reference_min,
				lrt.reference_max,
				lrt.uom
			FROM `tabLab Report Test` lrt
			INNER JOIN `tabLab Report` lr ON lrt.parent = lr.name
			WHERE lr.patient = %s
			AND lrt.test_name = %s
			AND lr.status IN ('Approved', 'Delivered')
			AND lrt.result_value IS NOT NULL
			AND lrt.result_value != ''
			ORDER BY lr.report_date DESC
			LIMIT %s
			""",
			(patient, test_name, limit),
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
