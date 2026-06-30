"""Director Workspace + Lab Manager Workspace under Kanonas Diagnosis.

Mirrors the v15 genetest desk layout EXACTLY:
  - Hero chart (Monthly Revenue Trend, full width)
  - 4 KPI Number Cards in a row (col=3 each)
  - Section "cards" — each one renders a `Card Break` group from the links
    table as a clean header + link-list (NOT cramped shortcut tiles)

Frappe layout primer (so the JSON below makes sense):
    A workspace's `content` field is a JSON array of layout blocks.
    Each block is `{"id": "<random>", "type": "<type>", "data": {...}}`.
    Common types:
      "chart"        → renders a Dashboard Chart (chart_name + col)
      "number_card"  → renders a Number Card (number_card_name + col)
      "card"         → renders a LINKS Card Break group (card_name = the
                       Card Break's label; the Link rows that follow that
                       Card Break in `links` are shown beneath)
      "shortcut"     → renders a Shortcut tile (shortcut_name + col)
      "header"       → free-form HTML heading (text + col)
      "spacer"       → vertical breathing room (col=12)
    `col` is on a 12-column grid (col=3 → 4 per row, col=4 → 3 per row).

Idempotent. Called from after_install / after_migrate via setup/__init__.py.
"""

from __future__ import annotations

import json
import secrets

import frappe


PARENT = "Kanonas Diagnosis"


def install_director_and_lab_manager_workspaces() -> None:
	_ensure_number_cards()
	_ensure_dashboard_charts()
	_ensure_director_workspace()
	_ensure_lab_manager_workspace()


def _bid() -> str:
	# Each content block needs a unique id; matches the format Frappe's
	# workspace page-builder generates client-side.
	return secrets.token_hex(5)


# ---------------------------------------------------------------------------
# Number Cards (label IS the doc name — Number Card autonames from label)
# ---------------------------------------------------------------------------

