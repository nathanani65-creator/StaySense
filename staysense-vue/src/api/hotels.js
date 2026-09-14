import { get, post } from './client'

/**
 * @param {object} filters
 * @param {string} [filters.type] accommodation_types.code, e.g. 'hotel'
 * @param {string[]} [filters.district] district names
 * @param {number} [filters.price_min]
 * @param {number} [filters.price_max]
 * @param {number} [filters.rating_min]
 * @param {string[]} [filters.amenities] amenity codes
 * @param {number} [filters.distance_max_km]
 * @param {string} [filters.sort] 'recommended' | 'price-asc' | 'price-desc' | 'rating-desc' | 'distance-asc'
 * @param {number} [filters.page]
 * @param {number} [filters.page_size]
 * @returns {Promise<{items: object[], total: number, page: number, pageSize: number}>}
 */
export function fetchAccommodations(filters) {
  return get('/api/accommodations', filters)
}

export function fetchAccommodation(id) {
  return get(`/api/accommodations/${id}`)
}

export function fetchDistrictCounts(filters) {
  return get('/api/districts/counts', filters)
}

/**
 * @param {number|string} id accommodation id
 * @param {object} [params]
 * @param {string} [params.sort] 'newest' | 'highest' | 'lowest'
 * @param {number} [params.page]
 * @param {number} [params.page_size]
 * @returns {Promise<{items: object[], total: number, page: number, pageSize: number}>}
 */
export function fetchReviews(id, params) {
  return get(`/api/accommodations/${id}/reviews`, params)
}

/**
 * Nearby points of interest, distances computed live from the accommodation's
 * coordinates on the backend.
 * @returns {Promise<{popular: object[], nearest: object[], all: object[]}>}
 */
export function fetchNearby(id) {
  return get(`/api/accommodations/${id}/nearby`)
}

/**
 * Requires an auth token — no login flow in the frontend yet, so this is
 * wired for later use, not called from the UI.
 */
export function postReview(id, body) {
  return post(`/api/accommodations/${id}/reviews`, body)
}

/**
 * @param {object} payload same filter shape as fetchAccommodations, plus `query`
 * @returns {Promise<{items: object[], total: number, page: number, pageSize: number, meta: object}>}
 */
export function searchAccommodations(payload) {
  return post('/api/search', payload)
}

/**
 * @param {object} payload
 * @param {number} payload.latitude
 * @param {number} payload.longitude
 * @param {string} [payload.query]
 * @param {string} [payload.accommodation_type]
 * @param {number} [payload.radius_km]
 * @param {number} [payload.price_min]
 * @param {number} [payload.price_max]
 * @param {string[]} [payload.facilities]
 * @param {string[]} [payload.district]
 * @param {string} [payload.sort_by] 'relevance' | 'distance' | 'price-asc'
 * @returns {Promise<object>} NearbySearchResponse — see app/schemas.py
 */
export function searchNearby(payload) {
  return post('/api/search/nearby', payload)
}
