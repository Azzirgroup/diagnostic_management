import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ADMSStockAlert(Document):
	def before_insert(self):
		if not self.alert_date:
			self.alert_date = now_datetime()
		if not self.status:
			self.status = "Open"


@frappe.whitelist()
def acknowledge(name: str) -> dict:
	"""Mark a Stock Alert as Acknowledged with timestamp + actor."""
	doc = frappe.get_doc("ADMS Stock Alert", name)
	doc.db_set("status", "Acknowledged")
	doc.db_set("acknowledged_by", frappe.session.user)
	doc.db_set("acknowledged_at", now_datetime())
	return {"ok": True, "name": name, "status": "Acknowledged"}


@frappe.whitelist()
def resolve(name: str) -> dict:
	"""Mark a Stock Alert as Resolved (restocked / superseded)."""
	doc = frappe.get_doc("ADMS Stock Alert", name)
	doc.db_set("status", "Resolved")
	if not doc.acknowledged_at:
		doc.db_set("acknowledged_by", frappe.session.user)
		doc.db_set("acknowledged_at", now_datetime())
	return {"ok": True, "name": name, "status": "Resolved"}
