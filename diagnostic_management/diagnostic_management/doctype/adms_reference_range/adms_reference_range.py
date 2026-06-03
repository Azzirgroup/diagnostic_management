# Copyright (c) 2026, Azzir ADMS
"""ADMS Reference Range — one row in a Lab Test Template's reference table.
Each row is scoped by optional gender + age group; range_text is free-form
("13.0 - 17.0", "> 40", "< 200", "Negative") and is parsed at result entry
time to flag High / Low / Normal."""
import frappe
from frappe.model.document import Document


class ADMSReferenceRange(Document):
	pass
