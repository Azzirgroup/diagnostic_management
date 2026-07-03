import axios, { AxiosError, AxiosInstance } from 'axios'

// Frappe REST conventions:
//   - Session cookie `sid` is set by Frappe on login.
//   - For state-changing calls Frappe expects either an `X-Frappe-CSRF-Token`
//     header OR Authorization: token <api_key>:<api_secret>. We use the
//     session-cookie + CSRF-token model since the SPA runs on the same origin.
//   - The CSRF token is exposed by Frappe at `window.csrf_token` when the page
//     is served by the desk; on standalone SPA loads we fetch it via
//     /api/method/frappe.auth.get_logged_user after login.

declare global {
  interface Window {
    csrf_token?: string
    frappe?: { csrf_token?: string }
  }
}

const client: AxiosInstance = axios.create({
  baseURL: '/',
  withCredentials: true,
  headers: { Accept: 'application/json', 'X-Frappe-Site-Name': window.location.hostname },
})

client.interceptors.request.use((config) => {
  const token = window.csrf_token || window.frappe?.csrf_token
  if (token && config.method && config.method.toUpperCase() !== 'GET') {
    config.headers['X-Frappe-CSRF-Token'] = token
  }
  return config
})

client.interceptors.response.use(
  (r) => r,
  (err: AxiosError) => {
    if (err.response?.status === 403 || err.response?.status === 401) {
      const path = window.location.pathname
      if (!path.endsWith('/login') && !path.endsWith('/doctor-login')) {
        // Soft redirect to login; preserve return URL.
        const next = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.assign(`/diagnostic_management/login?next=${next}`)
      }
    }
    return Promise.reject(err)
  },
)

export default client

// --- Typed helpers around Frappe REST -------------------------------------

export interface FrappeListParams {
  doctype: string
  fields?: string[]
  filters?: Array<[string, string, string | number | (string | number)[]]> | Record<string, unknown>
  limit_page_length?: number
  limit_start?: number
  order_by?: string
}

export async function getList<T = Record<string, unknown>>(p: FrappeListParams): Promise<T[]> {
  const params = new URLSearchParams()
  if (p.fields) params.set('fields', JSON.stringify(p.fields))
  if (p.filters) params.set('filters', JSON.stringify(p.filters))
  if (p.limit_page_length != null) params.set('limit_page_length', String(p.limit_page_length))
  if (p.limit_start != null) params.set('limit_start', String(p.limit_start))
  if (p.order_by) params.set('order_by', p.order_by)
  const { data } = await client.get(`/api/resource/${encodeURIComponent(p.doctype)}?${params.toString()}`)
  return data.data as T[]
}

export async function getDoc<T = Record<string, unknown>>(doctype: string, name: string): Promise<T> {
  const { data } = await client.get(`/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`)
  return data.data as T
}

export async function createDoc<T = Record<string, unknown>>(doctype: string, doc: Record<string, unknown>): Promise<T> {
  const { data } = await client.post(`/api/resource/${encodeURIComponent(doctype)}`, doc)
  return data.data as T
}

export async function updateDoc<T = Record<string, unknown>>(
  doctype: string,
  name: string,
  doc: Record<string, unknown>,
): Promise<T> {
  const { data } = await client.put(
    `/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`,
    doc,
  )
  return data.data as T
}

export async function call<T = unknown>(method: string, args: Record<string, unknown> = {}): Promise<T> {
  // Frappe whitelisted method call. POST so CSRF + complex args work.
  const { data } = await client.post(`/api/method/${method}`, args)
  return data.message as T
}

// Extract a human-readable message from a Frappe/axios error. Frappe puts
// validation text (e.g. mandatory-result errors → HTTP 417) in
// `_server_messages` (a JSON array of JSON strings), not always `message`.
//
// IMPORTANT: when the request rolled back because of an exception, Frappe
// still includes msgprint INFO lines emitted before the throw (e.g.
// "Sample Collection HLC-SC-2026-00003 has been created") in
// `_server_messages` — so plainly returning the first message hides the
// actual failure reason. Prefer the exception ladder, then fall back to
// `_server_messages` only when no exception is reported.
export function frappeError(e: any, fallback = 'Something went wrong'): string {
  const d = e?.response?.data
  const httpFailed = d?.exception || d?.exc_type ||
    (typeof e?.response?.status === 'number' && e.response.status >= 400)

  // Parse _server_messages once; we may use it standalone OR combine with
  // an exception's last line.
  let serverMsg = ''
  try {
    if (d?._server_messages) {
      const msgs = JSON.parse(d._server_messages)
      const parsed = msgs.map((m: string) => { try { return JSON.parse(m).message } catch { return m } })
      serverMsg = parsed.filter(Boolean).join('. ').replace(/<[^>]+>/g, '')
    }
  } catch { /* ignore */ }

  if (httpFailed) {
    // Take the most-specific text we have for the actual failure. Strip
    // Frappe's `frappe.exceptions.<X>Error:` prefix and any HTML entities
    // so the message renders like a human wrote it, not like a traceback.
    const excText = (d?.exception || '').toString().split('\n').pop()?.trim()
    const failure = clean(excText || d?.exc_type || d?.message || '')
    const cleanedServer = clean(serverMsg)
    // Don't concatenate two variants of the same sentence — pick one.
    if (failure && cleanedServer && !sentenceMatch(failure, cleanedServer)) {
      return `${failure} — ${cleanedServer}`
    }
    if (failure) return failure
    if (cleanedServer) return cleanedServer
  }

  return clean(serverMsg) || clean(d?.message) || clean(d?.exception) || e?.message || fallback
}

// Strip Frappe's exception class prefix, decode common HTML entities, collapse whitespace.
function clean(s?: string): string {
  if (!s) return ''
  return s
    .replace(/^[a-zA-Z._]+(Error|Exception):\s*/, '')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/<[^>]+>/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

// True when the two strings say the same thing (after clean()) — used to avoid
// stitching "X — X" when the exception text and server message are duplicates.
function sentenceMatch(a: string, b: string): boolean {
  const norm = (x: string) => x.toLowerCase().replace(/[^a-z0-9 ]/g, '').replace(/\s+/g, ' ').trim()
  const A = norm(a), B = norm(b)
  return A === B || A.includes(B) || B.includes(A)
}

export async function getCount(doctype: string, filters?: FrappeListParams['filters']): Promise<number> {
  const result = await call<number>('frappe.client.get_count', { doctype, filters })
  return result || 0
}
