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
		# Self-heal the SOURCE first. Refetch only reshapes whatever sits on the
		# Lab Tests, so if the Lab Test itself is missing analytes there is
		# nothing for the builder to copy. The known cause is Marley's
		# `load_result_format()` having no branch for a Grouped member of a
		# Grouped package — nested packages (TFT / Electrolytes / Lipid Profile
		# inside "Afya Bora") get silently dropped at Lab Test creation. Expand
		# them here so one click fixes the root, not just the symptom.
		repaired = self._repair_source_lab_tests(si)
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
			"repaired_lab_tests": repaired,
			"counts": {
				"numeric": len(self.get("numeric_results") or []),
				"grouped": len(self.get("grouped_results") or []),
				"qualitative": len(self.get("qualitative_results") or []),
				"descriptive": len(self.get("descriptive_results") or []),
				"lab_report_tests": len(self.get("lab_report_tests") or []),
			},
		}

	def _repair_source_lab_tests(self, sales_invoice: str) -> list:
		"""Re-expand nested Grouped packages on every DRAFT Lab Test behind
		this report, and report which ones actually gained rows.

		Idempotent and safe to run on every refetch: a Lab Test whose packages
		are already expanded is left untouched and never re-saved. Submitted
		Lab Tests are skipped — their results are locked.

		Never raises: a repair failure must not block the refetch itself, which
		is still useful even if the source can't be widened.
		"""
		from diagnostic_management.overrides.lab_test_expansion import expand_nested_groups

		repaired = []
		lab_tests = frappe.get_all(
			"Lab Test",
			filters={"custom_sales_invoice": sales_invoice, "docstatus": 0},
			pluck="name",
		)
		for name in lab_tests:
			try:
				doc = frappe.get_doc("Lab Test", name)
				before = len(doc.get("normal_test_items") or [])
				expand_nested_groups(doc)
				doc.reload()
				after = len(doc.get("normal_test_items") or [])
				if after > before:
					repaired.append({"lab_test": name, "rows_added": after - before})
			except Exception:
				frappe.log_error(
					title=f"refetch_from_invoice: repair failed for {name}",
					message=frappe.get_traceback(),
				)
		return repaired

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
