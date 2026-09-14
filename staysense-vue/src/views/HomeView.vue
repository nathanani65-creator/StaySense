<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import SearchCapsule from '../components/SearchCapsule.vue'
import LocateButton from '../components/LocateButton.vue'
import LocationPermissionModal from '../components/LocationPermissionModal.vue'
import CategoryCard from '../components/CategoryCard.vue'
import AreaCard from '../components/AreaCard.vue'
import HomeSection from '../components/HomeSection.vue'
import OnboardingBox from '../components/OnboardingBox.vue'
import { fetchHome } from '../api/home'
import { saveMyPreferences } from '../api/preferences'
import { useAuth } from '../composables/useAuth'
import { useReferenceData } from '../composables/useReferenceData'
import { useNearbySearch } from '../composables/useNearbySearch'
import { useSearchContext } from '../composables/useSearchContext'
import { getCurrentPosition, GEO_ERROR_MESSAGES, detectNearMe, detectTypeCode } from '../utils/geolocation'

const router = useRouter()
const { isLoggedIn } = useAuth()
const { amenities, ensureLoaded } = useReferenceData()
const { setPending } = useNearbySearch()
const { setContext } = useSearchContext()

// local files under public/images/categories/ — anything in public/ is
// served as-is from the site root by Vite, so "public/images/categories/
// hotel.jpg" is reachable at "/images/categories/hotel.jpg".
const categories = [
  {
    code: 'hotel', key: 'โรงแรม',
    icon: '<path d="M3 21V8l9-5 9 5v13"/><path d="M9 21v-6h6v6M9 12h.01M15 12h.01M9 8h.01M15 8h.01"/>',
    img: '/images/categories/hotel.jpg',
  },
  {
    code: 'resort', key: 'รีสอร์ต',
    icon: '<path d="M2 22h20M4 18h2M18 18h2M6 18v-3a6 6 0 0 1 12 0v3M12 3v3"/>',
    img: '/images/categories/Resort.jpg',
  },
  {
    code: 'homestay', key: 'โฮมสเตย์',
    icon: '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-5h4v5"/>',
    img: '/images/categories/Homestay.jpg',
  },
]

const areas = [
  { name: 'อำเภอเมืองพิษณุโลก', img: '/images/muang.jpg' },
  { name: 'อำเภอวังทอง', img: '/images/wang.jpg' },
  { name: 'อำเภอนครไทย', img: '/images/nakhon.jpg' },
  { name: 'อำเภอเนินมะปราง', img: '/images/maprang.png' },
]

const examples = [
  { label: 'ที่พักสำหรับครอบครัว มีสระว่ายน้ำ', icon: '<circle cx="8" cy="8" r="2.5"/><circle cx="17" cy="9" r="2"/><path d="M2 20v-1a5 5 0 0 1 5-5h2a5 5 0 0 1 5 5v1"/>' },
  { label: 'ที่พักวิวภูเขา บรรยากาศเงียบสงบ', icon: '<path d="m3 17 5-6 4 4 5-7 4 5"/><path d="M3 20h18"/>' },
  { label: 'โรงแรมในเมือง ราคาไม่เกิน 1,000 บาท', icon: '<path d="M3 21V8l9-5 9 5v13"/><path d="M9 21v-6h6v6"/>' },
]

/* -------------------------------------------------------------- data load */

const home = ref(null)
const loading = ref(true)
const errorMessage = ref(null)
const searchQuery = ref('')
const onboardingSkipped = ref(false)

async function loadHome() {
  loading.value = true
  errorMessage.value = null
  try {
    home.value = await fetchHome({ q: searchQuery.value || undefined })
    // the hero search box is a real search entry point too (spec §14) — the
    // detail page must show the same reasons whether the visitor arrived
    // here or from /hotels, so carry the same structured context over.
    if (home.value.searchMeta) {
      setContext({ ...home.value.searchMeta, items: home.value.matchSection?.items || [] })
    }
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  ensureLoaded()
  loadHome()
})
watch(isLoggedIn, loadHome)

function goSearch(query) {
  if (detectNearMe(query)) {
    goNearby(query)
    return
  }
  searchQuery.value = query
  onboardingSkipped.value = false
  loadHome()
  // let the visitor keep searching from /hotels too, for full filter/pagination
}

