import frappe


ADMS_ROLES = [
	"Receptionist",
	"Phlebotomist",
	"Sample Receiver",
	"Lab Technician",
	"Lab Quality Officer",
	"Pathologist",
	"Lab Manager",
	"Urgent Review Officer",
	"Radiology Technologist",
	"Radiologist",
	"Radiology Manager",
	"Diagnostic Director",
	"Billing Officer",
	"Insurance Officer",
	"Referring Doctor",
	"Auditor",
]


def install_roles():
	"""Create the ADMS-specific roles. Idempotent."""
	for r in ADMS_ROLES:
		if not frappe.db.exists("Role", r):
			frappe.get_doc({
				"doctype": "Role",
				"role_name": r,
				"desk_access": 0 if r in {"Referring Doctor", "Auditor"} else 1,
			}).insert(ignore_permissions=True)
