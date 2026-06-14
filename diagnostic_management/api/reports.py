"""Analytics backend for the /reports SPA tab.

Aggregations the page renders as charts + tables:
  - top-line KPIs (reports, tests, samples, revenue, P&L)
  - daily activity trend over the chosen window
  - top tests by volume + revenue
  - sample type breakdown
  - billing summary (paid vs outstanding, payment-mode mix)
  - profit & loss (revenue from Sales Invoices vs lab consumable cost
    inferred from Manufacture Stock Entries created via the Work-Order
    automation that ships with this app)

All endpoints accept `days` (window size, default 30). Sales Invoice queries
guard against missing fields so the page renders even on a fresh install.
"""
from __future__ import annotations

import frappe
from frappe.utils import add_days, flt, getdate, today


def _window(days: int = 30) -> tuple[str, str]:
	to = today()
	frm = add_days(to, -int(days or 30))
	return str(frm), str(to)


@frappe.whitelist()
def overview(days: int = 30) -> dict:
	"""Top-line KPIs for the Reports header (totals over the window)."""
	frm, to = _window(days)
	# Lab Reports
	reports = frappe.db.count("Lab Report", {"report_date": ["between", [frm, to]]}) if frappe.db.exists("DocType", "Lab Report") else 0
	# Lab Tests (submitted) — Marley's docstatus=1 means submitted/Completed.
	tests = frappe.db.count("Lab Test", {"creation": [">=", frm], "docstatus": 1})
	# Sample Collections
	samples = frappe.db.count("Sample Collection", {"creation": [">=", frm]})
	# Revenue + outstanding from Sales Invoices in window
	rev = frappe.db.sql(
		"""SELECT
			COALESCE(SUM(grand_total),0) AS billed,
			COALESCE(SUM(grand_total - outstanding_amount),0) AS collected,
			COALESCE(SUM(outstanding_amount),0) AS outstanding,
			COUNT(*) AS invoice_count
		FROM `tabSales Invoice`
		WHERE docstatus = 1 AND posting_date BETWEEN %s AND %s""",
		(frm, to), as_dict=True,
	)[0]
	# Lab-consumable cost: post-rework the issue happens through a Material
	# Issue stock entry (no Work Order). We still include the legacy
	# 'Manufacture' type so historical data continues to count.
	cost = frappe.db.sql(
		"""SELECT COALESCE(SUM(total_outgoing_value),0) AS cost
		FROM `tabStock Entry`
		WHERE docstatus = 1
		  AND stock_entry_type IN ('Material Issue','Manufacture')
		  AND posting_date BETWEEN %s AND %s""",
		(frm, to), as_dict=True,
	)[0]
	gross_profit = flt(rev.billed) - flt(cost.cost)
	margin_pct = (gross_profit / flt(rev.billed) * 100.0) if rev.billed else 0.0

	return {
		"window": {"from": frm, "to": to, "days": int(days or 30)},
		"reports": int(reports), "tests": int(tests), "samples": int(samples),
		"revenue_billed": flt(rev.billed),
		"revenue_collected": flt(rev.collected),
		"outstanding": flt(rev.outstanding),
		"invoice_count": int(rev.invoice_count or 0),
		"cogs": flt(cost.cost),
		"gross_profit": gross_profit,
		"margin_pct": margin_pct,
	}


@frappe.whitelist()
def activity_trend(days: int = 30) -> list[dict]:
	"""Daily activity over the window: reports / tests / samples / revenue."""
	frm, to = _window(days)
	rows = frappe.db.sql(
		"""SELECT d.day,
			COALESCE(r.cnt,0)   AS reports,
			COALESCE(lt.cnt,0)  AS tests,
			COALESCE(sc.cnt,0)  AS samples,
			COALESCE(si.amt,0)  AS revenue
		FROM (
			SELECT DATE_ADD(%s, INTERVAL n DAY) AS day
			FROM (
				SELECT a.N + b.N*10 + c.N*100 AS n
				FROM (SELECT 0 N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) a
				CROSS JOIN (SELECT 0 N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) b
				CROSS JOIN (SELECT 0 N UNION SELECT 1) c
			) numbers
			WHERE DATE_ADD(%s, INTERVAL n DAY) <= %s
		) d
		LEFT JOIN (SELECT report_date AS day, COUNT(*) AS cnt FROM `tabLab Report` WHERE report_date BETWEEN %s AND %s GROUP BY report_date) r  ON r.day  = d.day
		LEFT JOIN (SELECT DATE(creation)  AS day, COUNT(*) AS cnt FROM `tabLab Test`           WHERE docstatus = 1 AND DATE(creation)  BETWEEN %s AND %s GROUP BY DATE(creation))  lt ON lt.day = d.day
		LEFT JOIN (SELECT DATE(creation)  AS day, COUNT(*) AS cnt FROM `tabSample Collection`  WHERE DATE(creation)  BETWEEN %s AND %s GROUP BY DATE(creation))  sc ON sc.day = d.day
		LEFT JOIN (SELECT posting_date    AS day, SUM(grand_total) AS amt FROM `tabSales Invoice` WHERE docstatus = 1 AND posting_date BETWEEN %s AND %s GROUP BY posting_date) si ON si.day = d.day
		ORDER BY d.day ASC""",
		(frm, frm, to, frm, to, frm, to, frm, to, frm, to), as_dict=True,
	)
	for r in rows:
		r["day"] = str(r["day"])
		r["reports"] = int(r["reports"] or 0)
		r["tests"] = int(r["tests"] or 0)
		r["samples"] = int(r["samples"] or 0)
		r["revenue"] = flt(r["revenue"])
	return rows


