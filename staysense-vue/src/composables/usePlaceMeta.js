// Display metadata for `places.category` values returned by
// GET /api/accommodations/{id}/nearby.
export const PLACE_META = {
  temple: { label: 'วัด', emoji: '🛕' },
  attraction: { label: 'สถานที่ท่องเที่ยว', emoji: '📸' },
  station: { label: 'การเดินทาง', emoji: '🚉' },
  mall: { label: 'ห้างสรรพสินค้า', emoji: '🛍️' },
  hospital: { label: 'โรงพยาบาล', emoji: '🏥' },
  market: { label: 'ตลาด', emoji: '🧺' },
  convenience: { label: 'ร้านสะดวกซื้อ', emoji: '🏪' },
  restaurant: { label: 'ร้านอาหาร', emoji: '🍜' },
  museum: { label: 'พิพิธภัณฑ์', emoji: '🏛️' },
  _: { label: 'อื่น ๆ', emoji: '📍' },
}

export function formatDistance(km) {
  return km < 1 ? `${Math.round(km * 1000)} ม.` : `${km.toFixed(1)} กม.`
}
