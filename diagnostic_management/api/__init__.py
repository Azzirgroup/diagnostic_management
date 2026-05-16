# ADMS whitelisted API surface — every sub-module exports `@frappe.whitelist()`
# methods consumed by the Vue SPA. Sub-modules:
#
#   auth          : doctor self-registration / invite acceptance
#   session       : profile / role lookup for the SPA bootstrap
#   permission    : has_app_permission gate for the desk Apps launcher
#   dashboard     : KPI roll-ups for Lab Manager, Director, Doctor screens
#   patients      : patient search + rich profile detail
#   orders        : Service Request intake / worklist / catalog
#   collection    : phlebotomy worklist + collected/accession actions
#   sample        : sample accept / reject workflow
#   lab           : lab hub summary, verification queue, peer review
#   reagents      : Reagent Lot list / low stock / expiring soon / usage
#   instruments   : Lab Instrument list / monitor / state / heartbeat
#   qc            : QC Run submit / approve / reject
#   calibration   : Calibration Run log / due-soon
#   radiology     : reading worklist, pre-auth lifecycle, report editor
#   critical      : critical-result acknowledgement + Critical Finding Log
#   billing       : Sales Invoice queue + patient invoices + summary
#   analytics     : volume / quality KPIs + trend + section mix
#   audit         : Activity Log, critical audit trail, rejection log
#   doctor        : doctor portal — inbox, my patients, statements
#   settings      : per-user UI preferences
