import { get, post, put, del } from './client'

export function fetchAdminAmenities() {
  return get('/api/admin/amenities')
}

export function fetchAmenityCategories() {
  return get('/api/admin/amenity-categories')
}

export function createAmenity(payload) {
  return post('/api/admin/amenities', payload)
}

export function updateAmenity(id, payload) {
  return put(`/api/admin/amenities/${id}`, payload)
}

export function deleteAmenity(id) {
  return del(`/api/admin/amenities/${id}`)
}
