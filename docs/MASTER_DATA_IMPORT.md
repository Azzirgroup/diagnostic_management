# Master Data Import — Architecture & Order

Goal: take a Frappe / ERPNext / Healthcare / ADMS / HRMS backup, extract
**only master data** (no transactions, no GL Entries, no Stock Ledger), and
load it into a fresh empty site. Transactional history stays in the backup
file for archival reference; the new site starts at zero.

---

## 1. Pre-flight (one-off)

On the destination site (`genetest.com`):

1. Install apps in this order — each depends on the previous:
   `frappe` → `erpnext` → `payments` → `helpdesk` → `hrms` → `healthcare` → `diagnostic_management` → `telephony`
2. Confirm system-seed tables already exist (Currency, Country, UOM, Role,
   default Customer Group "All Customer Groups", default Territory "All
   Territories"). These come automatically with `bench install-app`.

A separate **stage site** (`master-stage.com`) hosts the restored backup
read-only — we only query it for master-data export, never write.

---

## 2. The import is layered. Each layer must complete before the next.

Order is dictated by **link dependencies**: a Customer can't insert if its
Customer Group doesn't exist; a POS Profile can't insert if its Company,
Warehouse, Mode of Payment, and write-off Account don't exist.

### Layer 0 — System-shared lookups (skip if already seeded)
- Currency, Country, UOM, Brand, Role
- Lab Test UOM, Sensitivity, Antibiotic, Sample Type, Body Part

### Layer 1 — Tenant root
- **Company** (`Genetest Diagnostic Limited`) — **must be first**.
  ERPNext auto-creates the default Chart of Accounts, default Cost Center,
  default Warehouse, and a few default Accounts on Company insert. Re-create
  the Company exactly as the backup had it (currency, abbreviation, country,
  fiscal year).
- **Fiscal Year**
- **Domain Settings** (which domains are active — Healthcare, Manufacturing,
  etc.)

### Layer 2 — Chart structure (mostly auto-created by Layer 1, but
diff + patch)
- **Account** (full Chart of Accounts as the backup had it — names, parent,
  account_type, account_currency)
- **Cost Center** (Main, plus any branch-specific cost centers)
- **Warehouse Type / Warehouse** (Finished Goods, Reagent Store, etc.)
- **Account Settings** (single)

### Layer 3 — Org / Geographic
- **Branch** (`UMC`, `PMC`, `Nairobi`, `Test` …)
- **Department** (HRMS — Medical Departments are separate, layered later)
- **Designation**
- **Territory** (extra leaves under "All Territories")
- **Customer Group** (e.g. `Cash Patients`, `Insurance`, `Cash Client 10%` …)
- **Supplier Group**
- **Item Group** (Lab Tests, Reagents, Consumables, Services …)
- **Brand**

### Layer 4 — People (depends on Layer 3 for branch/group lookups)
- **User** — including our custom `branch` field, role assignments
- **Employee** (HRMS) — links to User, Branch, Department
- **Healthcare Practitioner** — links to User, Department; carries our
  ADMS custom fields (practitioner_role, signature, etc.)
- **Customer** — links to Customer Group + Territory
- **Supplier** — links to Supplier Group
- **Patient** — links to Customer (created in Layer 4 first), Healthcare
  Settings, Branch. **Decision needed**: include or skip Patient (PHI).
  Default: include as master, since clinical history depends on stable
  patient identity.

### Layer 5 — Payment & POS infrastructure
- **Mode of Payment** — links to Account
- **Mode of Payment Account** (child table, per-Company)
- **POS Profile** — links to Company, Warehouse, Mode of Payment, Account,
  Branch. Carries our `branch` Custom Field.

### Layer 6 — Catalog
- **Sample Type** (Healthcare)
- **Body Part** (Healthcare)
- **Medical Department** (Healthcare)
- **Lab Test Template** — links to Item Group, Sample Type, Medical
  Department, UOM. Carries ADMS custom fields (LOINC, TAT, reference ranges,
  custom_comment, etc.) and child table `custom_reference_ranges` (ADMS
  Reference Range rows).
- **Lab Instrument** (ADMS)
- **Reagent Lot** — borderline (audit / consumable); usually treated as
  master because it represents a procured item, not an event.
- **Item** — links to Item Group, default Warehouse, UOM. Every Lab Test
  Template has an auto-created Item (created lazily by
  `_ensure_item_for_template`); we re-create those upfront so billing works
  immediately.
- **Item Price** — links to Item + Price List
- **Price List** — Standard Buying, Standard Selling, plus any custom ones

### Layer 7 — ADMS-specific masters
- **ADMS Age Group**
- **ADMS Reference Range** (often embedded as child of Lab Test Template,
  but standalone master rows can exist too)
