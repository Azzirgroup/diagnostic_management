"""Barcode / quick-lookup resolver for the SPA.

Mirrors the previous system's `resolve_barcode`: take a scanned code (or typed
id) and return the SPA route that opens the matching record. Scanners type the
value fast and emit Enter, so the SPA calls this on Enter and navigates.
"""

import frappe


# Doctype → SPA route template. Only doctypes the SPA can actually open.
_ROUTES = {
	"Sample Collection": "/lab/sample/{name}",
	"Service Request": "/orders/{name}",
	"Patient": "/patients/{name}",
	"Sales Invoice": "/billing/{name}",
}


def _hit(doctype: str, name: str) -> dict:
	return {
		"found": True,
		"doctype": doctype,
		"name": name,
		"route": _ROUTES[doctype].format(name=name),
	}


@frappe.whitelist()
def resolve(code: str) -> dict:
	"""Resolve a scanned code to {found, doctype, name, route}."""
	code = (code or "").strip()
	if not code:
		return {"found": False}

	# 1) Specimen label scans carry the Sample Collection.barcode value, not
	#    the document name — match that first.
	sc = frappe.db.get_value("Sample Collection", {"barcode": code}, "name")
	if sc:
		return _hit("Sample Collection", sc)

	# 2) Exact document name across the routable doctypes (covers HSR-…,
	#    HLC-SC-…, HLC-PAT-…, ACC-SINV-… etc.).
	for dt in ("Sample Collection", "Service Request", "Patient", "Sales Invoice"):
		if frappe.db.exists(dt, code):
			return _hit(dt, code)

	# 3) Lab Test isn't a SPA page — route to its order (or its sample).
	if frappe.db.exists("Lab Test", code):
		lt = frappe.db.get_value("Lab Test", code, ["service_request", "sample"], as_dict=True) or {}
		if lt.get("service_request") and frappe.db.exists("Service Request", lt["service_request"]):
			return _hit("Service Request", lt["service_request"])
		if lt.get("sample") and frappe.db.exists("Sample Collection", lt["sample"]):
			return _hit("Sample Collection", lt["sample"])

	return {"found": False, "code": code}
