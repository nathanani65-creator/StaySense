import { get, post, put, del } from './client'

/**
 * @param {object} params
 * @param {string} [params.status] draft|pending_review|published|closed
 * @param {string} [params.district] districts.name, exact match
 * @param {string} [params.type] accommodation_types.code
 * @param {string} [params.search] name contains this text
 * @param {number} [params.page]
 * @param {number} [params.page_size]
 */
export function fetchAdminAccommodations(params) {
  return get('/api/admin/accommodations', params)
}

/**
 * District x type breakdown (every status by default) — the "อำเภอเมือง
 * มีโรงแรม/รีสอร์ต/โฮมสเตย์กี่แห่ง" summary grid.
 * @param {object} [params]
 * @param {string} [params.status]
 * @param {string} [params.search]
 */
export function fetchAdminSummary(params) {
  return get('/api/admin/accommodations/summary', params)
}

/** Same payload shape as AccommodationCreate/Update on the backend. */
export function createAccommodation(payload) {
  return post('/api/accommodations', payload)
}

export function updateAccommodation(id, payload) {
  return put(`/api/accommodations/${id}`, payload)
}

export function deleteAccommodationHard(id) {
  return del(`/api/accommodations/${id}`)
}
