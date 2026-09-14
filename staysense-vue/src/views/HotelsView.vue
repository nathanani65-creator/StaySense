<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SearchCapsule from '../components/SearchCapsule.vue'
import LocateButton from '../components/LocateButton.vue'
import LocationPermissionModal from '../components/LocationPermissionModal.vue'
import FilterSidebar from '../components/FilterSidebar.vue'
import HotelCard from '../components/HotelCard.vue'
import DistrictMap from '../components/DistrictMap.vue'
import Pagination from '../components/Pagination.vue'
import ChipRow from '../components/ChipRow.vue'
import { useReferenceData } from '../composables/useReferenceData'
import { useAuth } from '../composables/useAuth'
import { useFavorites } from '../composables/useFavorites'
import { useCompare } from '../composables/useCompare'
import { useNearbySearch } from '../composables/useNearbySearch'
import { useSearchContext } from '../composables/useSearchContext'
import { fetchAccommodations, fetchDistrictCounts, searchAccommodations, searchNearby } from '../api/hotels'
import { getCurrentPosition, GEO_ERROR_MESSAGES, detectNearMe, detectTypeCode } from '../utils/geolocation'

const route = useRoute()
const router = useRouter()
const { districts, accommodationTypes, amenities, ensureLoaded, amenityLabel } = useReferenceData()
const { isLoggedIn } = useAuth()
const { toggleFavorite } = useFavorites()
const { isInCompare, toggleCompare, isFull } = useCompare()
const { consumePending } = useNearbySearch()
const { setContext } = useSearchContext()

const activeType = ref('') // accommodation_types.code, set once reference data loads
const query = ref('')
const sort = ref('recommended')
const view = ref('list')
const page = ref(1)
const pageSize = 6
const sidebarOpen = ref(false)

const loading = ref(true)
const errorMessage = ref(null)
const items = ref([])
const total = ref(0)
const districtCounts = ref({})

// what the search system understood from the current query text — populated
// only by an actual /api/search or /api/search/nearby call (never for the
// plain, query-less listing), never for a keystroke (spec §3/§16/§10).
const searchMeta = ref(null)
const otherSuggestions = ref([])
const useRawQuery = ref(false) // "ใช้ข้อความเดิม" — bypass typo correction for the next request
const confidenceDismissed = ref(false)

// a ref (not reactive()) so FilterSidebar's v-model can replace the whole object at once
const filters = ref({
  districts: new Set(),
  priceMin: 200,
  priceMax: 5000,
  tier: null,
  ratingMin: null,
  amenities: new Set(),
  distance: null,
})

const TIER_RANGES = {
  '0-1000': [0, 1000],
  '1001-2000': [1001, 2000],
  '2001-3000': [2001, 3000],
  '3000+': [3001, undefined],
}

// price-range slider intersected with the selected quick-tier, if any —
// shared by the normal filter flow and the nearby-search payload builder.
function effectivePriceRange() {
  const f = filters.value
  let priceMin = f.priceMin
  let priceMax = f.priceMax >= 5000 ? undefined : f.priceMax
  const tierRange = f.tier ? TIER_RANGES[f.tier] : null
  if (tierRange) {
    priceMin = Math.max(priceMin, tierRange[0])
    if (tierRange[1] !== undefined) priceMax = priceMax !== undefined ? Math.min(priceMax, tierRange[1]) : tierRange[1]
  }
  return { priceMin, priceMax }
}

function buildFilterParams({ includeDistrict = true } = {}) {
  const f = filters.value
  const { priceMin, priceMax } = effectivePriceRange()

  let distanceMaxKm
  if (f.distance === '5') distanceMaxKm = 5
  else if (f.distance === '10') distanceMaxKm = 10

  let sortValue = sort.value
  if (f.distance === 'nearest' && sortValue === 'recommended') sortValue = 'distance-asc'

  const params = {
    type: activeType.value || undefined,
    price_min: priceMin,
    price_max: priceMax,
    rating_min: f.ratingMin || undefined,
    amenities: [...f.amenities],
    distance_max_km: distanceMaxKm,
    sort: sortValue,
  }
  if (includeDistrict) params.district = [...f.districts]
  return params
}

