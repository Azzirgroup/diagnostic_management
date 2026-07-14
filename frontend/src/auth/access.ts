// Central role-based access control for the ADMS staff SPA.
//
// Each sidebar item OR route declares the roles that may see it. Users with
// ANY of those roles get access. Administrator / System Manager always pass
// (they're treated as super-users by Frappe). A route guard in router/index
// reuses the same predicate so a user typing the URL directly can't bypass
// the sidebar filter.

export interface SidebarItem {
  to: string
  label: string
  icon: string
  key: string
  /** Roles that may see this page. Empty / undefined → everyone. */
  roles?: string[]
  /** Section header this item lives under in the sidebar (rendered as a
   * small uppercase caption above the group). Items without a section
   * render loose at the top before the first grouped item. */
  section?: string
}

// Super-roles that always have access to every page.
export const ADMIN_ROLES = ['Administrator', 'System Manager']

export function hasAnyRole(userRoles: string[], required: string[]): boolean {
  if (!required || !required.length) return true
  if (userRoles.some((r) => ADMIN_ROLES.includes(r))) return true
  return userRoles.some((r) => required.includes(r))
}

export function canSee(item: { roles?: string[] }, userRoles: string[]): boolean {
  return hasAnyRole(userRoles, item.roles || [])
}

// The single source of truth for the SPA sidebar. The same `roles` list gates
// access in router/index.ts so URL-typing can't get around the sidebar.
export const SIDEBAR_ITEMS: SidebarItem[] = [
  // Loose top items (no section header).
  { to: '/', label: 'Home', icon: 'home', key: 'home' /* everyone */ },
  { to: '/patients', label: 'Patients', icon: 'patients', key: 'patients',
    roles: ['Receptionist','Phlebotomist','Sample Receiver','Lab Technician','Pathologist','Lab Manager','Diagnostic Director','Billing Officer'] },
  { to: '/workflow', label: 'Workflow', icon: 'workflow', key: 'workflow',
    roles: ['Phlebotomist','Sample Receiver','Lab Technician','Lab Quality Officer','Pathologist','Lab Manager','Diagnostic Director','Receptionist'] },

  // Front-desk workflow
  { section: 'Front Desk', to: '/orders', label: 'Test Orders', icon: 'orders', key: 'orders',
    roles: ['Receptionist','Lab Technician','Pathologist','Lab Manager','Diagnostic Director','Billing Officer'] },
  { section: 'Front Desk', to: '/collection', label: 'Collection', icon: 'collection', key: 'collection',
    roles: ['Phlebotomist','Sample Receiver','Lab Technician','Lab Quality Officer','Lab Manager','Diagnostic Director'] },
  { section: 'Front Desk', to: '/checkin', label: 'Check-In', icon: 'checkin', key: 'checkin' },

  // Laboratory
  { section: 'Laboratory', to: '/lab', label: 'Lab', icon: 'lab', key: 'lab',
    roles: ['Lab Technician','Lab Quality Officer','Pathologist','Lab Manager','Diagnostic Director','Urgent Review Officer'] },
  { section: 'Laboratory', to: '/lab/reports', label: 'Lab Reports', icon: 'reports', key: 'lab-reports',
    roles: ['Lab Technician','Pathologist','Lab Manager','Diagnostic Director','Auditor','Referring Doctor'] },
  { section: 'Laboratory', to: '/critical-findings', label: 'Critical Findings', icon: 'critical', key: 'critical',
    roles: ['Pathologist','Lab Manager','Diagnostic Director','Urgent Review Officer','Radiologist','Radiology Manager'] },

  // Radiology (its own section)
  { section: 'Radiology', to: '/radiology', label: 'Radiology', icon: 'radiology', key: 'radiology',
    roles: ['Radiology Technologist','Radiologist','Radiology Manager','Diagnostic Director'] },

  // Billing & Accounts
  { section: 'Billing', to: '/billing', label: 'Billing', icon: 'billing', key: 'billing',
    roles: ['Billing Officer','Insurance Officer','Lab Manager','Diagnostic Director'] },
  { section: 'Billing', to: '/customers', label: 'Customers', icon: 'customers', key: 'customers',
    roles: ['Billing Officer','Accounts Manager','Lab Manager','Diagnostic Director'] },
  { section: 'Billing', to: '/shift', label: 'Shifts', icon: 'shift', key: 'shift',
    roles: ['Billing Officer','Lab Manager','Diagnostic Director','Receptionist'] },

  // Insights
  { section: 'Insights', to: '/reports', label: 'Reports', icon: 'reports', key: 'reports',
    roles: ['Lab Manager','Radiology Manager','Diagnostic Director','Auditor','Billing Officer'] },
  { section: 'Insights', to: '/analytics', label: 'Analytics', icon: 'analytics', key: 'analytics',
    roles: ['Lab Manager','Radiology Manager','Diagnostic Director','Auditor'] },
  { section: 'Insights', to: '/audit', label: 'Audit & Compliance', icon: 'audit', key: 'audit',
    roles: ['Auditor','Diagnostic Director','Lab Manager'] },

  // Administration
  { section: 'Admin', to: '/branches', label: 'Branches', icon: 'branches', key: 'branches',
    roles: ['Diagnostic Director'] /* + Admin/System Manager bypass */ },
  { section: 'Admin', to: '/settings', label: 'Settings', icon: 'settings', key: 'settings' /* everyone — basic profile */ },
]

