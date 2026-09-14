import { post } from './client'

/**
 * Logs a real usage event for one accommodation — the only input to the
 * "ที่พักยอดนิยม" popularity ranking. Never awaited by its callers for UI
 * purposes; failures are swallowed so a broken event ping never blocks the
 * action the user actually cared about (viewing, favoriting, ...).
 * @param {number} accommodationId
 * @param {'view'|'favorite'|'compare'|'contact_click'|'direction_click'} eventType
 */
export function logEvent(accommodationId, eventType) {
  return post(`/api/accommodations/${accommodationId}/events`, { event_type: eventType }).catch(() => {})
}
