# Copyright (c) 2026, Azzir ADMS
import json as _json
import frappe
from frappe.model.document import Document


class LabReport(Document):
	@frappe.whitelist()
	def refetch_from_invoice(self):
		"""Refresh this Lab Report from the Lab Sample + Lab Tests that were
		created when its linked Sales Invoice was submitted.

		The lab pipeline sometimes drops rows on this doc when a workflow is
		re-opened, or a tech deletes something manually — this rebuilds the
		Lab Report's rows from the source of truth (the Lab Tests linked to
		`custom_sales_invoice`) without needing a full workflow restart.

		Uses the same `_build_lab_report` shaper as the workflow's Verify &
		Release path so numeric / grouped / qualitative / descriptive result
		tables come out identical to a fresh print.
		"""
		si = self.get("custom_sales_invoice")
		if not si:
			frappe.throw("This Lab Report has no linked Sales Invoice (custom_sales_invoice).")
		# Find the Lab Sample the report was built from — prefer the child
		# Lab Report Sample rows; fall back to any Lab Test on this invoice.
		sample = None
		for s in (self.get("samples") or []):
			if s.get("lab_sample"):
				sample = s.get("lab_sample"); break
		if not sample:
			sample = frappe.db.get_value(
				"Lab Test",
				{"custom_sales_invoice": si, "sample": ["is", "set"]},
				"sample",
			)
		if not sample:
			frappe.throw(
				f"No Lab Sample linked to Sales Invoice {si}. Confirm the invoice "
				"was submitted through the workflow so Lab Tests + Sample were created."
			)
		# Delegate to the workflow's builder — it upserts rows on the same
		# Lab Report doc (matched by the Lab Report Sample child table).
		from diagnostic_management.api.results import _build_lab_report
		result = _build_lab_report(sample, {"status": self.get("status") or "Approved"})
		# Refresh in-memory so the desk form re-renders with the new child rows.
		if result:
			self.reload()
		# Return counts for the client-side toast.
		return {
			"ok": True,
			"lab_report": result or self.name,
			"sample": sample,
			"counts": {
				"numeric": len(self.get("numeric_results") or []),
				"grouped": len(self.get("grouped_results") or []),
				"qualitative": len(self.get("qualitative_results") or []),
				"descriptive": len(self.get("descriptive_results") or []),
				"lab_report_tests": len(self.get("lab_report_tests") or []),
			},
		}

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
