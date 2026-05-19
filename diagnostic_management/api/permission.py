import frappe


def has_app_permission():
	"""Decides whether the current user sees the Diagnostic Management tile
	on the desk Apps launcher.

	Allow anyone with any ADMS role, plus System Manager and Administrator.
	"""
	allowed = {
		"System Manager", "Administrator",
		"Healthcare Administrator", "Physician", "Nursing User",
		"Laboratory User", "LabTest Approver",
		# ADMS roles
		"Receptionist", "Phlebotomist", "Sample Receiver", "Lab Technician",
		"Lab Quality Officer", "Pathologist", "Lab Manager",
		"Radiology Technologist", "Radiologist", "Radiology Manager",
		"Diagnostic Director", "Billing Officer", "Insurance Officer",
		"Referring Doctor", "Auditor",
	}
	roles = set(frappe.get_roles())
	return bool(roles & allowed)
