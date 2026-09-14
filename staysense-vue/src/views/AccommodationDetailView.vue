<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchAccommodation, fetchAccommodations, fetchNearby } from '../api/hotels'
import { fetchAccommodationImages, fetchImageCategories } from '../api/images'
import { logEvent } from '../api/events'
import { useAuth } from '../composables/useAuth'
import { useCompare } from '../composables/useCompare'
import { useFavorites } from '../composables/useFavorites'
import { useSearchContext } from '../composables/useSearchContext'
import { PLACE_META, formatDistance } from '../composables/usePlaceMeta'
import StayCard from '../components/StayCard.vue'
import RoomTypeList from '../components/RoomTypeList.vue'
import AmenitiesGrid from '../components/AmenitiesGrid.vue'
import CategoryRatings from '../components/CategoryRatings.vue'
import ReviewsSection from '../components/ReviewsSection.vue'
import NearbyPlacesModal from '../components/NearbyPlacesModal.vue'
import ImageGalleryModal from '../components/ImageGalleryModal.vue'

const route = useRoute()
const router = useRouter()
const { isLoggedIn } = useAuth()
const { toggleFavorite } = useFavorites()
const { isInCompare, toggleCompare, isFull } = useCompare()

const loading = ref(true)
const errorMessage = ref(null)
const hotel = ref(null)
const related = ref([])
const nearby = ref({ popular: [], nearest: [], all: [] })
const gallery = ref({ open: false, images: [], loading: false, startIndex: 0 })
const galleryCategoryLabels = ref({})
const nearbyModal = ref(false)

onMounted(async () => {
  try {
    const cats = await fetchImageCategories()
    galleryCategoryLabels.value = Object.fromEntries(cats.accommodation.map((c) => [c.key, c.label]))
  } catch {
    galleryCategoryLabels.value = {}
  }
})

async function load() {
  loading.value = true
  errorMessage.value = null
  hotel.value = null
  related.value = []
  nearby.value = { popular: [], nearest: [], all: [] }
  try {
    hotel.value = await fetchAccommodation(route.params.id)
    logEvent(hotel.value.id, 'view')
    loadRelated()
    loadNearby()
    nextTick(() => {
      setupSpy()
      observeOverview()
    })
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

async function loadRelated() {
  try {
    const res = await fetchAccommodations({ district: [hotel.value.district], page_size: 5 })
    related.value = res.items.filter((h) => h.id !== hotel.value.id).slice(0, 4)
  } catch {
    related.value = []
  }
}

async function loadNearby() {
  try {
    nearby.value = await fetchNearby(route.params.id)
  } catch {
    nearby.value = { popular: [], nearest: [], all: [] }
  }
}

onMounted(load)
watch(() => route.params.id, load)

/* ------------------------ keep the right card exactly as tall as the left
   overview column (bottom edges level) — desktop only, via ResizeObserver. */

const leftOverview = ref(null)
const rightOverview = ref(null)
let heightObserver = null

function isDesktop() {
  return window.matchMedia('(min-width: 1024px)').matches
}

function syncRightHeight(h) {
  if (!rightOverview.value) return
  if (isDesktop() && h) rightOverview.value.style.height = `${Math.round(h)}px`
  else rightOverview.value.style.height = '' // mobile: height: auto
}

function observeOverview() {
  heightObserver?.disconnect()
  if (!leftOverview.value) return
  heightObserver = new ResizeObserver(([entry]) => syncRightHeight(entry.contentRect.height))
  heightObserver.observe(leftOverview.value)
  // don't wait for the first async RO tick
  syncRightHeight(leftOverview.value.getBoundingClientRect().height)
}

function onResize() {
  syncRightHeight(leftOverview.value?.getBoundingClientRect().height)
}

watch(() => !!hotel.value, (ready) => ready && nextTick(observeOverview))
onMounted(() => window.addEventListener('resize', onResize))
onBeforeUnmount(() => {
  heightObserver?.disconnect()
  window.removeEventListener('resize', onResize)
})

/* ---------------------------------------------------------------- gallery */

// cheap preview, already published + cover-first from the detail response —
// good enough for the hero grid without an extra request
const FALLBACK_IMAGE =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500"><rect width="800" height="500" fill="%23EEECFF"/><text x="400" y="260" font-family="sans-serif" font-size="22" fill="%237C6FE0" text-anchor="middle">ยังไม่มีรูปภาพ</text></svg>'
  )
const images = computed(() => {
  if (hotel.value?.images?.length) return hotel.value.images.map((img) => img.url)
  return [hotel.value?.img || FALLBACK_IMAGE]
})
const heroThumbs = computed(() => images.value.slice(1, 5))

async function openGallery(i) {
  if (!hotel.value) return
  gallery.value = { open: true, images: [], loading: true, startIndex: i }
  try {
    // re-fetch via accommodation_id specifically for the modal's richer
    // per-image metadata (category/alt/source) — never room_type_images
    const rich = await fetchAccommodationImages(hotel.value.id)
    gallery.value.images = rich.map((img) => ({
      url: img.url, thumbnailUrl: img.thumbnailUrl, category: img.category,
      caption: img.caption, altText: img.altText, sourceName: img.sourceName, sourceUrl: img.sourceUrl,
    }))
  } catch {
    gallery.value.images = images.value.map((url) => ({ url }))
  } finally {
    gallery.value.loading = false
  }
}
function closeGallery() {
  gallery.value.open = false
}

/* ------------------------------------------------------------- sub-nav spy */

const SECTIONS = [
  { id: 'overview', label: 'ภาพรวม' },
  { id: 'rooms', label: 'ห้องพัก' },
  { id: 'amenities', label: 'สิ่งอำนวยความสะดวก' },
  { id: 'reviews', label: 'รีวิว' },
  { id: 'location', label: 'ตำแหน่งที่ตั้ง' },
]
const activeSection = ref('overview')
let observer = null

function setupSpy() {
  observer?.disconnect()
  observer = new IntersectionObserver(
    (entries) => {
      const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)
      if (visible[0]) activeSection.value = visible[0].target.id
    },
    { rootMargin: '-140px 0px -55% 0px', threshold: [0.1, 0.5] },
  )
  SECTIONS.forEach((s) => {
    const el = document.getElementById(s.id)
    if (el) observer.observe(el)
  })
}
onBeforeUnmount(() => observer?.disconnect())

