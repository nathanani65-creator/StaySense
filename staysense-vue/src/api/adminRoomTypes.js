import { get, post, put, del } from './client'

export function fetchAdminRoomTypes(accommodationId) {
  return get(`/api/admin/accommodations/${accommodationId}/room-types`)
}

export function createRoomType(accommodationId, payload) {
  return post(`/api/admin/accommodations/${accommodationId}/room-types`, payload)
}

export function updateRoomType(roomTypeId, payload) {
  return put(`/api/admin/room-types/${roomTypeId}`, payload)
}

export function deleteRoomType(roomTypeId) {
  return del(`/api/admin/room-types/${roomTypeId}`)
}
