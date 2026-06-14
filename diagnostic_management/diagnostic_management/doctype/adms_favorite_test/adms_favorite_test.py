# Copyright (c) 2026, Azzir ADMS
"""ADMS Favorite Test — per-user starred test/procedure templates.

A small relation between User and a template (Lab Test Template or Clinical
Procedure Template). Powers the "Favorites" tab in the Order Intake test
picker. Uniqueness on (user, template_dt, template_dn) is enforced in code
(see api.orders.toggle_favorite).
"""
import frappe
from frappe.model.document import Document


class ADMSFavoriteTest(Document):
	pass