function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/* --------------------------------------------------------------- location */

const mapsUrl = computed(() => {
  const h = hotel.value
  if (!h) return null
  if (h.googleMapsUrl) return h.googleMapsUrl
  if (h.latitude && h.longitude) return `https://www.google.com/maps?q=${h.latitude},${h.longitude}`
  return null
})
const mapEmbedUrl = computed(() => {
  const h = hotel.value
  if (!h?.latitude || !h?.longitude) return null
  return `https://www.google.com/maps?q=${h.latitude},${h.longitude}&z=15&output=embed`
})
const hasParking = computed(() => hotel.value?.amenities?.includes('parking'))

/* ---------------------------------------------------------------- contact */

function ensureHttp(v) {
  return /^https?:\/\//i.test(v) ? v : `https://${v}`
}

const contactRows = computed(() => {
  const c = hotel.value?.contact
  if (!c) return []
  const rows = []
  if (c.phone) rows.push({ icon: 'phone', label: 'โทรศัพท์', text: c.phone, href: `tel:${c.phone.replace(/[^\d+]/g, '')}` })
  if (c.line) {
    const isUrl = /^https?:\/\//i.test(c.line)
    rows.push({ icon: 'line', label: 'LINE', text: c.line, href: isUrl ? c.line : `https://line.me/R/ti/p/${encodeURIComponent(c.line.replace(/^@/, '~'))}` })
  }
  if (c.facebook) {
    const isUrl = /^https?:\/\//i.test(c.facebook)
    rows.push({ icon: 'facebook', label: 'Facebook', text: c.facebook, href: isUrl ? c.facebook : `https://facebook.com/${c.facebook}` })
  }
  if (c.instagram) {
    const isUrl = /^https?:\/\//i.test(c.instagram)
    rows.push({ icon: 'instagram', label: 'Instagram', text: c.instagram, href: isUrl ? c.instagram : `https://instagram.com/${c.instagram.replace(/^@/, '')}` })
  }
  if (c.website) rows.push({ icon: 'globe', label: 'เว็บไซต์', text: c.website, href: ensureHttp(c.website) })
  return rows
})

const primaryContact = computed(() => {
  const rows = contactRows.value
  return rows.find((r) => r.icon === 'phone') || rows.find((r) => r.icon === 'line') || rows[0] || null
})

const CONTACT_ICONS = {
  phone: 'M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .3 2 .7 2.9a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.2-1.2a2 2 0 0 1 2.1-.5c.9.4 1.9.6 2.9.7a2 2 0 0 1 1.8 2z',
  line: 'M21 11c0 4.4-4 8-9 8-1 0-2-.1-2.9-.4L4 20l1.4-3.6C4.2 15.1 3 13.2 3 11c0-4.4 4-8 9-8s9 3.6 9 8z',
  facebook: 'M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z',
  instagram: 'M2 7.6A5.6 5.6 0 0 1 7.6 2h8.8A5.6 5.6 0 0 1 22 7.6v8.8a5.6 5.6 0 0 1-5.6 5.6H7.6A5.6 5.6 0 0 1 2 16.4zM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zm5-1v.01',
  globe: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM2 12h20M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20z',
}

/* ------------------------------------------------------------ price / CTA */

const startingPrice = computed(() => {
  const rts = hotel.value?.roomTypes || []
  const prices = rts.map((r) => r.price).filter((n) => typeof n === 'number')
  return prices.length ? Math.min(...prices) : hotel.value?.price ?? 0
})

/* ------------------------------------------------------ recommendation box */

// Real, structured reasons carried over from the results page (spec §9) —
// keyed by accommodation id, so a card only ever shows reasons that were
// actually computed for THIS accommodation against the visitor's own query.
// Never re-derived here from the accommodation's own static data — that
// would risk drifting from what actually matched, or fabricating a match
// the visitor never searched for.
const { getReasonsFor, getPoisFor, context: searchContextState } = useSearchContext()
const contextReasons = computed(() => (hotel.value ? getReasonsFor(hotel.value.id) : []))
const hasSearchContext = computed(() => contextReasons.value.length > 0)
const matchedQuery = computed(() => {
  if (hasSearchContext.value && searchContextState.value?.originalQuery) return searchContextState.value.originalQuery
  return route.query.q ? String(route.query.q) : null
})