/* ---------------------------------------------------------- "ใช้ตำแหน่งปัจจุบัน" */

const locating = ref(false)
const permissionModal = ref({ visible: false, message: '' })
let lastNearbyQuery = ''

async function goNearby(query = '') {
  lastNearbyQuery = query
  locating.value = true
  try {
    const { latitude, longitude } = await getCurrentPosition()
    setPending({
      query,
      useCurrentLocation: true,
      accommodationType: detectTypeCode(query),
      latitude,
      longitude,
      radiusKm: 10,
      sortBy: query.trim() ? 'relevance' : 'distance',
    })
    permissionModal.value = { visible: false, message: '' }
    router.push('/hotels')
  } catch (e) {
    permissionModal.value = { visible: true, message: GEO_ERROR_MESSAGES[e?.code] || GEO_ERROR_MESSAGES.POSITION_UNAVAILABLE }
  } finally {
    locating.value = false
  }
}

function onModalRetry() {
  goNearby(lastNearbyQuery)
}
function onModalChooseDistrict() {
  permissionModal.value = { visible: false, message: '' }
  router.push('/hotels')
}
function onModalSearchLandmark(name) {
  permissionModal.value = { visible: false, message: '' }
  router.push({ path: '/hotels', query: { q: name } })
}

const hasSearch = computed(() => !!searchQuery.value.trim())
const showOnboarding = computed(() => !!home.value?.onboarding && !onboardingSkipped.value && !hasSearch.value)
const discoverSection = computed(() => home.value?.popularSection || home.value?.featuredSection || null)
const discoverIcon = computed(() => (home.value?.popularSection ? 'fire' : 'compass'))

async function onOnboardingSubmit(payload) {
  try {
    await saveMyPreferences(payload)
  } catch (e) {
    errorMessage.value = e.message || String(e)
    return
  }
  await loadHome()
}

function onOnboardingSkip() {
  onboardingSkipped.value = true
}
</script>

