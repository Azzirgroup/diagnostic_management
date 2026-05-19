from frappe.model.document import Document


class DoctorStatement(Document):
	def before_save(self):
		total = self.total_billed or 0
		pct = self.commission_pct or 0
		self.commission_amount = round(total * pct / 100.0, 2) if pct else (self.commission_amount or 0)
		self.net_payable = round((self.commission_amount or 0) - (self.tax_amount or 0), 2)