// every real place behind a poi_match reason for this accommodation+query —
// not just the 3 shown on the results card (spec §3/§13).
const contextPois = computed(() => (hotel.value ? getPoisFor(hotel.value.id) : []))
const POI_PREVIEW_COUNT = 5
const poisExpanded = ref(false)
const visiblePois = computed(() => (poisExpanded.value ? contextPois.value : contextPois.value.slice(0, POI_PREVIEW_COUNT)))
function formatPoiDistance(p) {
  const suffix = p.isRoad ? 'ระยะทางตามเส้นทาง' : 'ระยะเส้นตรงโดยประมาณ'
  return `${formatDistance(p.distanceKm)} (${suffix})`
}

const highlights = computed(() => {
  const h = hotel.value
  if (!h) return []
  const out = []
  if (h.landmark) out.push({ icon: 'pin', text: `ใกล้${h.landmark.split(/[( ]/)[0]}` })
  const amenityMap = [
    ['pool', 'pool', 'มีสระว่ายน้ำ'],
    ['wifi', 'wifi', 'Wi-Fi ฟรี'],
    ['breakfast', 'food', 'มีอาหารเช้า'],
    ['parking', 'parking', 'มีที่จอดรถ'],
    ['family', 'family', 'เหมาะสำหรับครอบครัว'],
    ['pet', 'pet', 'อนุญาตให้นำสัตว์เลี้ยงเข้าพัก'],
  ]
  for (const [code, icon, text] of amenityMap) {
    if (h.amenities?.includes(code)) out.push({ icon, text })
  }
  for (const t of h.tags || []) out.push({ icon: 'sparkle', text: t })
  const seen = new Set()
  return out.filter((x) => !seen.has(x.text) && seen.add(x.text)).slice(0, 6)
})

const HL_ICONS = {
  pin: 'M12 21s-7-7.5-7-12a7 7 0 0 1 14 0c0 4.5-7 12-7 12zM12 11a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
  pool: 'M2 16c1.5 0 1.5 1 3 1s1.5-1 3-1 1.5 1 3 1 1.5-1 3-1 1.5 1 3 1 1.5-1 3-1M2 20c1.5 0 1.5 1 3 1s1.5-1 3-1 1.5 1 3 1 1.5-1 3-1 1.5 1 3 1 1.5-1 3-1M7 13V5a2 2 0 0 1 4 0M15 13V5a2 2 0 0 1 4 0',
  wifi: 'M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0M12 19.5h.01',
  food: 'M18 8h1a4 4 0 0 1 0 8h-1M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4zM6 1v3M10 1v3M14 1v3',
  parking: 'M9 21V3h5a5 5 0 0 1 0 10H9M4 3h5m-5 18h5',
  family: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
  pet: 'M12 13c-2 0-3.5 1.6-3.5 3.5A1.5 1.5 0 0 0 10 18h4a1.5 1.5 0 0 0 1.5-1.5C15.5 14.6 14 13 12 13zM6.5 10a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM17.5 10a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM9 6.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM15 6.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z',
  sparkle: 'M12 3l1.8 4.7L18.5 9.5 13.8 11.3 12 16l-1.8-4.7L5.5 9.5l4.7-1.8z',
}

/* --------------------------------------------- extra "about" (left column) */

// Short lead shown up top; the full text only earns its own left-column
// section when it is meaningfully longer than the lead.
const descLead = computed(() => {
  const d = hotel.value?.description || ''
  return d.length > 170 ? d.slice(0, 170).replace(/\s+\S*$/, '') + '…' : d
})
const hasMoreAbout = computed(() => (hotel.value?.description || '').length > 170)

/* --------------------------------------------------------------- policies */

const policyRows = computed(() => {
  const p = hotel.value?.policies
  if (!p) return []
  const rows = []
  if (p.checkinTime || p.checkoutTime) rows.push({ icon: 'clock', label: 'เวลาเช็คอิน / เช็คเอาต์', value: `${p.checkinTime || '—'} / ${p.checkoutTime || '—'}` })
  if (p.cancellationPolicy) rows.push({ icon: 'shield', label: 'การยกเลิก / คืนเงิน', value: p.cancellationPolicy })
  if (p.minAge != null) rows.push({ icon: 'user', label: 'อายุขั้นต่ำผู้เช็คอิน', value: `${p.minAge} ปี` })
  if (p.smokingAllowed != null) rows.push({ icon: 'no-smoking', label: 'การสูบบุหรี่', value: p.smokingAllowed ? 'สูบบุหรี่ได้ในพื้นที่ที่กำหนด' : 'ห้ามสูบบุหรี่ในห้องพัก' })
  if (p.depositRequired || p.depositAmount != null || p.depositPercent != null) {
    let v
    if (p.depositAmount != null) v = `ต้องวางมัดจำ ฿${p.depositAmount.toLocaleString()} ต่อการจอง`
    else if (p.depositPercent != null) v = `ต้องวางมัดจำ ${p.depositPercent}% ของยอดจอง`
    else v = 'ต้องวางเงินมัดจำเพื่อยืนยันการจอง'
    if (p.depositNote) v += `\n${p.depositNote}`
    rows.push({ icon: 'wallet', label: 'เงินมัดจำ', value: v })
  }
  if (p.advanceBookingRequired || p.advanceBookingDays != null) {
    rows.push({ icon: 'calendar', label: 'การจองล่วงหน้า', value: p.advanceBookingDays != null ? `ต้องจองล่วงหน้าอย่างน้อย ${p.advanceBookingDays} วัน` : 'ต้องจองล่วงหน้า ไม่รับ walk-in' })
  }
  if (p.priceConditions) rows.push({ icon: 'tag', label: 'เงื่อนไขราคาเพิ่มเติม', value: p.priceConditions })
  if (p.paymentMethods?.length) rows.push({ icon: 'card', label: 'วิธีชำระเงิน', value: p.paymentMethods.join(', ') })
  return rows
})

