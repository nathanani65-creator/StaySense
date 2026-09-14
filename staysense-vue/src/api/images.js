import { get, patch, del, postForm } from './client'

export function fetchImageCategories() {
  return get('/api/image-categories')
}

/* -------------------------------------------------- accommodation gallery */

export function fetchAccommodationImages(accommodationId) {
  return get(`/api/accommodations/${accommodationId}/images`)
}

export function fetchAdminAccommodationImages(accommodationId) {
  return get(`/api/admin/accommodations/${accommodationId}/images`)
}

export function uploadAccommodationImages(accommodationId, files, category) {
  const fd = new FormData()
  for (const f of files) fd.append('files', f)
  if (category) fd.append('category', category)
  return postForm(`/api/admin/accommodations/${accommodationId}/images`, fd)
}

export function updateAccommodationImage(imageId, patchBody) {
  return patch(`/api/admin/accommodation-images/${imageId}`, patchBody)
}

export function setAccommodationImageCover(imageId) {
  return patch(`/api/admin/accommodation-images/${imageId}/cover`, {})
}

export function deleteAccommodationImage(imageId) {
  return del(`/api/admin/accommodation-images/${imageId}`)
}

export function reorderAccommodationImages(accommodationId, orderedIds) {
  return patch('/api/admin/accommodation-images/reorder', { accommodationId, orderedIds })
}

/* ----------------------------------------------------- room-type gallery */

export function fetchRoomTypeImages(roomTypeId) {
  return get(`/api/room-types/${roomTypeId}/images`)
}

export function fetchAdminRoomTypeImages(roomTypeId) {
  return get(`/api/admin/room-types/${roomTypeId}/images`)
}

export function uploadRoomTypeImages(roomTypeId, files, category) {
  const fd = new FormData()
  for (const f of files) fd.append('files', f)
  if (category) fd.append('category', category)
  return postForm(`/api/admin/room-types/${roomTypeId}/images`, fd)
}

export function updateRoomTypeImage(imageId, patchBody) {
  return patch(`/api/admin/room-type-images/${imageId}`, patchBody)
}

export function setRoomTypeImageCover(imageId) {
  return patch(`/api/admin/room-type-images/${imageId}/cover`, {})
}

export function deleteRoomTypeImage(imageId) {
  return del(`/api/admin/room-type-images/${imageId}`)
}

export function reorderRoomTypeImages(roomTypeId, orderedIds) {
  return patch('/api/admin/room-type-images/reorder', { roomTypeId, orderedIds })
}
