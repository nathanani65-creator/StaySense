import { get } from './client'

/**
 * Typing suggestions for the search box — never logged as search history
 * (see app/routers/search.py's /api/search/suggestions, which deliberately
 * never calls crud.log_search).
 * @param {string} q
 * @returns {Promise<{
 *   originalQuery: string,
 *   normalizedQuery: string,
 *   interpretedAs: string|null,
 *   querySuggestions: string[],
 *   poiSuggestions: {name: string, category: string}[],
 *   accommodationSuggestions: {id: number, name: string, type: string, district: string, matchedPoiName: string|null, distanceKm: number|null}[],
 * }>}
 */
export function fetchSearchSuggestions(q) {
  return get('/api/search/suggestions', { q })
}
