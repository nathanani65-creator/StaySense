import { ref } from 'vue'
import { get } from '../api/client'

// Pixel positions for the hand-drawn SVG map in DistrictMap.vue. This is a
// fixed visual layout tied to the artwork, not data — it doesn't come from
// the backend. Keyed by district name so it merges with whatever the API
// returns for `key`.
export const DISTRICT_MAP_LAYOUT = {
  เมืองพิษณุโลก: { cx: 230, cy: 300 },
  พรหมพิราม: { cx: 300, cy: 210 },
  ชาติตระการ: { cx: 110, cy: 110 },
  บางกระทุ่ม: { cx: 340, cy: 360 },
  วังทอง: { cx: 255, cy: 400 },
  นครไทย: { cx: 150, cy: 230 },
  วัดโบสถ์: { cx: 150, cy: 330 },
  บางระกำ: { cx: 110, cy: 410 },
  เนินมะปราง: { cx: 330, cy: 460 },
}

// Static fallback matching schema.sql's seed data exactly. Districts, types,
// and amenities are fixed reference data that basically never changes, so
// the UI shows this immediately (synchronously, no network wait) and only
// silently upgrades to live data in the background. This means filters,
// type tabs, and the district map always render — even if the backend is
// slow, unreachable, or not running yet — instead of the page looking broken.
const STATIC_DISTRICTS = [
  { id: 1, key: 'เมืองพิษณุโลก', landmark: 'วัดพระศรีรัตนมหาธาตุวรมหาวิหาร (วัดใหญ่)' },
  { id: 2, key: 'พรหมพิราม', landmark: 'วัดพรหมพิราม' },
  { id: 3, key: 'ชาติตระการ', landmark: 'อุทยานแห่งชาติภูสอยดาว' },
  { id: 4, key: 'บางกระทุ่ม', landmark: 'สวนผลไม้ริมน่าน' },
  { id: 5, key: 'วังทอง', landmark: 'อุทยานแห่งชาติทุ่งแสลงหลวง' },
  { id: 6, key: 'นครไทย', landmark: 'อุทยานแห่งชาติภูหินร่องกล้า' },
  { id: 7, key: 'วัดโบสถ์', landmark: 'น้ำตกวังก้านเหลือง' },
  { id: 8, key: 'บางระกำ', landmark: 'ทุ่งบางระกำ' },
  { id: 9, key: 'เนินมะปราง', landmark: 'ถ้ำเจดีย์งาม' },
].map((d) => ({ ...d, ...(DISTRICT_MAP_LAYOUT[d.key] || { cx: 0, cy: 0 }) }))

const STATIC_TYPES = [
  { code: 'hotel', key: 'โรงแรม' },
  { code: 'resort', key: 'รีสอร์ต' },
  { code: 'homestay', key: 'โฮมสเตย์' },
]

// Groups amenity codes for the detail page's categorized display.
// Matches schema_addendum_2.sql's expanded amenity set.
export const AMENITY_CATEGORIES = [
  { key: 'room', label: 'ภายในห้อง', codes: ['aircon', 'tv', 'fridge', 'water_heater'] },
  { key: 'property', label: 'ภายในที่พัก', codes: ['wifi', 'pool', 'restaurant', 'gym', 'elevator'] },
  { key: 'service', label: 'บริการ', codes: ['breakfast', 'laundry', 'reception24'] },
  { key: 'parking', label: 'ที่จอดรถและการเดินทาง', codes: ['parking'] },
  { key: 'accessibility', label: 'การรองรับพิเศษ', codes: ['family', 'pet', 'wheelchair', 'elderly'] },
]