const POLICY_ICONS = {
  clock: 'M12 6v6l4 2M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z',
  shield: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
  user: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
  'no-smoking': 'M2 12h14v4H2zM18 12h4v4h-4zM18 8V6a2 2 0 0 0-2-2M4 4l16 16',
  wallet: 'M21 12V7H5a2 2 0 0 1 0-4h14v4M3 5v14a2 2 0 0 0 2 2h16v-5M18 12a2 2 0 0 0 0 4h4v-4z',
  card: 'M2 5h20v14H2zM2 10h20',
  calendar: 'M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  tag: 'M20.6 13.4 12 22l-9-9V3h10l7.6 7.6a2 2 0 0 1 0 2.8zM7.5 7.5h.01',
}

const hasCategoryRatings = computed(() => {
  const cr = hotel.value?.categoryRatings
  return !!cr && Object.values(cr).some((v) => Number(v) > 0)
})

const ratingLabel = computed(() => {
  const r = hotel.value?.rating || 0
  if (r >= 4.5) return 'ยอดเยี่ยม'
  if (r >= 4.0) return 'ดีมาก'
  if (r >= 3.5) return 'ดี'
  if (r >= 3.0) return 'พอใช้'
  return 'ทั่วไป'
})

function placeMeta(cat) {
  return PLACE_META[cat] || PLACE_META._
}

async function toggleFav() {
  if (!hotel.value) return
  if (!isLoggedIn.value) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  try {
    await toggleFavorite(hotel.value)
  } catch {
    // toggleFavorite already reverted hotel.value.fav; nothing else to do
  }
}

// compare is client-side only (useCompare.js), no login required — same
// behaviour as the "เพิ่มเพื่อเปรียบเทียบ" button on the search-result cards.
function onToggleCompare() {
  if (!hotel.value) return
  const res = toggleCompare(hotel.value)
  if (!res.ok && res.reason === 'limit') {
    alert('สามารถเปรียบเทียบที่พักได้สูงสุด 3 แห่ง กรุณานำที่พักหนึ่งแห่งออกก่อนเพิ่มรายการใหม่')
  }
}
async function toggleRelatedFav(id) {
  const h = related.value.find((x) => x.id === id)
  if (!h) return
  if (!isLoggedIn.value) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  try {
    await toggleFavorite(h)
  } catch {
    // reverted already
  }
}
</script>

