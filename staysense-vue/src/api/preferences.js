import { get, put, del } from './client'

export function fetchMyPreferences() {
  return get('/api/me/preferences')
}

export function saveMyPreferences(payload) {
  return put('/api/me/preferences', payload)
}

export function fetchPersonalizationSettings() {
  return get('/api/me/personalization')
}

export function setPersonalizationSettings(allowPersonalization) {
  return put('/api/me/personalization', { allow_personalization: allowPersonalization })
}

export function clearSearchHistory() {
  return del('/api/me/search-history')
}

export function fetchSearchHistorySetting() {
  return get('/api/me/search-history-setting')
}

export function setSearchHistorySetting(saveSearchHistory) {
  return put('/api/me/search-history-setting', { save_search_history: saveSearchHistory })
}