async function refreshList() {
  loading.value = true
  errorMessage.value = null
  try {
    const common = buildFilterParams()
    if (query.value.trim()) {
      const result = await searchAccommodations({
        query: query.value,
        page: page.value,
        page_size: pageSize,
        raw: useRawQuery.value,
        ...common,
      })
      items.value = result.items
      total.value = result.total
      searchMeta.value = result.meta
      otherSuggestions.value = result.otherSuggestions || []
      setContext({ ...result.meta, items: result.items })
    } else {
      const result = await fetchAccommodations({ ...common, page: page.value, page_size: pageSize })
      items.value = result.items
      total.value = result.total
      searchMeta.value = null
      otherSuggestions.value = []
    }
  } catch (e) {
    errorMessage.value = e.message || String(e)
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function refreshCounts() {
  try {
    const params = buildFilterParams({ includeDistrict: false })
    delete params.sort // counts endpoint doesn't take a sort param
    const result = await fetchDistrictCounts(params)
    districtCounts.value = result.counts
  } catch {
    districtCounts.value = {}
  }
}

/* --------------------------------------------------- "ใกล้ฉัน" (nearby) mode */

const nearbyMode = ref(false)
const nearbyCoords = ref(null) // { latitude, longitude } — real, in-memory only, never in the URL
const nearbyRadius = ref(10)
const nearbySort = ref('relevance') // 'relevance' | 'distance' | 'price-asc'
const nearbyResult = ref(null) // full NearbySearchResponse, for title/subtitle/expansion message
const locating = ref(false)
const permissionModal = ref({ visible: false, message: '' })

function buildNearbyPayload() {
  const f = filters.value
  const { priceMin, priceMax } = effectivePriceRange()
  return {
    latitude: nearbyCoords.value.latitude,
    longitude: nearbyCoords.value.longitude,
    query: query.value,
    accommodation_type: activeType.value || undefined,
    radius_km: nearbyRadius.value,
    price_min: priceMin,
    price_max: priceMax,
    rating_min: f.ratingMin || undefined,
    facilities: [...f.amenities],
    district: [...f.districts],
    sort_by: nearbySort.value,
    raw: useRawQuery.value,
    page: page.value,
    page_size: pageSize,
  }
}

async function runNearbySearch() {
  if (!nearbyCoords.value) return
  loading.value = true
  errorMessage.value = null
  try {
    const result = await searchNearby(buildNearbyPayload())
    nearbyResult.value = result
    items.value = result.items
    total.value = result.total
    searchMeta.value = result
    otherSuggestions.value = result.otherSuggestions || []
    setContext({ ...result, originalQuery: result.query, items: result.items })
  } catch (e) {
    errorMessage.value = e.message || String(e)
    nearbyResult.value = null
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

/**
 * Always asks the browser for a fresh position — never reuses a cached one,
 * since the visitor may have moved. `preserveType` keeps whatever type tab
 * is already active (used by the Locate button and "เปลี่ยนตำแหน่ง"); a typed
 * "ใกล้ฉัน"-style query always derives the type from the text itself.
 */
async function requestLocationAndSearch(q, { preserveType = false } = {}) {
  locating.value = true
  try {
    const { latitude, longitude } = await getCurrentPosition()
    nearbyCoords.value = { latitude, longitude }
    nearbyMode.value = true
    query.value = q
    const detected = detectTypeCode(q)
    if (detected) activeType.value = detected
    else if (!preserveType) activeType.value = ''
    nearbySort.value = q.trim() ? 'relevance' : 'distance'
    nearbyRadius.value = 10
    page.value = 1
    permissionModal.value = { visible: false, message: '' }
    await runNearbySearch()
  } catch (e) {
    permissionModal.value = { visible: true, message: GEO_ERROR_MESSAGES[e?.code] || GEO_ERROR_MESSAGES.POSITION_UNAVAILABLE }
  } finally {
    locating.value = false
  }
}

function onModalRetry() {
  requestLocationAndSearch(query.value, { preserveType: true })
}
function onModalChooseDistrict() {
  permissionModal.value = { visible: false, message: '' }
  sidebarOpen.value = true
}
function onModalSearchLandmark(name) {
  permissionModal.value = { visible: false, message: '' }
  nearbyMode.value = false
  nearbyResult.value = null
  nearbyCoords.value = null
  query.value = name
  page.value = 1
}

function editSearch() {
  nearbyMode.value = false
  nearbyResult.value = null
  nearbyCoords.value = null
  refreshList()
  refreshCounts()
}
function clearNearbyFilters() {
  filters.value = { districts: new Set(), priceMin: 200, priceMax: 5000, tier: null, ratingMin: null, amenities: new Set(), distance: null }
  page.value = 1
}
function changeLocation() {
  requestLocationAndSearch(query.value, { preserveType: true })
}

/* -------------------------------------------------------------------------- */

// combined key: any change here means "go fetch again"
const activeTypeLabel = computed(
  () => accommodationTypes.value.find((t) => t.code === activeType.value)?.key || 'ที่พัก'
)

const paramsKey = computed(() =>
  JSON.stringify({
    type: activeType.value,
    districts: [...filters.value.districts].sort(),
    priceMin: filters.value.priceMin,
    priceMax: filters.value.priceMax,
    tier: filters.value.tier,
    ratingMin: filters.value.ratingMin,
    amenities: [...filters.value.amenities].sort(),
    distance: filters.value.distance,
    sort: sort.value,
    page: page.value,
    query: query.value,
    nearbyMode: nearbyMode.value,
    nearbyRadius: nearbyRadius.value,
    nearbySort: nearbySort.value,
  })
)

onMounted(async () => {
  ensureLoaded() // fire-and-forget: fallback data is already in the refs, no need to wait

  const pending = consumePending()
  if (pending && pending.useCurrentLocation) {
    nearbyCoords.value = { latitude: pending.latitude, longitude: pending.longitude }
    nearbyMode.value = true
    query.value = pending.query || ''
    activeType.value = pending.accommodationType || ''
    nearbyRadius.value = pending.radiusKm || 10
    nearbySort.value = pending.sortBy || 'relevance'
    await runNearbySearch()
  } else {
    const typeFromUrl = route.query.type ? String(route.query.type) : null
    const matchedType = typeFromUrl && accommodationTypes.value.find((t) => t.code === typeFromUrl)
    activeType.value =
      matchedType?.code ||
      accommodationTypes.value.find((t) => t.key === 'โรงแรม')?.code ||
      accommodationTypes.value[0]?.code ||
      ''

    const q = route.query.q
    if (q) query.value = String(q)

    await refreshList()
    refreshCounts()
  }

  watch(paramsKey, () => {
    if (nearbyMode.value) {
      runNearbySearch()
    } else {
      refreshList()
      refreshCounts()
    }
  })
})

function runSearch(q) {
  if (!nearbyMode.value && detectNearMe(q)) {
    requestLocationAndSearch(q)
    return
  }
  query.value = q
  useRawQuery.value = false // a fresh query text always starts corrected, not raw
  confidenceDismissed.value = false
  if (nearbyMode.value) {
    // a freshly typed query is a new explicit intent — let it re-derive the
    // type filter, same as entering nearby mode fresh would (§4)
    const detected = detectTypeCode(q)
    if (detected) activeType.value = detected
  }
  page.value = 1
}

function confirmCorrection() {
  confidenceDismissed.value = true
}
function useOriginalQueryInstead() {
  useRawQuery.value = true
  confidenceDismissed.value = true
  page.value = 1
  if (nearbyMode.value) runNearbySearch()
  else refreshList()
}

function handleNotFoundOption(opt) {
  if (opt.startsWith('เลือกชื่อ') || opt === 'เลือกอำเภอ') {
    sidebarOpen.value = true
  } else if (opt === 'ขยายรัศมี') {
    if (nearbyMode.value) {
      nearbyRadius.value = Math.min(50, nearbyRadius.value * 2 || 10)
    } else {
      clearFilters()
    }
  } else if (opt === 'ล้างตัวกรอง') {
    nearbyMode.value ? clearNearbyFilters() : clearFilters()
  }
  // "ดูที่พักอื่น" — otherSuggestions is already rendered below, nothing to do
}

function clearFilters() {
  filters.value = {
    districts: new Set(),
    priceMin: 200,
    priceMax: 5000,
    tier: null,
    ratingMin: null,
    amenities: new Set(),
    distance: null,
  }
  page.value = 1
}

function clearAll() {
  clearFilters()
  query.value = ''
}

async function toggleFav(id) {
  const h = items.value.find((x) => x.id === id)
  if (!h) return
  if (!isLoggedIn.value) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  try {
    await toggleFavorite(h)
  } catch {
    // toggleFavorite already reverted h.fav; nothing else to do
  }
}

function onToggleCompare(item) {
  const res = toggleCompare(item)
  if (!res.ok && res.reason === 'limit') {
    alert('สามารถเปรียบเทียบที่พักได้สูงสุด 3 แห่ง กรุณานำที่พักหนึ่งแห่งออกก่อนเพิ่มรายการใหม่')
  }
}

function onMapSelect(key) {
  if (key === null) {
    filters.value = { ...filters.value, districts: new Set() }
  } else if (filters.value.districts.has(key)) {
    filters.value = { ...filters.value, districts: new Set([...filters.value.districts].filter((d) => d !== key)) }
  } else {
    filters.value = { ...filters.value, districts: new Set([key]) }
  }
  page.value = 1
}
</script>

<template>
  <div class="mx-auto max-w-[1320px] px-8 pb-16 pt-[26px]">
    <div class="mb-3.5 flex items-center gap-1.5 text-[13px] text-ink-faint">
      <RouterLink to="/" class="font-medium hover:text-indigo-700">หน้าแรก</RouterLink>
      <span class="opacity-60">/</span>
      <span class="font-medium">ประเภทที่พัก</span>
      <span class="opacity-60">/</span>
      <span class="font-semibold text-ink">{{ nearbyMode ? 'ใกล้คุณ' : activeTypeLabel }}</span>
    </div>

    <section class="hero-cover mb-[26px] rounded-[22px] px-10 pb-[34px] pt-[52px]">
      <template v-if="nearbyMode && nearbyResult">
        <h1 class="max-w-[680px] text-[32px] font-extrabold text-white [text-shadow:0_2px_18px_rgba(10,8,30,0.35)]">{{ nearbyResult.title }}</h1>
        <p class="mb-[26px] mt-2 max-w-[600px] text-[15px] text-white/86">{{ nearbyResult.subtitle }}</p>
      </template>
      <template v-else>
        <h1 class="max-w-[680px] text-[32px] font-extrabold text-white [text-shadow:0_2px_18px_rgba(10,8,30,0.35)]">
          {{ searchMeta?.interpretedAs ? searchMeta.interpretedAs + 'ในจังหวัดพิษณุโลก' : activeTypeLabel + 'ในจังหวัดพิษณุโลก' }}
        </h1>
        <p class="mb-[26px] mt-2 max-w-[600px] text-[15px] text-white/86">
          ค้นหาและเปรียบเทียบ{{ activeTypeLabel }}ที่ตรงกับความต้องการของคุณ ด้วยระบบค้นหาเชิงความหมาย (Semantic Search)
        </p>
      </template>

      <div class="flex flex-col items-stretch gap-3 sm:flex-row">
        <SearchCapsule v-model="query" placeholder='ลองค้นหา เช่น "ที่พักเงียบสงบใกล้ธรรมชาติ ราคาไม่เกิน 1,500 บาท"' @search="runSearch" />
        <LocateButton :loading="locating" @locate="() => requestLocationAndSearch(query, { preserveType: true })" />
      </div>
      <div class="mt-3 flex items-center gap-1.5 pl-0.5 text-xs text-white/75">
        <svg viewBox="0 0 24 24" class="h-3.5 w-3.5 text-indigo-300" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M12 3v3M12 18v3M4.2 4.2l2.2 2.2M17.6 17.6l2.2 2.2M3 12h3M18 12h3M4.2 19.8l2.2-2.2M17.6 6.4l2.2-2.2" />
        </svg>
        <span><b class="font-bold text-[#FFD9A0]">Semantic Search</b> — เข้าใจความหมายของประโยค ไม่ใช่แค่คำค้นตรงตัว เช่น "ริมน้ำ" จะพาไปเจอที่พักติดแม่น้ำน่านโดยอัตโนมัติ</span>
      </div>
    </section>

    <!-- what the search system understood from the current query text (spec §4/§10) -->
    <div v-if="searchMeta && query.trim()" class="mb-[18px] rounded-2xl border border-line bg-white p-4">
      <p class="text-[13px] text-ink-soft">
        กำลังแสดงผลสำหรับ <b class="font-extrabold text-ink">“{{ searchMeta.normalizedQuery }}”</b>
      </p>
      <div
        v-if="!confidenceDismissed && searchMeta.confidence != null && searchMeta.confidence < 0.85"
        class="mt-2.5 flex flex-wrap items-center gap-2.5 rounded-[10px] border border-amber-line bg-amber-bg px-3.5 py-2.5 text-[12.5px] font-semibold text-amber-ink"
      >
        <span>คุณหมายถึง “{{ searchMeta.normalizedQuery }}” ใช่หรือไม่?</span>
        <button @click="confirmCorrection" class="rounded-lg bg-amber-icon px-3 py-1.5 font-bold text-white">ใช่ ค้นหาคำนี้</button>
        <button @click="useOriginalQueryInstead" class="rounded-lg border border-amber-line bg-white px-3 py-1.5 font-bold text-amber-ink">ใช้ข้อความเดิม</button>
      </div>
      <div v-if="searchMeta.detectedFilters?.length" class="mt-2.5 flex flex-wrap gap-1.5">
        <span v-for="(f, i) in searchMeta.detectedFilters" :key="i" class="rounded-full bg-indigo-50 px-3 py-1 text-[12px] font-bold text-indigo-700">{{ f }}</span>
      </div>
    </div>

    <!-- named POI/category with no resolvable data for any candidate — never claim a match (spec §12/§15) -->
    <div v-if="searchMeta?.notFoundMessage" class="mb-[18px] rounded-2xl border border-dashed border-line bg-white p-6 text-center">
      <p class="text-[13.5px] font-semibold text-ink-soft">{{ searchMeta.notFoundMessage }}</p>
      <div class="mt-3 flex flex-wrap justify-center gap-2">
        <button
          v-for="(opt, i) in searchMeta.notFoundOptions"
          :key="i"
          @click="handleNotFoundOption(opt)"
          class="rounded-[10px] border-[1.5px] border-line px-4 py-2 text-[12.5px] font-bold text-ink-soft hover:bg-pagebg"
        >
          {{ opt }}
        </button>
      </div>
      <template v-if="otherSuggestions.length">
        <p class="mb-3 mt-6 text-left text-[13.5px] font-extrabold text-ink">ที่พักอื่นที่อาจสนใจ</p>
        <div class="grid grid-cols-1 gap-4 text-left sm:grid-cols-2">
          <HotelCard v-for="h in otherSuggestions" :key="h.id" :hotel="h" :amenities="amenities" :query="query" :show-compare="false" />
        </div>
      </template>
    </div>

    <div class="mb-[22px] flex flex-wrap gap-2.5">
      <button
        v-if="nearbyMode"
        @click="activeType = ''; page = 1"
        class="flex items-center gap-2 rounded-xl border-[1.5px] px-5 py-2.5 text-sm font-bold transition"
        :class="activeType === '' ? 'border-indigo-600 bg-indigo-600 text-white shadow' : 'border-line bg-white text-ink-soft hover:border-[#B6B2F2] hover:text-indigo-700'"
      >
        ทั้งหมด
      </button>
      <button
        v-for="t in accommodationTypes"
        :key="t.code"
        @click="activeType = t.code; page = 1"
        class="flex items-center gap-2 rounded-xl border-[1.5px] px-5 py-2.5 text-sm font-bold transition"
        :class="activeType === t.code ? 'border-indigo-600 bg-indigo-600 text-white shadow' : 'border-line bg-white text-ink-soft hover:border-[#B6B2F2] hover:text-indigo-700'"
      >
        {{ t.key }}
      </button>
    </div>

    <!-- nearby-search condition bar: radius, sort, applied-filter chips, actions (spec §6/§7) -->
    <div v-if="nearbyMode" class="mb-[22px] rounded-2xl border border-line bg-white p-4">
      <div v-if="nearbyResult?.radiusExpandedMessage" class="mb-3 rounded-[10px] border border-amber-line bg-amber-bg px-3.5 py-2.5 text-[12.5px] font-semibold text-amber-ink">
        {{ nearbyResult.radiusExpandedMessage }}
      </div>
      <div class="mb-3.5 flex flex-wrap gap-1.5">
        <span class="rounded-full bg-indigo-50 px-3 py-1.5 text-[12px] font-bold text-indigo-700">📍 ใกล้ตำแหน่งปัจจุบันของคุณ</span>
        <span v-if="activeType" class="rounded-full bg-indigo-50 px-3 py-1.5 text-[12px] font-bold text-indigo-700">{{ activeTypeLabel }}</span>
        <span class="rounded-full bg-indigo-50 px-3 py-1.5 text-[12px] font-bold text-indigo-700">ภายใน {{ nearbyRadius }} กม.</span>
        <span v-if="filters.priceMax < 5000" class="rounded-full bg-indigo-50 px-3 py-1.5 text-[12px] font-bold text-indigo-700">งบไม่เกิน {{ filters.priceMax.toLocaleString() }} บาท</span>
        <span v-for="a in [...filters.amenities]" :key="a" class="rounded-full bg-indigo-50 px-3 py-1.5 text-[12px] font-bold text-indigo-700">{{ amenityLabel(a) }}</span>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-1.5">
          <span class="mr-1 text-[12.5px] font-bold text-ink-soft">รัศมี:</span>
          <button
            v-for="r in [5, 10, 25, 50]"
            :key="r"
            @click="nearbyRadius = r; page = 1"
            class="rounded-lg border-[1.5px] px-3 py-1.5 text-[12.5px] font-bold"
            :class="nearbyRadius === r ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-line bg-white text-ink-soft hover:border-[#D8D5F5]'"
          >
            {{ r }} กม.
          </button>
        </div>
        <select v-model="nearbySort" class="rounded-[10px] border-[1.5px] border-line bg-white px-3.5 py-2 text-[13px] font-semibold">
          <option value="relevance">เรียงตามความเกี่ยวข้อง</option>
          <option value="distance">เรียงตามใกล้ที่สุด</option>
          <option value="price-asc">เรียงตามราคาต่ำที่สุด</option>
        </select>
      </div>

      <div class="mt-3.5 flex flex-wrap gap-2 border-t border-line pt-3.5">
        <button @click="editSearch" class="rounded-[10px] border-[1.5px] border-line px-4 py-2 text-[12.5px] font-bold text-ink-soft hover:bg-pagebg">แก้ไขการค้นหา</button>
        <button @click="clearNearbyFilters" class="rounded-[10px] border-[1.5px] border-line px-4 py-2 text-[12.5px] font-bold text-ink-soft hover:bg-pagebg">ล้างตัวกรอง</button>
        <button @click="changeLocation" :disabled="locating" class="rounded-[10px] border-[1.5px] border-line px-4 py-2 text-[12.5px] font-bold text-ink-soft hover:bg-pagebg disabled:opacity-50">เปลี่ยนตำแหน่ง</button>
        <button @click="view = view === 'map' ? 'list' : 'map'" class="rounded-[10px] border-[1.5px] border-line px-4 py-2 text-[12.5px] font-bold text-ink-soft hover:bg-pagebg">ดูบนแผนที่</button>
      </div>
    </div>

    <div class="grid grid-cols-1 items-start gap-[26px] lg:grid-cols-[272px_1fr]">
      <button @click="sidebarOpen = !sidebarOpen" class="mb-4 flex items-center gap-2 rounded-[10px] border-[1.5px] border-line bg-white px-4 py-2.5 text-[13.5px] font-bold lg:hidden">
        <svg viewBox="0 0 24 24" class="h-4 w-4 text-indigo-600" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 6h16M7 12h10M10 18h4" /></svg>
        ตัวกรอง
      </button>
      <div :class="sidebarOpen ? 'block' : 'hidden lg:block'">
        <FilterSidebar v-model="filters" :districts="districts" :amenities="amenities" @clear="nearbyMode ? clearNearbyFilters() : clearFilters()" />
      </div>

      <main class="min-w-0">
        <div class="mb-3.5 flex flex-wrap items-center justify-between gap-4">
          <div class="text-[16.5px] font-extrabold">พบ{{ nearbyMode ? '' : activeTypeLabel }} <b class="text-indigo-700">{{ total }}</b> แห่ง</div>
          <div v-if="!nearbyMode" class="flex flex-wrap items-center gap-2.5">
            <select v-model="sort" class="rounded-[10px] border-[1.5px] border-line bg-white px-3.5 py-2.5 text-[13.5px] font-semibold">
              <option value="recommended">แนะนำ</option>
              <option value="price-asc">ราคา: ต่ำ → สูง</option>
              <option value="price-desc">ราคา: สูง → ต่ำ</option>
              <option value="rating-desc">คะแนนสูงสุด</option>
              <option value="distance-asc">ใกล้ที่สุด</option>
            </select>
            <div class="flex overflow-hidden rounded-[10px] border-[1.5px] border-line">
              <button @click="view = 'list'" class="flex items-center gap-1.5 border-r-[1.5px] border-line px-4 py-2.5 text-[13.5px] font-bold" :class="view === 'list' ? 'bg-indigo-600 text-white' : 'bg-white text-ink-soft'">
                <svg viewBox="0 0 24 24" class="h-[15px] w-[15px]" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" /></svg>
                รายการ
              </button>
              <button @click="view = 'map'" class="flex items-center gap-1.5 px-4 py-2.5 text-[13.5px] font-bold" :class="view === 'map' ? 'bg-indigo-600 text-white' : 'bg-white text-ink-soft'">
                <svg viewBox="0 0 24 24" class="h-[15px] w-[15px]" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 20 3 17V4l6 3m0 13 6-3m-6 3V7m6 10 6 3V7l-6-3m0 13V4m0 3-6-3" /></svg>
                แผนที่
              </button>
            </div>
          </div>
        </div>

        <ChipRow v-if="!nearbyMode" :filters="filters" :query="query" :amenities="amenities" @update:filters="(v) => (filters = v)" @update:query="runSearch" @clear-all="clearAll" />

        <div v-if="errorMessage" class="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
          เชื่อมต่อ API ไม่สำเร็จ: {{ errorMessage }}
          <div class="mt-1 text-red-600/80">ตรวจสอบว่า backend รันอยู่ที่ http://localhost:8000 หรือไม่</div>
        </div>

        <div v-else class="grid grid-cols-1 gap-4" :class="view === 'list' ? 'lg:grid-cols-[minmax(0,1fr)_420px]' : ''">
          <div v-show="view === 'list'" class="flex flex-col gap-4">
            <div v-if="loading" class="rounded-2xl border border-dashed border-line bg-white p-14 text-center text-ink-soft">
              {{ locating ? 'กำลังระบุตำแหน่ง...' : 'กำลังโหลด...' }}
            </div>
            <template v-else-if="items.length">
              <HotelCard
                v-for="h in items"
                :key="h.id"
                :hotel="h"
                :matched="!!query.trim()"
                :amenities="amenities"
                :query="query"
                :in-compare="isInCompare(h.id)"
                :compare-disabled="isFull"
                @toggle-fav="toggleFav"
                @toggle-compare="onToggleCompare"
              />
            </template>
            <div v-else-if="nearbyMode" class="rounded-2xl border border-dashed border-line bg-white p-14 text-center text-ink-soft">
              <h4 class="mb-1.5 text-base font-extrabold text-ink">ไม่พบที่พักตามเงื่อนไขในบริเวณนี้</h4>
              <p>กรุณาขยายระยะทางหรือปรับตัวกรอง</p>
              <button @click="clearNearbyFilters" class="mt-3.5 rounded-[10px] bg-indigo-600 px-[22px] py-2.5 text-[13.5px] font-bold text-white">ล้างตัวกรองทั้งหมด</button>
            </div>
            <div v-else class="rounded-2xl border border-dashed border-line bg-white p-14 text-center text-ink-soft">
              <h4 class="mb-1.5 text-base font-extrabold text-ink">ไม่พบที่พักที่ตรงกับตัวกรอง</h4>
              <p>ลองปรับช่วงราคา หรือ ล้างตัวกรองบางส่วนเพื่อดูตัวเลือกเพิ่มเติม</p>
              <button @click="clearAll" class="mt-3.5 rounded-[10px] bg-indigo-600 px-[22px] py-2.5 text-[13.5px] font-bold text-white">ล้างตัวกรองทั้งหมด</button>
            </div>
            <Pagination v-if="items.length" v-model:page="page" :page-size="pageSize" :total="total" />
          </div>

          <div :class="view === 'map' ? 'lg:col-span-2' : ''" class="min-h-[420px] lg:sticky lg:top-[86px] lg:h-[calc(100vh-110px)] lg:min-h-[520px]">
            <DistrictMap :districts="districts" :counts="districtCounts" :selected="filters.districts" @select="onMapSelect" />
          </div>
        </div>
      </main>
    </div>
  </div>

  <LocationPermissionModal
    :visible="permissionModal.visible"
    :message="permissionModal.message"
    @retry="onModalRetry"
    @choose-district="onModalChooseDistrict"
    @search-landmark="onModalSearchLandmark"
    @close="permissionModal = { visible: false, message: '' }"
  />
</template>
