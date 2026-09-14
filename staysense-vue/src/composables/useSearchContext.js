import { ref } from 'vue'

// Carries the last completed search's query + structured, per-accommodation
// match reasons from the results page to the detail page (spec §9) — never
// coordinates (see useNearbySearch.js for that same privacy rule). Persisted
// to sessionStorage so it survives a reload within the tab, cleared whenever
// a new search actually runs; only a *completed* search (Enter/button/pick a
// suggestion) writes it — never a keystroke.
const STORAGE_KEY = 'staysense_search_context'

function load() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function persist(value) {
  try {
    if (value) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value))
    else sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // sessionStorage unavailable (private mode, etc.) — in-memory only
  }
}

const context = ref(load())

export function useSearchContext() {
  /** @param {{originalQuery, normalizedQuery, interpretedAs, detectedFilters, confidence, corrections, items}} result */
  function setContext({ originalQuery, normalizedQuery, interpretedAs, detectedFilters, confidence, corrections, items }) {
    const reasonsById = {}
    const poisById = {}
    for (const item of items || []) {
      if (item.matchReasons && item.matchReasons.length) reasonsById[item.id] = item.matchReasons
      if (item.matchedPois && item.matchedPois.length) poisById[item.id] = item.matchedPois
    }
    context.value = {
      originalQuery: originalQuery || '',
      normalizedQuery: normalizedQuery || originalQuery || '',
      interpretedAs: interpretedAs || null,
      detectedFilters: detectedFilters || [],
      confidence: confidence ?? null,
      corrections: corrections || [],
      reasonsById,
      poisById,
    }
    persist(context.value)
  }

  function clearContext() {
    context.value = null
    persist(null)
  }

  function getReasonsFor(accommodationId) {
    return context.value?.reasonsById?.[accommodationId] || []
  }

  function getPoisFor(accommodationId) {
    return context.value?.poisById?.[accommodationId] || []
  }

  return { context, setContext, clearContext, getReasonsFor, getPoisFor }
}