@frappe.whitelist()
def top_tests(days: int = 30, limit: int = 10) -> list[dict]:
	"""Top tests by Lab Test creation volume + revenue from invoiced templates."""
	frm, to = _window(days)
	rows = frappe.db.sql(
		"""SELECT lt.template AS template,
			COUNT(*) AS count,
			COALESCE(MAX(ltt.lab_test_rate),0) AS rate,
			COALESCE(MAX(ltt.department), 'General') AS department
		FROM `tabLab Test` lt
		LEFT JOIN `tabLab Test Template` ltt ON ltt.name = lt.template
		WHERE lt.docstatus = 1 AND DATE(lt.creation) BETWEEN %s AND %s
		GROUP BY lt.template
		ORDER BY count DESC
		LIMIT %s""",
		(frm, to, int(limit)), as_dict=True,
	)
	for r in rows:
		r["count"] = int(r["count"])
		r["rate"] = flt(r["rate"])
		r["revenue"] = flt(r["count"]) * flt(r["rate"])
	return rows


@frappe.whitelist()
def sample_mix(days: int = 30) -> list[dict]:
	"""Sample-type breakdown over the window (Blood / Urine / etc)."""
	frm, to = _window(days)
	rows = frappe.db.sql(
		"""SELECT COALESCE(sample,'(unknown)') AS sample_type, COUNT(*) AS count
		FROM `tabSample Collection`
		WHERE DATE(creation) BETWEEN %s AND %s
		GROUP BY sample
		ORDER BY count DESC""",
		(frm, to), as_dict=True,
	)
	for r in rows:
		r["count"] = int(r["count"])
	return rows


@frappe.whitelist()
def billing_summary(days: int = 30) -> dict:
	"""Billing aggregates for the financial card: paid vs outstanding, by mode."""
	frm, to = _window(days)
	mode_mix = frappe.db.sql(
		"""SELECT COALESCE(spd.mode_of_payment,'(none)') AS mode,
			COALESCE(SUM(spd.amount),0) AS amount
		FROM `tabSales Invoice Payment` spd
		JOIN `tabSales Invoice` si ON si.name = spd.parent
		WHERE si.docstatus = 1 AND si.posting_date BETWEEN %s AND %s
		GROUP BY spd.mode_of_payment
		ORDER BY amount DESC""",
		(frm, to), as_dict=True,
	)
	totals = frappe.db.sql(
		"""SELECT
			COALESCE(SUM(grand_total),0)        AS billed,
			COALESCE(SUM(outstanding_amount),0) AS outstanding,
			COALESCE(SUM(grand_total - outstanding_amount),0) AS collected,
			COUNT(*) AS invoices
		FROM `tabSales Invoice`
		WHERE docstatus = 1 AND posting_date BETWEEN %s AND %s""",
		(frm, to), as_dict=True,
	)[0]
	return {
		"billed": flt(totals.billed),
		"collected": flt(totals.collected),
		"outstanding": flt(totals.outstanding),
		"invoices": int(totals.invoices or 0),
		"mode_mix": [{"mode": r["mode"], "amount": flt(r["amount"])} for r in mode_mix],
	}


@frappe.whitelist()
def profit_and_loss(days: int = 30) -> dict:
	"""Simple P&L: revenue (billed SI grand_total) − COGS (Manufacture stock
	entries from the Work-Order automation). Returns daily series + totals."""
	frm, to = _window(days)
	rev = frappe.db.sql(
		"""SELECT posting_date AS day, COALESCE(SUM(grand_total),0) AS amt
		FROM `tabSales Invoice`
		WHERE docstatus = 1 AND posting_date BETWEEN %s AND %s
		GROUP BY posting_date""",
		(frm, to), as_dict=True,
	)
	cogs = frappe.db.sql(
		"""SELECT posting_date AS day, COALESCE(SUM(total_outgoing_value),0) AS amt
		FROM `tabStock Entry`
		WHERE docstatus = 1
		  AND stock_entry_type IN ('Material Issue','Manufacture')
		  AND posting_date BETWEEN %s AND %s
		GROUP BY posting_date""",
		(frm, to), as_dict=True,
	)
	rev_by = {str(r["day"]): flt(r["amt"]) for r in rev}
	cogs_by = {str(r["day"]): flt(r["amt"]) for r in cogs}
	days_iter: list[str] = []
	d = getdate(frm)
	end = getdate(to)
	while d <= end:
		days_iter.append(str(d))
		d = add_days(d, 1)
	series = [{
		"day": d,
		"revenue": rev_by.get(d, 0.0),
		"cogs": cogs_by.get(d, 0.0),
		"profit": rev_by.get(d, 0.0) - cogs_by.get(d, 0.0),
	} for d in days_iter]
	total_rev = sum(s["revenue"] for s in series)
	total_cogs = sum(s["cogs"] for s in series)
	return {
		"series": series,
		"revenue": total_rev,
		"cogs": total_cogs,
		"profit": total_rev - total_cogs,
		"margin_pct": (total_rev - total_cogs) / total_rev * 100.0 if total_rev else 0.0,
	}
