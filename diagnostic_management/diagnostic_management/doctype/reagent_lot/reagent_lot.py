import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today


class ReagentLot(Document):
	def before_save(self):
		self._auto_status()

	def _auto_status(self):
		if self.status in ("Quarantine", "Depleted"):
			return
		if self.expiry_date and getdate(self.expiry_date) < getdate(today()):
			self.status = "Expired"
			return
		if (self.quantity_on_hand or 0) <= 0:
			self.status = "Depleted"
			return
		if (self.quantity_on_hand or 0) <= (self.quantity_received or 0) * 0.2:
			self.status = "Low Stock"
			return
		self.status = "Active"
