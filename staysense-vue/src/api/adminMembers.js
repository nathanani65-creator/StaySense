import { get, put } from './client'

/**
 * @param {object} [params]
 * @param {string} [params.search]
 * @param {number} [params.page]
 * @param {number} [params.page_size]
 */
export function fetchAdminMembers(params) {
  return get('/api/admin/members', params)
}

export function setMemberActive(id, isActive) {
  return put(`/api/admin/members/${id}`, { is_active: isActive })
}

export function fetchAdminStats() {
  return get('/api/admin/stats')
}
