// Module-level singleton (same pattern as useAuth.js) — the comparison list
// is purely client-side (up to 3 accommodations, keyed by id + a few display
// fields so the compare page doesn't need a second fetch), persisted to
// localStorage so it survives a reload. Adding an item logs a real
// 'compare' event server-side (the only input popularity scoring has for
// this signal) but the list membership itself is never sent to the backend.
import { ref, computed } from 'vue'
import { logEvent } from '../api/events'

const STORAGE_KEY = 'staysense_compare'
const MAX_COMPARE = 3

function readStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items.value))
  } catch {
    // localStorage unavailable — list still works in-memory for this session
  }
}

const items = ref(readStored())

function isInCompare(id) {
  return items.value.some((i) => i.id === id)
}

// `item` is an AccommodationOut-shaped object — only a few display fields
// are kept so the compare page can render without a second round trip.
function addToCompare(item) {
  if (isInCompare(item.id)) return { ok: true }
  if (items.value.length >= MAX_COMPARE) {
    return { ok: false, reason: 'limit' }
  }
  items.value = [
    ...items.value,
    { id: item.id, name: item.name, district: item.district, type: item.type, price: item.price, img: item.img, rating: item.rating, reviews: item.reviews, amenities: item.amenities },
  ]
  persist()
  logEvent(item.id, 'compare')
  return { ok: true }
}

function removeFromCompare(id) {
  items.value = items.value.filter((i) => i.id !== id)
  persist()
}

function toggleCompare(item) {
  return isInCompare(item.id) ? (removeFromCompare(item.id), { ok: true }) : addToCompare(item)
}

function clearCompare() {
  items.value = []
  persist()
}

const count = computed(() => items.value.length)
const isFull = computed(() => items.value.length >= MAX_COMPARE)

export function useCompare() {
  return { items, count, isFull, maxCompare: MAX_COMPARE, isInCompare, addToCompare, removeFromCompare, toggleCompare, clearCompare }
}
