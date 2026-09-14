import { get, post, del } from './client'

/** @returns {Promise<object[]>} accommodations the current user has favorited */
export function fetchFavorites() {
  return get('/api/favorites')
}

export function addFavorite(accommodationId) {
  return post(`/api/favorites/${accommodationId}`)
}

export function removeFavorite(accommodationId) {
  return del(`/api/favorites/${accommodationId}`)
}
