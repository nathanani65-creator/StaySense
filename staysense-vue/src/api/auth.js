import { get, post } from './client'

/** @returns {Promise<{access_token: string, token_type: string, user: object}>} */
export function apiRegister({ name, email, password }) {
  return post('/api/auth/register', { name, email, password })
}

/** @returns {Promise<{access_token: string, token_type: string, user: object}>} */
export function apiLogin({ email, password }) {
  return post('/api/auth/login', { email, password })
}

export function apiMe() {
  return get('/api/auth/me')
}
