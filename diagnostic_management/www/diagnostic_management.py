import json
import os

import frappe


# Frappe maps www/<page>.html to /<page>; combined with website_route_rules in
# hooks.py we serve the SPA shell at:
#   /diagnostic_management      (staff app)
#   /diagnostic_management/...  (deep links inside the staff app)
#   /doctor                     (doctor portal)
#   /doctor/...
#   /doctor-login
#   /doctor-register
#
# All four roots reuse this same controller via thin shims in their .py files.

no_cache = 1


def get_context(context):
	context.no_cache = 1

	# Resolve the hashed Vite-built asset filenames from the manifest. If the
	# bundle hasn't been built yet, fall back to predictable names so the page
	# still loads (useful in dev, or when `bench build` hasn't run).
	app_path = frappe.get_app_path("diagnostic_management")
	manifest_path = os.path.join(app_path, "public", "frontend", ".vite", "manifest.json")

	entry, stylesheet = _resolve_assets(manifest_path)
	context.entry = _asset_url(entry)
	context.stylesheet = _asset_url(stylesheet) if stylesheet else ""

	return context


def _asset_url(rel: str) -> str:
	if not rel:
		return ""
	# Cache-bust via the file's modified time so users get fresh JS after deploys.
	return f"/assets/diagnostic_management/frontend/{rel}"


def _resolve_assets(manifest_path: str) -> tuple[str, str]:
	"""Read the Vite manifest to find the hashed entry/css filenames.

	Vite writes the manifest at <outDir>/.vite/manifest.json. The 'index.html'
	key points at the entry chunk; its 'css' array points at the bundled CSS.
	"""
	try:
		with open(manifest_path) as f:
			manifest = json.load(f)
		entry = manifest.get("index.html") or manifest.get("src/main.ts") or {}
		js = entry.get("file", "")
		css_list = entry.get("css") or []
		css = css_list[0] if css_list else ""
		if js:
			return js, css
	except (OSError, json.JSONDecodeError):
		pass
	# Manifest missing — return empty so the controller renders a no-asset
	# page instead of 500ing. The user will see the bare HTML and a hint in
	# the console; this is the case we hit when `npm run build` hasn't run yet.
	return "", ""