<template>
  <div class="mx-auto max-w-[1190px] px-4 pb-20 pt-6 sm:px-6">
    <!-- breadcrumb -->
    <nav class="mb-4 flex items-center gap-1.5 text-[14px] text-ink-faint">
      <RouterLink to="/" class="font-medium hover:text-indigo-700">หน้าแรก</RouterLink>
      <span class="opacity-60">/</span>
      <RouterLink to="/hotels" class="font-medium hover:text-indigo-700">ค้นหาที่พัก</RouterLink>
      <span class="opacity-60">/</span>
      <span class="font-semibold text-ink">{{ hotel?.name || 'รายละเอียดที่พัก' }}</span>
    </nav>

    <div v-if="loading" class="rounded-2xl border border-dashed border-line bg-white p-16 text-center text-[16px] text-ink-soft">
      กำลังโหลด...
    </div>

    <div v-else-if="errorMessage" class="rounded-2xl border border-red-200 bg-red-50 p-6 text-[15px] text-red-700">
      เชื่อมต่อ API ไม่สำเร็จ: {{ errorMessage }}
      <div class="mt-1 text-red-600/80">ตรวจสอบว่า backend รันอยู่ที่ http://localhost:8000 หรือไม่ หรือที่พักนี้อาจไม่มีอยู่จริง</div>
      <button @click="router.push('/hotels')" class="mt-4 min-h-[44px] rounded-[10px] bg-indigo-600 px-5 text-[15px] font-semibold text-white">กลับไปหน้าค้นหาที่พัก</button>
    </div>

    <div v-else-if="hotel">
      <!-- ============================================ gallery -->
      <div class="grid gap-2" :class="heroThumbs.length ? 'lg:grid-cols-[68%_1fr]' : ''">
        <div class="relative">
          <button
            type="button"
            class="block h-[260px] w-full overflow-hidden rounded-2xl bg-cover bg-center sm:h-[420px]"
            :style="{ backgroundImage: `url(${images[0]})` }"
            @click="openGallery(0)"
          >
            <span
              v-if="images.length > 1"
              class="absolute bottom-3.5 right-3.5 inline-flex items-center gap-1.5 rounded-lg bg-black/65 px-3.5 py-2 text-[13px] font-bold text-white backdrop-blur-sm"
            >
              <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><path d="m21 15-5-5L5 21" /></svg>
              ดูรูปทั้งหมด {{ images.length }} รูป
            </span>
          </button>
          <!-- favourite + compare — top-right of the main photo -->
          <button
            @click="onToggleCompare"
            class="absolute right-16 top-3.5 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white/95 shadow-card backdrop-blur-sm disabled:opacity-50"
            :aria-label="isInCompare(hotel.id) ? 'นำออกจากรายการเปรียบเทียบ' : 'เพิ่มเพื่อเปรียบเทียบ'"
            :disabled="isFull && !isInCompare(hotel.id)"
          >
            <svg viewBox="0 0 24 24" class="h-5 w-5" :class="isInCompare(hotel.id) ? 'text-indigo-600' : 'text-[#C7C3DE]'" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="7" height="16" rx="1.5" /><rect x="14" y="4" width="7" height="16" rx="1.5" /><path d="M10 12h4" /></svg>
          </button>
          <!-- favourite — top-right of the main photo -->
          <button
            @click="toggleFav"
            class="absolute right-3.5 top-3.5 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white/95 shadow-card backdrop-blur-sm"
            aria-label="บันทึกที่พัก"
          >
            <svg viewBox="0 0 24 24" class="h-5 w-5" :class="hotel.fav ? 'fill-red-500 text-red-500' : 'text-[#C7C3DE]'" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.8 8.6c0 4.4-8.8 10-8.8 10s-8.8-5.6-8.8-10a4.8 4.8 0 0 1 8.8-2.7 4.8 4.8 0 0 1 8.8 2.7z" /></svg>
          </button>
        </div>

        <div v-if="heroThumbs.length" class="hidden grid-cols-2 grid-rows-2 gap-2 lg:grid">
          <button
            v-for="(img, i) in heroThumbs"
            :key="i"
            type="button"
            class="h-[102px] w-full overflow-hidden rounded-xl bg-cover bg-center"
            :style="{ backgroundImage: `url(${img})` }"
            @click="openGallery(i + 1)"
          />
        </div>
      </div>

      <!-- ============================================ OVERVIEW — 2 columns (this block only) -->
      <!-- lg:items-start keeps the right card's top aligned with the hotel name row -->
      <div id="overview" class="mt-6 grid scroll-mt-[120px] gap-6 lg:grid-cols-[1fr_340px] lg:items-start">

        <!-- ============ overview-left (~70%) ============ -->
        <div ref="leftOverview" class="order-2 flex min-w-0 flex-col gap-5 lg:order-1">
          <!-- title / location / rating / description -->
          <div>
            <span class="inline-block rounded-full bg-indigo-50 px-3 py-1 text-[14px] font-bold text-indigo-700">{{ hotel.type }}</span>
            <h1 class="mt-3 text-[26px] font-bold leading-tight text-ink sm:text-[32px]">{{ hotel.name }}</h1>
            <div class="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[16px] text-ink-faint">
              <span class="inline-flex items-center gap-1.5">
                <svg viewBox="0 0 24 24" class="h-[18px] w-[18px]" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s-7-7.5-7-12a7 7 0 0 1 14 0c0 4.5-7 12-7 12z" /><circle cx="12" cy="9" r="2.4" /></svg>
                อำเภอ{{ hotel.district }} จังหวัดพิษณุโลก
              </span>
              <template v-if="hotel.reviews > 0">
                <span class="text-ink-faint/60">·</span>
                <span class="inline-flex items-center gap-1.5 font-semibold text-ink">
                  <svg viewBox="0 0 24 24" class="h-[18px] w-[18px] text-gold" fill="currentColor"><path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.8 1.5 6.9L12 17.9l-6.1 3.4 1.5-6.9-5.2-4.8 6.9-.7z" /></svg>
                  คะแนน {{ hotel.rating.toFixed(1) }}
                  <span class="font-normal text-ink-faint">({{ hotel.reviews }} รีวิว)</span>
                </span>
              </template>
            </div>
            <p v-if="hotel.description" class="mt-3.5 whitespace-pre-line text-[16px] leading-[1.7] text-ink-soft">
              {{ descLead }}
            </p>
          </div>

          <!-- category nav — same width as the recommendation card; sticky on desktop only -->
          <nav class="z-20 overflow-x-auto rounded-xl border border-[#E4E1FF] bg-white px-4 sm:px-5 lg:sticky lg:top-[64px]">
            <div class="flex min-h-[54px] items-stretch gap-6 sm:gap-8">
              <button
                v-for="s in SECTIONS"
                :key="s.id"
                @click="scrollToSection(s.id)"
                class="relative whitespace-nowrap py-4 text-[15px] font-semibold transition-colors sm:text-[16px]"
                :class="activeSection === s.id ? 'text-indigo-600' : 'text-ink-faint hover:text-indigo-600'"
              >
                {{ s.label }}
                <span v-if="activeSection === s.id" class="absolute inset-x-0 bottom-0 h-[3px] rounded-t bg-indigo-600"></span>
              </button>
            </div>
          </nav>

          <!-- recommendation card — real, structured reasons carried over from a
               search (spec §9); when the visitor arrived directly (no search
               context for this accommodation), never invent a query match. -->
          <div
            class="relative overflow-hidden rounded-2xl border border-[#E4E1FF] bg-white p-6 sm:p-7"
            style="box-shadow: 0 8px 24px rgba(79, 70, 229, 0.08)"
          >
            <span class="absolute inset-y-0 left-0 w-1 bg-indigo-600"></span>
            <div class="flex items-center gap-3">
              <span class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-[#EEECFF] text-[19px]">✨</span>
              <div>
                <h2 class="text-[22px] font-bold leading-tight text-[#24214A]">เหตุผลที่ StaySense แนะนำ</h2>
                <p class="mt-0.5 text-[14.5px] font-medium text-[#5B55D6]">
                  {{ hasSearchContext ? 'จับคู่จากคำค้นและตัวกรองของคุณ' : 'ค้นหาที่พักเพื่อดูเหตุผลที่ตรงกับความต้องการของคุณ' }}
                </p>
              </div>
            </div>
            <template v-if="hasSearchContext">
              <p v-if="matchedQuery" class="mt-4 text-[15px] text-ink-soft">
                คำค้นของคุณ: <b class="font-bold text-ink">“{{ matchedQuery }}”</b>
              </p>
              <ul class="mt-4 flex flex-col gap-3.5">
                <li v-for="(r, i) in contextReasons" :key="i" class="flex items-start gap-3 text-[16px] leading-[1.7] text-[#3F3F57]">
                  <span class="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-[#EEECFF]">
                    <svg viewBox="0 0 24 24" class="h-[14px] w-[14px] text-indigo-600" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
                  </span>
                  {{ r.message }}
                </li>
              </ul>
              <div v-if="contextPois.length" class="mt-5 border-t border-[#ECEAF8] pt-4">
                <p class="text-[13px] font-bold text-[#5B55D6]">สถานที่ใกล้เคียงที่ตรงกับการค้นหา</p>
                <ul class="mt-2 flex flex-col divide-y divide-[#ECEAF8]">
                  <li v-for="(p, i) in visiblePois" :key="p.poiId + '-' + i" class="flex items-center justify-between gap-3 py-2">
                    <div class="min-w-0">
                      <p class="truncate text-[14px] font-semibold text-[#24214A]">{{ p.name }}</p>
                      <p class="text-[12px] text-[#62627A]">{{ formatPoiDistance(p) }}</p>
                    </div>
                    <a
                      v-if="p.mapUrl"
                      :href="p.mapUrl"
                      target="_blank"
                      rel="noopener"
                      @click="logEvent(hotel.id, 'direction_click')"
                      class="flex-shrink-0 text-[12.5px] font-semibold text-indigo-600 hover:underline"
                    >เปิดเส้นทาง</a>
                  </li>
                </ul>
                <button
                  v-if="contextPois.length > POI_PREVIEW_COUNT"
                  type="button"
                  @click="poisExpanded = !poisExpanded"
                  class="mt-2 text-[12.5px] font-semibold text-indigo-600 hover:underline"
                >{{ poisExpanded ? 'ย่อรายการ' : `ดูสถานที่ใกล้เคียงทั้งหมด (${contextPois.length})` }}</button>
              </div>
            </template>
            <div v-if="hotel.reason" class="mt-5 flex gap-2.5 rounded-xl bg-[#F5F3FF] p-4">
              <svg viewBox="0 0 24 24" class="mt-0.5 h-[18px] w-[18px] flex-shrink-0 text-indigo-600" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6M10 22h4M12 2a6 6 0 0 0-4 10.5c.7.6 1 1.2 1 2.5h6c0-1.3.3-1.9 1-2.5A6 6 0 0 0 12 2z" /></svg>
              <p class="text-[14.5px] leading-[1.65] text-[#3F3F57]">{{ hotel.reason }}</p>
            </div>
          </div>

          <!-- highlights card -->
          <div v-if="highlights.length" class="rounded-2xl border border-[#E8E6F5] bg-white p-6" style="box-shadow: 0 8px 24px rgba(79, 70, 229, 0.06)">
            <h2 class="text-[22px] font-bold leading-tight text-[#24214A]">จุดเด่นของที่พัก</h2>
            <p class="mt-1 text-[14.5px] text-ink-soft">สิ่งที่น่าสนใจและบริการสำคัญของที่พักแห่งนี้</p>
            <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <div
                v-for="(hl, i) in highlights"
                :key="i"
                class="flex items-center gap-2.5 rounded-xl border border-[#E4E1FF] bg-[#F7F6FF] px-3.5 py-3 text-[15px] font-medium text-[#37335C] transition-all hover:-translate-y-0.5 hover:bg-[#EEECFF]"
              >
                <svg viewBox="0 0 24 24" class="h-[19px] w-[19px] flex-shrink-0 text-indigo-600" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path :d="HL_ICONS[hl.icon]" /></svg>
                <span>{{ hl.text }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- ============ overview-right (~30%) — one card; JS keeps it as tall as overview-left ============ -->
        <aside class="order-1 lg:order-2">
          <div
            ref="rightOverview"
            class="flex flex-col overflow-hidden rounded-2xl border border-[#E4E1FF] bg-white"
            style="box-shadow: 0 6px 20px rgba(79, 70, 229, 0.08)"
          >
            <!-- 1. price -->
            <div class="shrink-0 p-4">
              <div class="flex items-baseline gap-1.5">
                <span class="text-[13px] font-medium text-[#62627A]">ราคาเริ่มต้น</span>
                <span class="text-[23px] font-extrabold text-indigo-600">฿{{ startingPrice.toLocaleString() }}</span>
                <span class="text-[13px] font-medium text-[#62627A]">/ คืน</span>
              </div>
              <div class="mt-2.5 flex gap-2">
                <button @click="scrollToSection('rooms')" class="min-h-[40px] flex-1 rounded-xl bg-indigo-600 text-[14.5px] font-semibold text-white shadow hover:brightness-105">ดูห้องพัก</button>
                <a
                  v-if="primaryContact"
                  :href="primaryContact.href"
                  :target="primaryContact.href.startsWith('tel:') ? undefined : '_blank'"
                  rel="noopener"
                  @click="logEvent(hotel.id, 'contact_click')"
                  class="flex min-h-[40px] flex-1 items-center justify-center rounded-xl border border-indigo-200 text-[14.5px] font-semibold text-indigo-600 hover:bg-indigo-50"
                >ติดต่อที่พัก</a>
              </div>
            </div>

            <!-- 2. rating & reviews (one line) -->
            <div class="flex shrink-0 flex-wrap items-center gap-x-2.5 gap-y-1 border-t border-[#ECEAF8] p-4">
              <template v-if="hotel.reviews > 0">
                <span class="text-[22px] font-extrabold leading-none text-indigo-600">{{ hotel.rating.toFixed(1) }}</span>
                <span class="text-[14px] font-bold text-[#24214A]">{{ ratingLabel }}</span>
                <span class="text-[12.5px] text-[#62627A]">({{ hotel.reviews }} รีวิว)</span>
              </template>
              <span v-else class="text-[13.5px] text-[#62627A]">ยังไม่มีรีวิว</span>
              <span class="rounded-full bg-amber-bg px-2 py-0.5 text-[10.5px] font-bold text-amber-ink">ข้อมูลตัวอย่าง</span>
              <button @click="scrollToSection('reviews')" class="ml-auto text-[13px] font-semibold text-indigo-600 hover:underline">ดูรีวิวทั้งหมด</button>
            </div>

            <!-- 3. location -->
            <div id="location" class="shrink-0 scroll-mt-[130px] border-t border-[#ECEAF8]">
              <iframe
                v-if="mapEmbedUrl"
                :src="mapEmbedUrl"
                class="h-[128px] w-full"
                style="border: 0"
                loading="lazy"
                referrerpolicy="no-referrer-when-downgrade"
                title="แผนที่ที่ตั้งที่พัก"
              ></iframe>
              <div class="flex items-start justify-between gap-2 p-4">
                <div class="min-w-0">
                  <p class="text-[14px] font-semibold text-[#24214A]">อำเภอ{{ hotel.district }} จังหวัดพิษณุโลก</p>
                  <p v-if="hotel.landmark && hotel.distanceKm != null" class="mt-0.5 text-[12.5px] text-[#62627A]">
                    ห่างจาก{{ hotel.landmark }} {{ hotel.distanceKm }} กม.<span v-if="hasParking"> · มีที่จอดรถฟรี</span>
                  </p>
                </div>
                <a v-if="mapsUrl" :href="mapsUrl" target="_blank" rel="noopener" @click="logEvent(hotel.id, 'direction_click')" class="flex-shrink-0 whitespace-nowrap text-[13px] font-semibold text-indigo-600 hover:underline">Google Maps</a>
              </div>
            </div>

            <!-- 4. nearby — grows to fill the card; overflowing rows are clipped, full list is in the modal -->
            <div v-if="nearby.popular.length || nearby.nearest.length" class="flex min-h-0 flex-1 flex-col border-t border-[#ECEAF8] p-4">
              <div class="min-h-0 flex-1 overflow-hidden">
                <div v-if="nearby.popular.length">
                  <h3 class="text-[14px] font-bold text-[#24214A]">ที่เที่ยวยอดนิยม</h3>
                  <ul class="mt-1 flex flex-col divide-y divide-[#ECEAF8]">
                    <li v-for="(pl, i) in nearby.popular.slice(0, 3)" :key="i" class="flex items-center justify-between gap-3 py-1.5">
                      <span class="flex min-w-0 items-center gap-2 text-[13.5px] text-[#3F3F57]">
                        <span class="text-[14px] leading-none">{{ placeMeta(pl.category).emoji }}</span>
                        <span class="truncate">{{ pl.name }}</span>
                      </span>
                      <span class="flex-shrink-0 text-[12.5px] font-semibold text-[#62627A]">{{ formatDistance(pl.distanceKm) }}</span>
                    </li>
                  </ul>
                </div>
                <div v-if="nearby.nearest.length" :class="nearby.popular.length ? 'mt-3' : ''">
                  <h3 class="text-[14px] font-bold text-[#24214A]">สถานที่ใกล้ที่สุด</h3>
                  <ul class="mt-1 flex flex-col divide-y divide-[#ECEAF8]">
                    <li v-for="(pl, i) in nearby.nearest.slice(0, 3)" :key="i" class="flex items-center justify-between gap-3 py-1.5">
                      <span class="flex min-w-0 items-center gap-2 text-[13.5px] text-[#3F3F57]">
                        <span class="text-[14px] leading-none">{{ placeMeta(pl.category).emoji }}</span>
                        <span class="truncate">{{ pl.name }}</span>
                      </span>
                      <span class="flex-shrink-0 text-[12.5px] font-semibold text-[#62627A]">{{ formatDistance(pl.distanceKm) }}</span>
                    </li>
                  </ul>
                </div>
              </div>
              <button @click="nearbyModal = true" class="mt-2.5 shrink-0 text-left text-[13px] font-semibold text-indigo-600 hover:underline">ดูสถานที่ใกล้เคียงทั้งหมด</button>
            </div>
          </div>

          <p class="mt-2.5 px-1 text-center text-[11.5px] leading-relaxed text-[#62627A]">
            StaySense เป็นเว็บแนะนำและค้นหาที่พัก ไม่ใช่ผู้รับจองโดยตรง
          </p>
        </aside>
      </div>
      <!-- ============================================ end of 2-column overview -->

      <!-- ===== ROOMS — full width, its own section ===== -->
      <section v-if="hotel.roomTypes && hotel.roomTypes.length" id="rooms" class="mt-14 scroll-mt-[130px]">
        <RoomTypeList :room-types="hotel.roomTypes" :type-code="hotel.typeCode" />
      </section>

      <section id="amenities" class="mt-14 scroll-mt-[130px] rounded-2xl border border-line bg-white p-6">
        <h2 class="mb-4 text-[22px] font-bold text-ink sm:text-[24px]">สิ่งอำนวยความสะดวก</h2>
        <AmenitiesGrid :codes="hotel.amenities" />
      </section>

      <section v-if="hasMoreAbout" class="mt-6 rounded-2xl border border-line bg-white p-6">
        <h2 class="mb-2.5 text-[22px] font-bold text-ink sm:text-[24px]">เกี่ยวกับที่พักเพิ่มเติม</h2>
        <p class="whitespace-pre-line text-[16px] leading-[1.75] text-ink-soft">{{ hotel.description }}</p>
      </section>

      <section v-if="policyRows.length" class="mt-6 rounded-2xl border border-line bg-white p-6">
        <h2 class="mb-5 text-[22px] font-bold text-ink sm:text-[24px]">นโยบายและเงื่อนไข</h2>
        <div class="grid gap-x-10 gap-y-6 sm:grid-cols-2">
          <div v-for="row in policyRows" :key="row.label" class="flex items-start gap-3">
            <svg viewBox="0 0 24 24" class="mt-0.5 h-[19px] w-[19px] flex-shrink-0 text-indigo-500" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path :d="POLICY_ICONS[row.icon]" /></svg>
            <div class="min-w-0">
              <div class="text-[14px] font-bold text-ink">{{ row.label }}</div>
              <div class="mt-1 whitespace-pre-line text-[15px] leading-[1.65] text-ink-soft">{{ row.value }}</div>
            </div>
          </div>
        </div>
      </section>

      <section id="reviews" class="mt-14 scroll-mt-[130px] rounded-2xl border border-line bg-white p-6">
        <div v-if="hasCategoryRatings" class="mb-6 rounded-xl bg-pagebg p-4">
          <div class="mb-2.5 flex items-center gap-2 text-[14px] font-bold text-ink-soft">
            คะแนนแยกตามหมวด
            <span class="rounded-full bg-amber-bg px-2 py-0.5 text-[11px] font-bold text-amber-ink">ข้อมูลตัวอย่าง</span>
          </div>
          <CategoryRatings :ratings="hotel.categoryRatings" />
        </div>
        <ReviewsSection :accommodation-id="hotel.id" :rating="hotel.rating" :review-count="hotel.reviews" />
      </section>

      <section v-if="related.length" class="mt-14 rounded-2xl border border-line bg-white p-6">
        <h2 class="mb-5 text-[22px] font-bold text-ink sm:text-[24px]">ที่พักใกล้เคียงในอำเภอ{{ hotel.district }}</h2>
        <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <StayCard v-for="r in related" :key="r.id" :stay="r" @toggle-fav="toggleRelatedFav" />
        </div>
      </section>
    </div>

    <ImageGalleryModal
      :visible="gallery.open"
      :title="`รูปภาพทั้งหมดของ ${hotel?.name || ''}`"
      :images="gallery.images"
      :initial-index="gallery.startIndex"
      :category-labels="galleryCategoryLabels"
      @close="closeGallery"
    />
    <NearbyPlacesModal
      v-if="nearbyModal"
      :popular="nearby.popular"
      :all="nearby.all"
      @close="nearbyModal = false"
    />
  </div>
</template>