// How the detail page frames the "room types" section for each accommodation
// category. Hotels are described room-by-room; homestays and resort villas are
// described house-by-house ("แต่ละหลัง"). `fields` lists which RoomType
// attributes to surface, in order.
export const ROOM_TYPE_PRESENTATION = {
  hotel: {
    sectionTitle: 'ประเภทห้องพัก',
    sectionHint: 'ราคาต่อคืนต่อห้อง เลือกตามจำนวนผู้เข้าพัก',
    unitWord: 'ห้อง',
    priceSuffix: '/ คืน',
    fields: ['occupancy', 'bedType', 'roomSize', 'extraBed', 'breakfast', 'unitsAvailable'],
  },
  homestay: {
    sectionTitle: 'บ้านพัก (แต่ละหลัง)',
    sectionHint: 'ราคาต่อคืนต่อหลัง พักได้ทั้งหลังตามจำนวนที่ระบุ',
    unitWord: 'หลัง',
    priceSuffix: '/ คืน / หลัง',
    fields: ['houseCapacity', 'bedrooms', 'bathrooms', 'bedType', 'roomSize', 'extraBed', 'breakfast', 'unitsAvailable'],
  },
  resort: {
    sectionTitle: 'ประเภทที่พัก',
    sectionHint: 'มีทั้งแบบห้องพักและแบบหลังส่วนตัว ราคาต่อคืน',
    unitWord: 'ยูนิต',
    priceSuffix: '/ คืน',
    fields: ['houseCapacity', 'bedrooms', 'bathrooms', 'bedType', 'roomSize', 'extraBed', 'breakfast', 'unitsAvailable'],
  },
}

export function roomTypePresentation(typeCode) {
  return ROOM_TYPE_PRESENTATION[typeCode] || ROOM_TYPE_PRESENTATION.hotel
}

const STATIC_AMENITIES = [
  { key: 'wifi', label: 'Wi-Fi ฟรี' },
  { key: 'parking', label: 'ที่จอดรถ' },
  { key: 'breakfast', label: 'อาหารเช้า' },
  { key: 'pool', label: 'สระว่ายน้ำ' },
  { key: 'family', label: 'ห้องสำหรับครอบครัว/เด็ก' },
  { key: 'pet', label: 'สัตว์เลี้ยงเข้าพักได้ (มีเงื่อนไข)' },
  { key: 'aircon', label: 'เครื่องปรับอากาศ' },
  { key: 'tv', label: 'โทรทัศน์' },
  { key: 'fridge', label: 'ตู้เย็น' },
  { key: 'water_heater', label: 'เครื่องทำน้ำอุ่น' },
  { key: 'restaurant', label: 'ร้านอาหาร' },
  { key: 'gym', label: 'ฟิตเนส' },
  { key: 'elevator', label: 'ลิฟต์' },
  { key: 'laundry', label: 'บริการซักรีด' },
  { key: 'reception24', label: 'แผนกต้อนรับ 24 ชม.' },
  { key: 'wheelchair', label: 'รองรับผู้ใช้รถเข็น' },
  { key: 'elderly', label: 'เหมาะสำหรับผู้สูงอายุ' },
]

const districts = ref(STATIC_DISTRICTS)
const accommodationTypes = ref(STATIC_TYPES)
const amenities = ref(STATIC_AMENITIES)
const loaded = ref(false)
const loadError = ref(null)
let loadingPromise = null

async function load() {
  try {
    const [d, t, a] = await Promise.all([
      get('/api/districts'),
      get('/api/accommodation-types'),
      get('/api/amenities'),
    ])
    districts.value = d.map((item) => ({
      ...item,
      ...(DISTRICT_MAP_LAYOUT[item.key] || { cx: 0, cy: 0 }),
    }))
    accommodationTypes.value = t
    amenities.value = a
    loaded.value = true
    loadError.value = null
  } catch (e) {
    // Backend unreachable or slow: keep showing the static fallback already
    // in the refs above. Don't throw — callers should never have to wrap
    // ensureLoaded() in try/catch just to render a filter sidebar.
    loadError.value = e?.message || String(e)
  }
}

export function useReferenceData() {
  function ensureLoaded() {
    if (loaded.value) return Promise.resolve()
    if (!loadingPromise) loadingPromise = load()
    return loadingPromise
  }

  function amenityLabel(code) {
    return amenities.value.find((a) => a.key === code)?.label || code
  }

  return { districts, accommodationTypes, amenities, loaded, loadError, ensureLoaded, amenityLabel }
}
