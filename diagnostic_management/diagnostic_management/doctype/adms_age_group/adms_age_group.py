# Copyright (c) 2026, Azzir ADMS
"""ADMS Age Group — named, reusable age bands (Newborn / Child / Adult / etc.)
that drive reference-range selection on Lab Test Templates. A row stores a
min/max age and a unit (Days / Months / Years); the result entry / Lab Report
builder picks the row whose band contains the patient's age."""
import frappe
from frappe.model.document import Document


class ADMSAgeGroup(Document):
	def validate(self):
		if self.min_age is not None and self.max_age is not None and float(self.min_age) > float(self.max_age):
			frappe.throw("Min Age cannot be greater than Max Age")
