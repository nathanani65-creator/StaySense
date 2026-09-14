// Real browser Geolocation only — no IP-based or fabricated coordinates.

export const NEAR_ME_PATTERN = /ใกล้ฉัน|แถวนี้|ใกล้ตัว|ใกล้ตำแหน่งปัจจุบัน|บริเวณนี้|ใกล้\s*ๆ|near me/i

const TYPE_KEYWORDS = [
  { re: /โรงแรม/, code: 'hotel' },
  { re: /รีสอร์ต|รีสอร์ท/, code: 'resort' },
  { re: /โฮมสเตย์/, code: 'homestay' },
]

export function detectNearMe(text) {
  return NEAR_ME_PATTERN.test(text || '')
}

/** Best-effort client-side type guess, only used to decide whether a type
 * filter tab should be pre-selected before navigating — the backend's
 * /api/search/nearby re-detects this itself from real amenity/type data and
 * is the source of truth for what's actually shown. */
export function detectTypeCode(text) {
  const hit = TYPE_KEYWORDS.find((t) => t.re.test(text || ''))
  return hit ? hit.code : null
}

export const GEO_ERROR_MESSAGES = {
  PERMISSION_DENIED: 'คุณไม่อนุญาตให้เข้าถึงตำแหน่ง กรุณาเลือกอำเภอหรือสถานที่ที่ต้องการค้นหา',
  POSITION_UNAVAILABLE: 'ไม่สามารถระบุตำแหน่งของคุณได้ในขณะนี้ กรุณาลองใหม่อีกครั้ง',
  TIMEOUT: 'ใช้เวลาระบุตำแหน่งนานเกินไป กรุณาลองใหม่หรือเลือกพื้นที่ด้วยตนเอง',
  UNSUPPORTED: 'อุปกรณ์นี้ไม่รองรับการระบุตำแหน่ง กรุณาเลือกอำเภอหรือสถานที่ที่ต้องการค้นหา',
  NETWORK_ERROR: 'ไม่สามารถเชื่อมต่อระบบค้นหาได้ กรุณาลองใหม่อีกครั้ง',
  NO_RESULTS: 'ไม่พบที่พักตามเงื่อนไขในบริเวณนี้ กรุณาขยายระยะทางหรือปรับตัวกรอง',
}

const CODE_NAMES = { 1: 'PERMISSION_DENIED', 2: 'POSITION_UNAVAILABLE', 3: 'TIMEOUT' }

/** Wraps navigator.geolocation.getCurrentPosition in a Promise. Always asks
 * the browser fresh — coordinates are never cached or reused across calls,
 * since the visitor may have moved since the last request. */
export function getCurrentPosition() {
  return new Promise((resolve, reject) => {
    if (!('geolocation' in navigator)) {
      reject({ code: 'UNSUPPORTED' })
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      (err) => reject({ code: CODE_NAMES[err.code] || 'POSITION_UNAVAILABLE' }),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    )
  })
}

export function formatDistance(km) {
  if (km == null) return null
  if (km < 1) return `${Math.round(km * 1000)} เมตร`
  return `${km.toFixed(1)} กม.`
}