_DIRECTOR_CARDS: list[dict] = [
	{
		"label": "Director — Today's Revenue",
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
		"label": "Director — Monthly Revenue",
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
		"label": "Director — Outstanding Receivables",
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
		"label": "Director — Tests Today",
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
		if frappe.db.exists("Number Card", spec["label"]):
			continue
		doc = frappe.new_doc("Number Card")
		for k, v in spec.items():
			doc.set(k, v)
		doc.is_public = 1
		doc.show_percentage_stats = 1
		doc.stats_time_interval = "Daily"
		doc.insert(ignore_permissions=True)
		print(f"  [workspaces] created Number Card {spec['label']!r}")


# ---------------------------------------------------------------------------
# Dashboard Chart — Monthly Revenue Trend (Sum on Sales Invoice grand_total,
# last 12 months, line chart). Dashboard Chart autonames from chart_name.
# ---------------------------------------------------------------------------

_REVENUE_TREND = {
	"chart_name": "Director — Monthly Revenue Trend",
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
# Section definitions
#
# Each section becomes a Card Break + Links in the `links` table, AND a
# `card` block in the content JSON. The Card Break's label IS the
# `card_name` referenced from content.
#
# Format: (card_label, [(label, link_to, link_type, optional onboard?), ...])
# Only items whose `link_to` actually resolves get rendered (so a site
# missing a particular report just skips it instead of throwing).
# ---------------------------------------------------------------------------

_DIRECTOR_SECTIONS: list[tuple[str, list[tuple[str, str, str]]]] = [
	("Revenue Intelligence", [
		("Sales by Test", "Sales Analytics", "Report"),
		("Sales by Customer", "Sales Analytics", "Report"),
		("Credit Customers", "Accounts Receivable", "Report"),
	]),
	("Lab Operations", [
		("Tests per Day", "Lab Test", "DocType"),
		("Turnaround Time", "Lab Test", "DocType"),
	]),
	("Inventory", [
		("Stock Balance", "Stock Balance", "Report"),
		("Batch Item Expiry Status", "Batch-Wise Balance History", "Report"),
		("Item Shortage Report", "Item Shortage Report", "Report"),
	]),
	("Financial Health", [
		("Accounts Receivable", "Accounts Receivable", "Report"),
		("Cash Flow", "Cash Flow", "Report"),
		("Sales Register", "Sales Register", "Report"),
		("Profitability Analysis", "Profitability Analysis", "Report"),
	]),
	("Assets and Equipment", [
		("Fixed Asset Register", "Fixed Asset Register", "Report"),
		("Asset Depreciation Ledger", "Asset Depreciation Ledger", "Report"),
	]),
	("Masters", [
		("Sales Invoice", "Sales Invoice", "DocType"),
		("Customer", "Customer", "DocType"),
	]),
]


_LAB_MGR_SECTIONS: list[tuple[str, list[tuple[str, str, str]]]] = [
	("Ordering", [
		("Purchase Order", "Purchase Order", "DocType"),
		("Purchase Receipt", "Purchase Receipt", "DocType"),
		("Purchase Invoice", "Purchase Invoice", "DocType"),
	]),
	("Accounting", [
		("Sales Invoice", "Sales Invoice", "DocType"),
		("Payment Entry", "Payment Entry", "DocType"),
	]),
	("Laboratory Reports", [
		# v15 had custom genetest reports here (Tests per Day / TAT Report /
		# Patient History / Billing Report) that don't exist on the new
		# site. Substitute the closest ERPNext / Healthcare equivalents.
		("Lab Tests", "Lab Test", "DocType"),
		("Lab Reports", "Lab Report", "DocType"),
		("Sample Collections", "Sample Collection", "DocType"),
		("Sales Register (Lab Billing)", "Sales Register", "Report"),
	]),
	("Revenue & Sales Reports", [
		("Sales Analytics", "Sales Analytics", "Report"),
		("Customer Ledger Summary", "Customer Ledger Summary", "Report"),
	]),
	("Stock & Inventory", [
		("Stock Balance", "Stock Balance", "Report"),
		("Batch-Wise Balance History", "Batch-Wise Balance History", "Report"),
	]),
	("Accounting Reports", [
		("Accounts Receivable", "Accounts Receivable", "Report"),
		("Cash Flow", "Cash Flow", "Report"),
		("Fixed Asset Register", "Fixed Asset Register", "Report"),
	]),
]


def _populate_section_links(ws, sections) -> list[str]:
	"""Append Card Break + Link rows to `ws.links` for each section, skipping
	any link whose target doesn't exist on this site. Returns the list of
	Card Break labels that ended up with at least one valid link (so the
	caller knows which ones to put into `content`)."""
	rendered: list[str] = []
	for card_label, items in sections:
		valid_items = [
			(lbl, lt, tp) for (lbl, lt, tp) in items
			if (tp == "Report" and frappe.db.exists("Report", lt))
			or (tp == "DocType" and frappe.db.exists("DocType", lt))
		]
		if not valid_items:
			continue
		ws.append("links", {"label": card_label, "type": "Card Break", "hidden": 0})
		for lbl, lt, tp in valid_items:
			ws.append("links", {
				"label": lbl, "link_to": lt, "link_type": tp,
				"type": "Link", "hidden": 0,
			})
		rendered.append(card_label)
	return rendered


# ---------------------------------------------------------------------------
# Director Workspace
# ---------------------------------------------------------------------------

def _ensure_director_workspace() -> None:
	name = "Director Workspace"
	exists = frappe.db.exists("Workspace", name)
	if exists:
		ws = frappe.get_doc("Workspace", name)
		# Wipe every child table — the v15-restored copy carries stale rows.
		ws.charts = []; ws.number_cards = []; ws.shortcuts = []
		ws.links = []; ws.quick_lists = []; ws.custom_blocks = []
		ws.parent_page = PARENT; ws.sequence_id = 15.0; ws.public = 1
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

	# Hero chart
	chart_name = _REVENUE_TREND["chart_name"]
	if frappe.db.exists("Dashboard Chart", chart_name):
		ws.append("charts", {"chart_name": chart_name, "label": "Monthly Revenue Trend"})

	# KPI cards
	for spec in _DIRECTOR_CARDS:
		if frappe.db.exists("Number Card", spec["label"]):
			ws.append("number_cards", {
				"number_card_name": spec["label"], "label": spec["label"],
			})

	# Section link groups
	rendered_sections = _populate_section_links(ws, _DIRECTOR_SECTIONS)

	# Build content JSON — chart, then 4 KPI cards, then section cards in
	# 3-per-row grid (col=4 each).
	content: list[dict] = []
	if frappe.db.exists("Dashboard Chart", chart_name):
		content.append({"id": _bid(), "type": "chart",
		                "data": {"chart_name": chart_name, "col": 12}})
	for spec in _DIRECTOR_CARDS:
		if frappe.db.exists("Number Card", spec["label"]):
			content.append({"id": _bid(), "type": "number_card",
			                "data": {"number_card_name": spec["label"], "col": 3}})
	content.append({"id": _bid(), "type": "spacer", "data": {"col": 12}})
	for card_label in rendered_sections:
		content.append({"id": _bid(), "type": "card",
		                "data": {"card_name": card_label, "col": 4}})
	ws.content = json.dumps(content)

	if ws.is_new():
		ws.insert(ignore_permissions=True)
	else:
		ws.save(ignore_permissions=True)
	print(f"  [workspaces] upserted {name!r}")


# ---------------------------------------------------------------------------
# Lab Manager Workspace
# ---------------------------------------------------------------------------

def _ensure_lab_manager_workspace() -> None:
	name = "Lab Manager Workspace"
	exists = frappe.db.exists("Workspace", name)
	if exists:
		ws = frappe.get_doc("Workspace", name)
		ws.charts = []; ws.number_cards = []; ws.shortcuts = []
		ws.links = []; ws.quick_lists = []; ws.custom_blocks = []
		ws.parent_page = PARENT; ws.sequence_id = 16.0; ws.public = 1
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

	rendered_sections = _populate_section_links(ws, _LAB_MGR_SECTIONS)

	# Layout: Ordering + Accounting as 2 cards side-by-side at the top
	# (col=6 each), then a header "Reports", then the 4 Reports sections
	# as 4 cards across (col=3 each, falling to 2 per row on tablet).
	content: list[dict] = []
	content.append({"id": _bid(), "type": "header",
	                "data": {"text": "<span class=\"h4\">LAB MANAGER</span>", "col": 12}})

	top_pair = [s for s in ("Ordering", "Accounting") if s in rendered_sections]
	for s in top_pair:
		content.append({"id": _bid(), "type": "card",
		                "data": {"card_name": s, "col": 6}})

	if any(s in rendered_sections for s in ("Laboratory Reports", "Revenue & Sales Reports",
	                                         "Stock & Inventory", "Accounting Reports")):
		content.append({"id": _bid(), "type": "spacer", "data": {"col": 12}})
		content.append({"id": _bid(), "type": "header",
		                "data": {"text": "<span class=\"h4\">Reports</span>", "col": 12}})
	for s in ("Laboratory Reports", "Revenue & Sales Reports",
	          "Stock & Inventory", "Accounting Reports"):
		if s in rendered_sections:
			content.append({"id": _bid(), "type": "card",
			                "data": {"card_name": s, "col": 3}})

	ws.content = json.dumps(content)

	if ws.is_new():
		ws.insert(ignore_permissions=True)
	else:
		ws.save(ignore_permissions=True)
	print(f"  [workspaces] upserted {name!r}")
