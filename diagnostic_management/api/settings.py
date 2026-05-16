"""User-level settings persistence (preferences stored on the User record)."""

import json

import frappe


# Map of user-facing keys → User table fields (where supported), else stored in
# the User.defaults JSON via frappe.defaults so it survives migrations.
USER_FIELDS = {
	"language": "language",
	"time_zone": "time_zone",
	"user_image": "user_image",
	"theme": "desk_theme",
}


@frappe.whitelist()
def get() -> dict:
	"""Return the SPA-relevant user preferences."""
	user = frappe.get_doc("User", frappe.session.user)
	out: dict = {k: getattr(user, v, None) for k, v in USER_FIELDS.items()}
	out["roles"] = [r.role for r in (user.get("roles") or [])]
	# Extra prefs we keep in DefaultValue (so we don't add custom fields).
	for key in ("home_page_module", "result_density", "preferred_branch"):
		out[key] = frappe.defaults.get_user_default(key, frappe.session.user) or None
	return out


@frappe.whitelist()
def update(payload: dict | str) -> dict:
	if isinstance(payload, str):
		try:
			payload = json.loads(payload)
		except Exception:
			frappe.throw("Invalid payload")
	user = frappe.get_doc("User", frappe.session.user)
	dirty = False
	for k, field in USER_FIELDS.items():
		if k in payload and hasattr(user, field):
			setattr(user, field, payload[k])
			dirty = True
	if dirty:
		user.save(ignore_permissions=True)
	for key in ("home_page_module", "result_density", "preferred_branch"):
		if key in payload:
			frappe.defaults.set_user_default(key, payload[key], frappe.session.user)
	return {"ok": True}
