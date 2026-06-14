# Copyright (c) 2026, Azzir ADMS
import json as _json
import frappe
from frappe.model.document import Document


class LabReport(Document):
	def get_section_comments_dict(self):
		stored = {}
		raw = getattr(self, "custom_section_comments", None)
		if raw:
			try:
				stored = _json.loads(raw)
			except Exception:
				stored = {}
		comments = dict(stored)
		names = set()
		for table in ["lab_report_tests", "numeric_results", "qualitative_results", "descriptive_results", "grouped_results"]:
			for row in getattr(self, table, None) or []:
				for val in [getattr(row, "test_category", "") or "", getattr(row, "group_name", "") or "", getattr(row, "test_name", "") or ""]:
					if val:
						names.add(val)
		for name in names:
			if name not in comments:
				try:
					c = frappe.db.get_value("Lab Test Template", name, "custom_comment")
				except Exception:
					c = None
				if c:
					comments[name] = c
		return comments
