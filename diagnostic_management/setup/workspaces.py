"""Director Workspace + Lab Manager Workspace under Kanonas Diagnosis.

Mirrors the v15 genetest desk layout:

  Director Workspace
    Hero: Monthly Revenue Trend (line chart)
    KPI cards: Today's Revenue · Monthly Revenue · Outstanding Receivables ·
               Tests Today
    Sections: Revenue Intelligence · Lab Operations · Inventory ·
              Financial Health · Assets and Equipment · Masters

  Lab Manager Workspace
    Ordering: Purchase Order · Purchase Receipt · Purchase Invoice
    Accounting: Sales Invoice · Payment Entry
    Reports → Laboratory · Revenue & Sales · Stock & Inventory · Accounting

Idempotent: every helper checks for existence before inserting. Called from
hooks.after_install / after_migrate via setup/__init__.py.

Branch awareness: the KPI cards aggregate ACROSS branches (consolidated
totals). Per-branch deep-dive uses ERPNext's built-in Profit and Loss
Statement / Sales Register / Accounts Receivable reports — those gained
a Branch filter automatically when we registered the Accounting Dimension
in setup/accounting_dimension.py.
"""

from __future__ import annotations

import json

import frappe


PARENT = "Kanonas Diagnosis"


def install_director_and_lab_manager_workspaces() -> None:
	_ensure_number_cards()
	_ensure_dashboard_charts()
	_ensure_director_workspace()
	_ensure_lab_manager_workspace()


# ---------------------------------------------------------------------------
# Number Cards
# ---------------------------------------------------------------------------

_DIRECTOR_CARDS: list[dict] = [
	{
		"name": "DM Today's Revenue",
		"label": "Today's Revenue",
		"document_type": "Sales Invoice",
		"function": "Sum",
		"aggregate_function_based_on": "grand_total",
		"filters_json": json.dumps([
			["Sales Invoice", "docstatus", "=", 1],
			["Sales Invoice", "posting_date", "=", "Today"],
		]),
		"color": "#449CF0",
	},
	{
		"name": "DM Monthly Revenue",
		"label": "Monthly Revenue",
		"document_type": "Sales Invoice",
		"function": "Sum",
		"aggregate_function_based_on": "grand_total",
		"filters_json": json.dumps([
			["Sales Invoice", "docstatus", "=", 1],
			["Sales Invoice", "posting_date", "Timespan", "this month"],
		]),
		"color": "#29CD42",
	},
	{
		"name": "DM Outstanding Receivables",
		"label": "Outstanding Receivables",
		"document_type": "Sales Invoice",
		"function": "Sum",
		"aggregate_function_based_on": "outstanding_amount",
		"filters_json": json.dumps([
			["Sales Invoice", "docstatus", "=", 1],
			["Sales Invoice", "outstanding_amount", ">", 0],
		]),
		"color": "#FFC107",
	},
	{
		"name": "DM Tests Today",
		"label": "Tests Today",
		"document_type": "Lab Test",
		"function": "Count",
		"filters_json": json.dumps([
			["Lab Test", "creation", "Timespan", "today"],
		]),
		"color": "#9B59B6",
	},
]


def _ensure_number_cards() -> None:
	for spec in _DIRECTOR_CARDS:
		if frappe.db.exists("Number Card", spec["name"]):
			continue
		doc = frappe.new_doc("Number Card")
		for k, v in spec.items():
			doc.set(k, v)
		doc.is_public = 1
		doc.show_percentage_stats = 1
		doc.stats_time_interval = "Daily"
		doc.insert(ignore_permissions=True)
		print(f"  [workspaces] created Number Card {spec['name']!r}")


# ---------------------------------------------------------------------------
# Dashboard Chart — Monthly Revenue Trend
# ---------------------------------------------------------------------------

_REVENUE_TREND = {
	# Name = chart_name (Dashboard Chart autonames from chart_name field).
	# Prefixed with "DM —" to avoid colliding with anything already in the
	# tabDashboard Chart table from prior installs / fixtures.
	"chart_name": "DM — Monthly Revenue Trend",
	"chart_type": "Sum",
	"document_type": "Sales Invoice",
	"based_on": "posting_date",
	"value_based_on": "grand_total",
	"type": "Line",
	"timespan": "Last Year",
	"time_interval": "Monthly",
	"filters_json": json.dumps([["Sales Invoice", "docstatus", "=", 1]]),
	"is_public": 1,
}


def _ensure_dashboard_charts() -> None:
	if frappe.db.exists("Dashboard Chart", _REVENUE_TREND["chart_name"]):
		return
	doc = frappe.new_doc("Dashboard Chart")
	for k, v in _REVENUE_TREND.items():
		doc.set(k, v)
	doc.insert(ignore_permissions=True)
	print(f"  [workspaces] created Dashboard Chart {_REVENUE_TREND['chart_name']!r}")


# ---------------------------------------------------------------------------
# Director Workspace
# ---------------------------------------------------------------------------

