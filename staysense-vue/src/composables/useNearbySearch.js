import { ref } from 'vue'

// In-memory only (module state, not localStorage/sessionStorage) — the
// pending nearby-search request (including real coordinates) lives only for
// the current tab and this navigation, and is gone on reload or tab close.
// This is how StaySense avoids ever persisting a visitor's exact location.
const pending = ref(null)

export function useNearbySearch() {
  function setPending(payload) {
    pending.value = payload
  }
  function consumePending() {
    const v = pending.value
    pending.value = null
    return v
  }
  return { setPending, consumePending }
}
