import frappe


@frappe.whitelist()
def profile() -> dict:
	"""Return the bare-minimum profile the SPA needs at boot.

	Shape:
	    name: User.name (the email-style id)
	    email: User.email
	    full_name: User.full_name
	    user_image: User.user_image (may be None)
	    roles: list[str] — flat list of role names assigned to the user
	"""
	if frappe.session.user == "Guest":
		frappe.throw("Not logged in", frappe.AuthenticationError)

	user = frappe.get_doc("User", frappe.session.user)
	roles = [r.role for r in user.get("roles") or []]
	return {
		"name": user.name,
		"email": user.email,
		"full_name": user.full_name or user.first_name or user.name,
		"user_image": user.user_image,
		"roles": roles,
	}