_DIRECTOR_SHORTCUTS: list[tuple[str, str, str]] = [
	# (label, link_to, type) — type=DocType / Report / Page
	# Revenue Intelligence
	("Sales by Test", "Sales Analytics", "Report"),
	("Sales by Customer", "Sales Analytics", "Report"),
	("Credit Customers", "Accounts Receivable", "Report"),
	# Lab Operations
	("Tests per Day", "Lab Test", "DocType"),
	("Turnaround Time", "Lab Test", "DocType"),
	# Inventory
	("Stock Balance", "Stock Balance", "Report"),
	("Batch Item Expiry Status", "Batch-Wise Balance History", "Report"),
	("Item Shortage Report", "Item Shortage Report", "Report"),
	# Financial Health
	("Accounts Receivable", "Accounts Receivable", "Report"),
	("Cash Flow", "Cash Flow", "Report"),
	("Sales Register", "Sales Register", "Report"),
	("Profitability Analysis", "Profitability Analysis", "Report"),
	# Assets and Equipment
	("Fixed Asset Register", "Fixed Asset Register", "Report"),
	("Asset Depreciation Ledger", "Asset Depreciation Ledger", "Report"),
	# Masters
	("Sales Invoice", "Sales Invoice", "DocType"),
	("Customer", "Customer", "DocType"),
]


def _ensure_director_workspace() -> None:
	name = "Director Workspace"
	if frappe.db.exists("Workspace", name):
		# Refresh content (idempotent overlay) but keep `is_hidden` / `for_user`.
		# We clear EVERY child table — the v15-restored copy of this workspace
		# carries link rows pointing at reports that don't exist on the new
		# site (Sales by Test - Genetest, Genetest Receivable Breakdown, …),
		# and Frappe's save() validates those Link targets.
		ws = frappe.get_doc("Workspace", name)
		ws.charts = []
		ws.number_cards = []
		ws.shortcuts = []
		ws.links = []
		ws.quick_lists = []
		ws.custom_blocks = []
		ws.parent_page = PARENT
		ws.sequence_id = 15.0
		ws.public = 1
	else:
		ws = frappe.new_doc("Workspace")
		ws.name = name
		ws.title = "Director Workspace"
		ws.label = "Director Workspace"
		ws.module = "Diagnostic Management"
		ws.app = "diagnostic_management"
		ws.public = 1
		ws.parent_page = PARENT
		ws.sequence_id = 15.0
		ws.type = "Workspace"
		ws.icon = "graph-up-arrow"
	# Filter the cards/charts/shortcuts that won't resolve on this site (e.g.
	# Healthcare report wasn't installed, etc.) so the workspace insert
	# doesn't trip a LinkValidationError.
	chart = _REVENUE_TREND["chart_name"]
	if frappe.db.exists("Dashboard Chart", chart):
		ws.append("charts", {"chart_name": chart, "label": "Monthly Revenue Trend"})
	for spec in _DIRECTOR_CARDS:
		if frappe.db.exists("Number Card", spec["name"]):
			ws.append("number_cards", {"number_card_name": spec["name"], "label": spec["label"]})
	for label, link_to, link_type in _DIRECTOR_SHORTCUTS:
		# Skip shortcuts whose target doesn't exist on this site (e.g. some
		# ERPNext reports are gated by modules being installed).
		if link_type == "Report" and not frappe.db.exists("Report", link_to):
			continue
		if link_type == "DocType" and not frappe.db.exists("DocType", link_to):
			continue
		ws.append("shortcuts", {"label": label, "link_to": link_to, "type": link_type})
	# Workspace content is serialised JSON describing the layout grid. A flat
	# list of cards/shortcuts is enough — Frappe renders them in default order.
	ws.content = json.dumps(_build_director_content(ws))
	if ws.is_new():
		ws.insert(ignore_permissions=True)
	else:
		ws.save(ignore_permissions=True)
	print(f"  [workspaces] upserted {name!r}")


def _build_director_content(ws) -> list[dict]:
	"""Generate the workspace content (page-builder grid) JSON. Order matches
	the v15 layout: chart → number cards → shortcut sections."""
	content: list[dict] = []
	content.append({"type": "header", "data": {"text": "<h3>Director's Workspace</h3>", "col": 12}})
	for c in ws.charts:
		content.append({"type": "chart", "data": {"chart_name": c.chart_name, "col": 12}})
	for c in ws.number_cards:
		content.append({"type": "card", "data": {"card_name": c.number_card_name, "col": 3}})
	# Section headers + shortcuts
	sections = [
		("Revenue Intelligence", ["Sales by Test", "Sales by Customer", "Credit Customers"]),
		("Lab Operations", ["Tests per Day", "Turnaround Time"]),
		("Inventory", ["Stock Balance", "Batch Item Expiry Status", "Item Shortage Report"]),
		("Financial Health", ["Accounts Receivable", "Cash Flow", "Sales Register", "Profitability Analysis"]),
		("Assets and Equipment", ["Fixed Asset Register", "Asset Depreciation Ledger"]),
		("Masters", ["Sales Invoice", "Customer"]),
	]
	existing_labels = {s.label for s in ws.shortcuts}
	for title, labels in sections:
		content.append({"type": "header", "data": {"text": f"<h5>{title}</h5>", "col": 12}})
		for lbl in labels:
			if lbl in existing_labels:
				content.append({"type": "shortcut", "data": {"shortcut_name": lbl, "col": 3}})
	return content


