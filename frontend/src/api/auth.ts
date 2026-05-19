import client, { call } from './client'

export interface FrappeUser {
  name: string
  email: string
  full_name: string
  user_image?: string
  roles: string[]
}

// Frappe's /api/method/login endpoint accepts form-encoded usr/pwd.
export async function login(usr: string, pwd: string): Promise<{ user: string }> {
  const form = new URLSearchParams()
  form.set('usr', usr)
  form.set('pwd', pwd)
  const { data } = await client.post('/api/method/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return { user: data.full_name || usr }
}

export async function logout(): Promise<void> {
  await client.get('/api/method/logout')
}

export async function getLoggedUser(): Promise<FrappeUser | null> {
  try {
    const loggedUser = await call<string>('frappe.auth.get_logged_user')
    if (!loggedUser || loggedUser === 'Guest') return null
    const profile = await call<Record<string, unknown>>(
      'diagnostic_management.api.session.profile',
    )
    return profile as unknown as FrappeUser
  } catch {
    return null
  }
}
