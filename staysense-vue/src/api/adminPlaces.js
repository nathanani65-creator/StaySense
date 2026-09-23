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

// every place within radius (curated + live-estimated), for the admin
// browse-and-curate view — mirrors the public nearby-places modal
export function fetchAdminNearbyPlaces(accommodationId, radiusKm) {
  return get(`/api/admin/accommodations/${accommodationId}/nearby-all`, radiusKm ? { radius_km: radiusKm } : undefined)
}

// curated distance links between one accommodation and nearby places
export function fetchAccommodationPlaces(accommodationId) {
  return get(`/api/admin/accommodations/${accommodationId}/places`)
}

export function createAccommodationPlace(accommodationId, payload) {
  return post(`/api/admin/accommodations/${accommodationId}/places`, payload)
}

export function updateAccommodationPlace(linkId, payload) {
  return put(`/api/admin/accommodation-places/${linkId}`, payload)
}

export function deleteAccommodationPlace(linkId) {
  return del(`/api/admin/accommodation-places/${linkId}`)
}
