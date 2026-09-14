const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
export const AUTH_TOKEN_KEY = 'staysense_token'

function authHeader() {
  let token = null
  try {
    token = localStorage.getItem(AUTH_TOKEN_KEY)
  } catch {
    // localStorage unavailable (private mode, etc.) — just skip auth
  }
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function buildQuery(params) {
  const usp = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      value.forEach((v) => {
        if (v !== undefined && v !== null && v !== '') usp.append(key, v)
      })
    } else {
      usp.append(key, value)
    }
  })
  return usp.toString()
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...authHeader(), ...(options.headers || {}) },
    ...options,
  })
  if (!res.ok) {
    let detail = ''
    try {
      const body = await res.json()
      detail = body.detail ? JSON.stringify(body.detail) : ''
    } catch {
      detail = await res.text().catch(() => '')
    }
    const err = new Error(`API ${res.status} ${path}: ${detail || res.statusText}`)
    err.status = res.status
    throw err
  }
  if (res.status === 204) return null
  return res.json()
}

export function get(path, params) {
  const qs = params ? '?' + buildQuery(params) : ''
  return request(path + qs)
}

export function post(path, body) {
  return request(path, { method: 'POST', body: JSON.stringify(body) })
}

export function put(path, body) {
  return request(path, { method: 'PUT', body: JSON.stringify(body) })
}

export function del(path) {
  return request(path, { method: 'DELETE' })
}

/** Multipart upload — deliberately does NOT set Content-Type so the browser
 * fills in the multipart boundary itself. */
export async function postForm(path, formData) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { ...authHeader() },
    body: formData,
  })
  if (!res.ok) {
    let detail = ''
    try {
      const body = await res.json()
      detail = body.detail ? JSON.stringify(body.detail) : ''
    } catch {
      detail = await res.text().catch(() => '')
    }
    const err = new Error(`API ${res.status} ${path}: ${detail || res.statusText}`)
    err.status = res.status
    throw err
  }
  return res.json()
}

export function patch(path, body) {
  return request(path, { method: 'PATCH', body: JSON.stringify(body) })
}