# ---------------------------------------------------------------------------
# Lab Manager Workspace
# ---------------------------------------------------------------------------

_LAB_MGR_SHORTCUTS: list[tuple[str, str, str]] = [
	# Ordering
	("Purchase Order", "Purchase Order", "DocType"),
	("Purchase Receipt", "Purchase Receipt", "DocType"),
	("Purchase Invoice", "Purchase Invoice", "DocType"),
	# Accounting
	("Sales Invoice", "Sales Invoice", "DocType"),
	("Payment Entry", "Payment Entry", "DocType"),
]

_LAB_MGR_LINKS: list[tuple[str, str, str, str]] = [
	# (section, label, link_to, type)
	("Laboratory Reports", "Tests per Day", "Lab Test", "DocType"),
	("Laboratory Reports", "TAT Report", "Lab Test", "DocType"),
	("Laboratory Reports", "Patient History", "Patient History", "Report"),
	("Laboratory Reports", "Billing Report", "Billing Report", "Report"),
	("Revenue & Sales Reports", "Sales Analytics", "Sales Analytics", "Report"),
	("Revenue & Sales Reports", "Customer Ledger Summary", "Customer Ledger Summary", "Report"),
	("Stock & Inventory", "Stock Balance", "Stock Balance", "Report"),
	("Stock & Inventory", "Batch-Wise Balance History", "Batch-Wise Balance History", "Report"),
	("Accounting Reports", "Accounts Receivable", "Accounts Receivable", "Report"),
	("Accounting Reports", "Cash Flow", "Cash Flow", "Report"),
	("Accounting Reports", "Fixed Asset Register", "Fixed Asset Register", "Report"),
]


def _ensure_lab_manager_workspace() -> None:
	name = "Lab Manager Workspace"
	if frappe.db.exists("Workspace", name):
		ws = frappe.get_doc("Workspace", name)
		ws.shortcuts = []
		ws.links = []
		ws.charts = []
		ws.number_cards = []
		ws.quick_lists = []
		ws.custom_blocks = []
		ws.parent_page = PARENT
		ws.sequence_id = 16.0
		ws.public = 1
	else:
		ws = frappe.new_doc("Workspace")
		ws.name = name
		ws.title = "Lab Manager Workspace"
		ws.label = "Lab Manager Workspace"
		ws.module = "Diagnostic Management"
		ws.app = "diagnostic_management"
		ws.public = 1
		ws.parent_page = PARENT
		ws.sequence_id = 16.0
		ws.type = "Workspace"
		ws.icon = "tool"

	for label, link_to, link_type in _LAB_MGR_SHORTCUTS:
		if link_type == "DocType" and not frappe.db.exists("DocType", link_to):
			continue
		ws.append("shortcuts", {"label": label, "link_to": link_to, "type": link_type})

	# Links table: section headers as "Card Break", entries as "Link"
	current_section = None
	for section, label, link_to, link_type in _LAB_MGR_LINKS:
		if link_type == "Report" and not frappe.db.exists("Report", link_to):
			continue
		if link_type == "DocType" and not frappe.db.exists("DocType", link_to):
			continue
		if section != current_section:
			ws.append("links", {"label": section, "type": "Card Break", "hidden": 0})
			current_section = section
		ws.append("links", {
			"label": label, "link_to": link_to, "link_type": link_type, "type": "Link",
		})

	ws.content = json.dumps(_build_lab_manager_content(ws))
	ws.save(ignore_permissions=True) if ws.get("__islocal") is False else ws.insert(ignore_permissions=True)
	print(f"  [workspaces] upserted {name!r}")


def _build_lab_manager_content(ws) -> list[dict]:
	content: list[dict] = [
		{"type": "header", "data": {"text": "<h3>LAB MANAGER</h3>", "col": 12}},
		{"type": "header", "data": {"text": "<h5>Ordering</h5>", "col": 6}},
		{"type": "header", "data": {"text": "<h5>Accounting</h5>", "col": 6}},
	]
	ordering = {"Purchase Order", "Purchase Receipt", "Purchase Invoice"}
	accounting = {"Sales Invoice", "Payment Entry"}
	for s in ws.shortcuts:
		col = 2 if s.label in ordering else 3 if s.label in accounting else 3
		content.append({"type": "shortcut", "data": {"shortcut_name": s.label, "col": col}})
	content.append({"type": "header", "data": {"text": "<h4>Reports</h4>", "col": 12}})
	return content
