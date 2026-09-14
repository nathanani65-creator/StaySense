import { get } from './client'

/**
 * @param {object} [params]
 * @param {string} [params.q]
 * @param {string} [params.type]
 * @param {string[]} [params.district]
 * @param {number} [params.price_min]
 * @param {number} [params.price_max]
 * @param {string[]} [params.amenities]
 */
export function fetchHome(params) {
  return get('/api/home', params)
}