<template>
  <section class="hero-cover px-8 pb-[46px] pt-16">
    <div class="mx-auto max-w-[1000px] text-center">
      <h1 class="mb-2.5 text-[38px] font-extrabold leading-tight text-white [text-shadow:0_2px_20px_rgba(10,8,30,0.4)]">
        ค้นหาที่พักที่ใช่ทั่วพิษณุโลก เข้าใจทุกความต้องการ
      </h1>
      <p class="mb-5 text-[15.5px] text-white/90">ค้นหาโรงแรม รีสอร์ต และโฮมสเตย์ทั่วจังหวัดพิษณุโลก</p>

      <div class="mx-auto flex max-w-[820px] flex-col items-stretch gap-2.5 sm:flex-row">
        <SearchCapsule v-model="searchQuery" placeholder="ลองค้นหา ที่พักเงียบสงบใกล้ธรรมชาติ ราคาไม่เกิน 1,500 บาท" @search="goSearch" />
        <LocateButton :loading="locating" @locate="() => goNearby('')" />
      </div>

      <div class="mt-[22px] flex flex-wrap items-center justify-center gap-3">
        <span class="flex items-center gap-1.5 text-[13px] font-bold text-white/85">
          <svg viewBox="0 0 24 24" class="h-3.5 w-3.5 text-[#FFD9A0]" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M12 3v3M12 18v3M4.2 4.2l2.2 2.2M17.6 17.6l2.2 2.2M3 12h3M18 12h3M4.2 19.8l2.2-2.2M17.6 6.4l2.2-2.2" />
          </svg>
          ลองค้นหาด้วยตัวอย่าง
        </span>
        <button
          v-for="ex in examples"
          :key="ex.label"
          @click="goSearch(ex.label)"
          class="flex items-center gap-2 rounded-xl border border-white/28 bg-white/12 px-4 py-2.5 text-[13px] font-semibold text-white backdrop-blur transition hover:-translate-y-px hover:bg-white/22"
        >
          <svg viewBox="0 0 24 24" class="h-[15px] w-[15px] text-[#C9C4FF]" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" v-html="ex.icon"></svg>
          {{ ex.label }}
        </button>
      </div>
    </div>
  </section>

  <LocationPermissionModal
    :visible="permissionModal.visible"
    :message="permissionModal.message"
    @retry="onModalRetry"
    @choose-district="onModalChooseDistrict"
    @search-landmark="onModalSearchLandmark"
    @close="permissionModal = { visible: false, message: '' }"
  />

  <div v-if="loading" class="mx-auto max-w-[1320px] px-8 py-16 text-center text-ink-faint">กำลังโหลด...</div>
  <p v-else-if="errorMessage" class="mx-auto max-w-[1320px] px-8 py-6 text-[13.5px] text-red-700">เชื่อมต่อ API ไม่สำเร็จ: {{ errorMessage }}</p>

  <template v-else-if="home">
    <!-- search-match state: replaces the personalized/featured slot while a query is active -->
    <template v-if="hasSearch">
      <HomeSection
        v-if="home.matchSection"
        icon="search"
        :title="home.matchSection.title"
        :subtitle="home.matchSection.subtitle"
        :items="home.matchSection.items"
        :amenities="amenities"
        :query="searchQuery"
      />
      <div v-else class="mx-auto max-w-[1320px] px-8 py-10 text-center text-[14px] text-ink-faint">
        ไม่พบที่พักที่ตรงกับ "{{ searchQuery }}" — ลองค้นหาด้วยคำอื่น หรือ
        <RouterLink :to="{ path: '/hotels', query: { q: searchQuery } }" class="font-semibold text-indigo-700 hover:underline">ค้นหาแบบละเอียดที่หน้าค้นหาที่พัก</RouterLink>
      </div>
    </template>

    <!-- onboarding: only for a logged-in member with no personal data yet, and not while actively searching -->
    <OnboardingBox v-if="showOnboarding" :options="home.onboarding" @submit="onOnboardingSubmit" @skip="onOnboardingSkip" />

    <!-- personalized recommendations: logged-in member with enough real data -->
    <HomeSection
      v-if="home.personalSection && !hasSearch"
      icon="sparkle"
      :title="home.personalSection.title"
      :subtitle="home.personalSection.subtitle"
      :items="home.personalSection.items"
      :amenities="amenities"
      section-badge="สำหรับคุณ"
    />

    <section v-if="!hasSearch" class="mx-auto max-w-[1320px] px-8 py-10">
      <div class="mb-5 flex items-center gap-2">
        <svg viewBox="0 0 24 24" class="h-[19px] w-[19px] text-indigo-600" fill="currentColor">
          <rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" />
        </svg>
        <h2 class="text-[19.5px] font-extrabold">ค้นหาตามประเภทที่พัก</h2>
      </div>
      <div class="grid grid-cols-1 gap-3.5 sm:grid-cols-3 lg:gap-5">
        <CategoryCard v-for="c in categories" :key="c.code" :label="c.key" :img="c.img" :icon-path="c.icon" :to="`/hotels?type=${c.code}`" />
      </div>
    </section>

    <!-- "ที่พักยอดนิยม" when there's enough real usage data, else "ที่พักน่าสนใจ" -->
    <HomeSection
      v-if="discoverSection"
      :icon="discoverIcon"
      :title="discoverSection.title"
      :subtitle="discoverSection.subtitle"
      :badge="discoverSection.badge"
      :items="discoverSection.items"
      :amenities="amenities"
    />

    <HomeSection
      v-if="home.recentlyViewedSection"
      icon="clock"
      :title="home.recentlyViewedSection.title"
      :subtitle="home.recentlyViewedSection.subtitle"
      :items="home.recentlyViewedSection.items"
      :amenities="amenities"
    />

    <section v-if="!hasSearch" class="mx-auto max-w-[1320px] px-8 py-10">
      <div class="mb-5 flex items-center gap-2">
        <svg viewBox="0 0 24 24" class="h-[19px] w-[19px] text-indigo-600" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 21s-7-7.5-7-12a7 7 0 0 1 14 0c0 4.5-7 12-7 12z" /><circle cx="12" cy="9" r="2.4" />
        </svg>
        <h2 class="text-[19.5px] font-extrabold">พื้นที่ยอดนิยมในพิษณุโลก</h2>
      </div>
      <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <AreaCard v-for="a in areas" :key="a.name" :name="a.name" :img="a.img" to="/hotels" />
      </div>
    </section>
  </template>
</template>
