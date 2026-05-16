from frappe.model.document import Document


class QCRun(Document):
	def before_save(self):
		# Compute z-score if SD provided
		if self.sd and self.sd > 0 and self.expected_value is not None and self.observed_value is not None:
			self.z_score = round((self.observed_value - self.expected_value) / self.sd, 3)
		# Derive result from Westgard flag if not set
		if self.westgard_flag in ("1-3s", "2-2s", "R-4s", "4-1s", "10-x"):
			self.result = "Fail"
		elif self.westgard_flag == "1-2s":
			self.result = "Warning"
