# Copyright (c) 2026, Azzir ADMS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class LabWorkflowSession(Document):
	def before_save(self):
		self.last_saved = now_datetime()
		if not self.workflow_started:
			self.workflow_started = now_datetime()
		if self.status == "Completed" and not self.workflow_completed:
			self.workflow_completed = now_datetime()