// Build a path → roles lookup used by the route guard.
export const ROUTE_ROLES: Record<string, string[] | undefined> = SIDEBAR_ITEMS.reduce(
  (acc, item) => { acc[item.to] = item.roles; return acc },
  {} as Record<string, string[] | undefined>,
)

// Path roles for sub-routes that aren't directly in the sidebar — they inherit
// from their section's top-level item.
export const ROUTE_PREFIX_ROLES: Array<{ prefix: string; roles?: string[] }> = [
  { prefix: '/lab/reports',   roles: ROUTE_ROLES['/lab/reports'] },
  { prefix: '/lab',           roles: ROUTE_ROLES['/lab'] },
  { prefix: '/radiology',     roles: ROUTE_ROLES['/radiology'] },
  { prefix: '/critical-findings', roles: ROUTE_ROLES['/critical-findings'] },
  { prefix: '/billing',       roles: ROUTE_ROLES['/billing'] },
  { prefix: '/shift',         roles: ROUTE_ROLES['/shift'] },
  { prefix: '/checkin',       roles: ROUTE_ROLES['/checkin'] },
  { prefix: '/orders',        roles: ROUTE_ROLES['/orders'] },
  { prefix: '/collection',    roles: ROUTE_ROLES['/collection'] },
  { prefix: '/patients',      roles: ROUTE_ROLES['/patients'] },
  { prefix: '/workflow',      roles: ROUTE_ROLES['/workflow'] },
  { prefix: '/reports',       roles: ROUTE_ROLES['/reports'] },
  { prefix: '/analytics',     roles: ROUTE_ROLES['/analytics'] },
  { prefix: '/audit',         roles: ROUTE_ROLES['/audit'] },
  { prefix: '/branches',      roles: ROUTE_ROLES['/branches'] },
]

/** Required roles for a given route path; undefined = no restriction. */
export function rolesForPath(path: string): string[] | undefined {
  if (ROUTE_ROLES[path] !== undefined) return ROUTE_ROLES[path]
  for (const r of ROUTE_PREFIX_ROLES) {
    if (path === r.prefix || path.startsWith(r.prefix + '/')) return r.roles
  }
  return undefined
}

/** Can this user navigate to `path`? */
export function canNavigate(path: string, userRoles: string[]): boolean {
  const required = rolesForPath(path)
  return hasAnyRole(userRoles, required || [])
}
