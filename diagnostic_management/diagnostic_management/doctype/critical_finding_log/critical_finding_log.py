import frappe
from frappe.model.document import Document


class CriticalFindingLog(Document):
	def before_save(self):
		if self.acknowledged_by and not self.acknowledged_at:
			self.acknowledged_at = frappe.utils.now_datetime()
		if self.acknowledged_at and self.status == "Detected":
			self.status = "Acknowledged"
