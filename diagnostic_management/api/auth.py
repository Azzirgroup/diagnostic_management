import frappe


@frappe.whitelist(allow_guest=True)
def accept_doctor_invite(
	invite_code: str,
	full_name: str,
	email: str,
	phone: str | None = None,
	license: str | None = None,
	password: str | None = None,
) -> dict:
	"""Stub for the doctor self-registration flow.

	The full implementation lives behind a Doctor Invite doctype that will
	land in a later phase. For now we validate the basics and create a
	disabled User the System Manager must approve, so the form behaves
	correctly end-to-end without an open registration hole.
	"""
	if not invite_code or len(invite_code) < 6:
		frappe.throw("Invalid invite code")

	if frappe.db.exists("User", email):
		frappe.throw("A user with this email already exists.")

	user = frappe.get_doc({
		"doctype": "User",
		"email": email,
		"first_name": full_name.split(" ")[0],
		"last_name": " ".join(full_name.split(" ")[1:]) or "",
		"username": email.split("@")[0],
		"mobile_no": phone,
		"enabled": 0,  # pending admin approval
		"user_type": "Website User",
		"new_password": password,
	})
	user.insert(ignore_permissions=True)

	# Record the requested invite + license so the admin can verify before enabling.
	user.add_comment(
		"Comment",
		text=(
			f"<b>Doctor self-registration</b><br>"
			f"Invite code: {frappe.utils.escape_html(invite_code)}<br>"
			f"License: {frappe.utils.escape_html(license or '')}"
		),
	)
	return {"ok": True, "user": user.name}