- **ADMS Favorite Test** (per-user)
- **Code System** (LOINC/SNOMED/ICD-10 placeholders)
- **Doctor Statement** template (if present in backup)

### Layer 8 — Print + comms
- **Letter Head** (e.g. `Genetest Letterhead`)
- **Print Format** (`Genetest Lab Report`, `Genetest Sales Invoice`,
  custom ADMS print formats)
- **Email Account** / **SMS Settings** / **WhatsApp Settings**
  (single docs — decision needed: copy creds verbatim or blank them out
  so the new system doesn't accidentally send live messages on test data)

### Layer 9 — Singles (configuration)
- **Healthcare Settings** — link_customer_to_patient, default Practitioner,
  fee defaults
- **Accounts Settings** — auto_accounting_for_stock, etc.
- **Stock Settings** — default Warehouse, valuation method
- **Selling Settings** — naming series flag, etc.
- **Buying Settings**
- **POS Settings** — invoice_type, post_change_gl_entries
- **Website Settings** — `home_page` (we reset this to "login" on restored sites)
- **Global Defaults** — default_currency, default_company, etc.

### Layer 10 — System overlays (re-installed via app setup, NOT copied)
- **Custom Field** — re-installed by `diagnostic_management.setup.custom_fields.install_custom_fields()` on `bench migrate`
- **Property Setter** — re-installed by our setup helpers
- **Workspace** — installed by `setup.workspaces.install_director_and_lab_manager_workspaces()`
- **Number Card / Dashboard Chart** — same
- **Role** — installed by `setup.roles.install_roles()`
- **Accounting Dimension** (Branch) — installed by `setup.accounting_dimension.ensure_branch_accounting_dimension()`

These do **not** come from the backup; they come from app code on `bench migrate`.

---

## 3. Explicitly EXCLUDED (transactional — stays in backup, not imported)

These are events / postings, not master:

- Sales Invoice, Sales Invoice Item, Sales Invoice Advance
- Purchase Invoice, Purchase Order, Purchase Receipt
- Payment Entry, Payment Entry Reference
- Journal Entry, Journal Entry Account
- GL Entry, Stock Ledger Entry, Stock Reconciliation, Stock Entry
- Service Request, Lab Test, Lab Test Result, Sample Collection,
  Diagnostic Report, Lab Report, Patient Medical Record
- POS Opening Entry, POS Closing Entry, POS Closing Detail
- Lab Workflow Session, Peer Review Case
- Notification Log, Email Queue, Communication, Activity Log,
  Error Log, View Log, Document Follow, Comment
- Naming Series counters (`tabSeries`) — start fresh

## 4. Explicitly EXCLUDED (system tables — never copy)

- `tabSeries` (autoname counters — restored fresh, fixed by patches)
- `tabSingles` for Singles not in Layer 9 (selectively restore configuration)
- `tabDefaultValue` (user defaults — including `is_pos` that we already cleared)
- `tabActivity Log`, `tabError Log`, `tabAccess Log`, `tabView Log`
- `tabPatch Log` (per-site patch runs — Frappe rebuilds)
- `tabSession Default Settings` (per-user session state)
- `tabDeleted Document`

---

## 5. Order of execution (concrete steps)

```
1.  bench --site master-stage.com new-site ... (apps: same set)
2.  bench --site master-stage.com restore <backup>.sql.gz --with-files <files>.tar
3.  bench --site master-stage.com migrate            # applies fix_v15_residue patch
4.  Run scripts/export_master_data.py on master-stage.com → writes JSON files
    per layer to scratchpad
5.  bench drop-site master-stage.com --no-backup --force
6.  bench --site genetest.com install-app ... (same set, fresh)
7.  Run scripts/import_master_data.py on genetest.com → reads JSON in layer
    order, inserts/upserts each row
8.  bench --site genetest.com migrate                # installs Custom Fields,
    Property Setters, Workspaces, etc.
9.  bench --site genetest.com clear-cache
```

---

## 6. Idempotency + conflict handling

- For each doctype: check `frappe.db.exists(dt, name)` before insert.
  If exists, decide per doctype: skip / update / merge.
- Lookups (Currency, Country, UOM): default = skip (system seeds).
- Catalog (Item, Lab Test Template): default = upsert (backup wins).
- Identity (Patient, Customer, Employee, User): default = skip if exists
  (avoid overwriting newer edits).
- Singles (Healthcare Settings, etc.): default = merge field-by-field.

## 7. Validation gates

Before declaring success:

- Count check: # rows imported vs # rows on stage for each doctype.
- Reference check: every `Customer.customer_group` resolves to a real row;
  every `Item.item_group` resolves; every `Lab Test Template.sample` resolves.
- No GL Entry / Sales Invoice / Lab Test rows on the destination (transactional
  doctypes empty).
- `bench --site genetest.com console` → spot-check 3 patients, 3 lab test
  templates, 3 customers.
