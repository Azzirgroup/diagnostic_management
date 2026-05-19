"""Idempotent seed data for the ADMS lab pipeline.

Marley Healthcare ships an empty `Sample Type` table on fresh sites — which
means `create_sample_doc` (the helper that auto-creates Sample Collection
when a Lab Test is inserted) silently skips, and the Collection worklist
stays empty even after the user submits orders. We seed the canonical
specimen types here so the flow works end-to-end out of the box.
"""

from __future__ import annotations

import frappe


# Two related lookup doctypes ship empty in fresh Marley sites:
#   • `Sample Type`        — broad category label (used as classification)
#   • `Lab Test Sample`    — what Lab Test Template / Sample Collection
#                            actually Link to. This is the row create_sample_doc
#                            looks up; missing rows here break the entire
#                            order → Lab Test → Sample Collection chain.
# Seed both, with name == specimen type for the lookup join to be trivial.
# UOM names match ERPNext's stock `UOM` records (Millilitre / Gram / Nos /
# Unit) — lower-case shorthand like "ml" / "g" doesn't exist as a UOM doc.
_SAMPLES = [
	{"name": "Blood",   "uom": "Millilitre", "container": "Red"},
	{"name": "Serum",   "uom": "Millilitre", "container": "Gold"},
	{"name": "Plasma",  "uom": "Millilitre", "container": "Lavender"},
	{"name": "Urine",   "uom": "Millilitre", "container": "Yellow"},
	{"name": "Stool",   "uom": "Gram",       "container": "Brown"},
	{"name": "Sputum",  "uom": "Millilitre", "container": "White"},
	{"name": "Swab",    "uom": "Nos",        "container": ""},
	{"name": "Tissue",  "uom": "Nos",        "container": ""},
	{"name": "CSF",     "uom": "Millilitre", "container": "Clear"},
	{"name": "Other",   "uom": "Nos",        "container": ""},
]


def install_seed_data() -> None:
	_seed_sample_types()
	_seed_lab_test_samples()
	_seed_body_parts()
	_seed_imaging_templates()
	_backfill_template_samples()


def _seed_sample_types() -> None:
	for spec in _SAMPLES:
		name = spec["name"]
		if frappe.db.exists("Sample Type", name):
			continue
		try:
			frappe.get_doc({
				"doctype": "Sample Type",
				"sample_type": name,
			}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(title=f"ADMS: failed to seed Sample Type {name}")


def _seed_lab_test_samples() -> None:
	"""Lab Test Sample — the row Sample Collection.sample links to.

	`sample_uom` (Link to Lab Test UOM) and `container_closure_color`
	(Link to Color) are skipped because their parent doctypes are empty
	on fresh sites — adding links to non-existent docs would raise
	`LinkValidationError`. Both are optional on Lab Test Sample.
	"""
	for spec in _SAMPLES:
		name = spec["name"]
		if frappe.db.exists("Lab Test Sample", name):
			continue
		try:
			frappe.get_doc({
				"doctype": "Lab Test Sample",
				"sample": name,
				"sample_type": name,
			}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(title=f"ADMS: failed to seed Lab Test Sample {name}")


_BODY_PARTS = [
	"Head", "Brain", "Neck", "Chest", "Abdomen", "Pelvis", "Spine",
	"Upper Limb", "Lower Limb", "Hand", "Foot", "Knee", "Shoulder", "Hip",
	"Whole Body",
]


def _seed_body_parts() -> None:
	for name in _BODY_PARTS:
		if frappe.db.exists("Body Part", name):
			continue
		try:
			frappe.get_doc({
				"doctype": "Body Part",
				"body_part": name,
			}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(title=f"ADMS: failed to seed Body Part {name}")


# Imaging procedures shipped as Clinical Procedure Template — the SPA's
# Order Intake "Radiology" tab pulls from this table. Each entry shows up
# as a selectable procedure when the user is placing an imaging order.
_IMAGING_PROCEDURES = [
	("X-Ray Chest PA", "Chest", "X-Ray"),
	("X-Ray Abdomen", "Abdomen", "X-Ray"),
	("X-Ray Spine", "Spine", "X-Ray"),
	("CT Brain Plain", "Brain", "CT"),
	("CT Chest with Contrast", "Chest", "CT"),
	("CT Abdomen Pelvis", "Abdomen", "CT"),
	("MRI Brain Plain", "Brain", "MRI"),
	("MRI Spine Lumbar", "Spine", "MRI"),
	("MRI Knee", "Knee", "MRI"),
	("Ultrasound Abdomen", "Abdomen", "Ultrasound"),
	("Ultrasound Pelvis", "Pelvis", "Ultrasound"),
	("Mammography Bilateral", "Chest", "Mammography"),
]


def _seed_imaging_templates() -> None:
	"""Seed a starter set of imaging Clinical Procedure Templates.

	Each row gets the procedure name, item_group="Services" (matches what we
	use for lab templates), and a short description with the modality &
	body part so the SPA order-intake list shows readable labels.
	"""
	item_group = "Services" if frappe.db.exists("Item Group", "Services") else None
	if not item_group:
		return
	for procedure, body_part, modality in _IMAGING_PROCEDURES:
		if frappe.db.exists("Clinical Procedure Template", procedure):
			continue
		try:
			frappe.get_doc({
				"doctype": "Clinical Procedure Template",
				"template": procedure,
				"item_group": item_group,
				"description": f"{modality} · {body_part}",
				"rate": 0,
			}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(title=f"ADMS: failed to seed Clinical Procedure Template {procedure}")


def _backfill_template_samples() -> None:
	"""Default any Lab Test Template that has no `sample` to "Blood".

	Without a sample on the template, Marley's `create_sample_doc` silently
	skips and no Sample Collection ever appears in the Collection worklist.
	Defaulting to Blood matches the most common lab order and is harmless
	for templates that should have used a different type — the lab manager
	can edit the template at any time.
	"""
	templates = frappe.get_all(
		"Lab Test Template",
		filters={"sample": ["in", ["", None]]},
		pluck="name",
	)
	for t in templates:
		try:
			# Lab Test Template.sample_uom links to "Lab Test UOM" — leave it
			# blank on backfill since stock sites ship with no volumetric
			# entries in that table. sample_qty is a plain Float.
			frappe.db.set_value(
				"Lab Test Template",
				t,
				{"sample": "Blood", "sample_qty": 5},
				update_modified=False,
			)
		except Exception:
			frappe.log_error(title=f"ADMS: failed to backfill sample on {t}")
