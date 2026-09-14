import { get, post, put, del } from './client'

/**
 * @param {object} [params]
 * @param {string} [params.district] districts.name, exact match
 * @param {string} [params.category] places.category
 * @param {string} [params.search] name contains this text
 */
export function fetchAdminPlaces(params) {
  return get('/api/admin/places', params)
}

export function fetchPlaceCategories() {
  return get('/api/admin/place-categories')
}

export function createPlace(payload) {
  return post('/api/admin/places', payload)
}

export function updatePlace(id, payload) {
  return put(`/api/admin/places/${id}`, payload)
}

export function deletePlace(id) {
  return del(`/api/admin/places/${id}`)
}
