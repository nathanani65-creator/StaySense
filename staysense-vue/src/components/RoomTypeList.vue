<script setup>
import { ref, computed, onMounted } from 'vue'
import { roomTypePresentation } from '../composables/useReferenceData'
import { fetchRoomTypeImages, fetchImageCategories } from '../api/images'
import ImageGalleryModal from './ImageGalleryModal.vue'

const props = defineProps({
  roomTypes: { type: Array, default: () => [] },
  typeCode: { type: String, default: 'hotel' },
  contactHref: { type: String, default: null },
  // shown instead of a blank box when a room type has no photos of its own
  // (common for sheet-imported data that only ever had property-wide photos)
  fallbackImage: { type: String, default: null },
})

const p = computed(() => roomTypePresentation(props.typeCode))
const cheapest = computed(() => {
  const v = props.roomTypes.map((r) => r.price).filter((n) => typeof n === 'number')
  return v.length ? Math.min(...v) : null
})

/* ------- per-card image carousel + fullscreen gallery ------- */
// each room type's own gallery — strictly keyed by room_type_id, never
// mixed with another room type's images or the accommodation-wide gallery
const idx = ref({}) // rt.id -> current image index
const gallery = ref({ open: false, images: [], roomTypeName: '', loading: false, startIndex: 0 })
const categoryLabels = ref({})

onMounted(async () => {
  try {
    const cats = await fetchImageCategories()
    categoryLabels.value = Object.fromEntries(cats.roomType.map((c) => [c.key, c.label]))
  } catch {
    categoryLabels.value = {}
  }
})

function imagesOf(rt) {
  return rt.images?.length ? rt.images.map((img) => img.url) : []
}
function displayImage(rt) {
  const imgs = imagesOf(rt)
  return imgs.length ? imgs[cur(rt)] : props.fallbackImage
}
function cur(rt) {
  return idx.value[rt.id] || 0
}
function step(rt, d) {
  const imgs = imagesOf(rt)
  if (imgs.length < 2) return
  idx.value = { ...idx.value, [rt.id]: (cur(rt) + d + imgs.length) % imgs.length }
}

async function openGallery(rt) {
  if (!imagesOf(rt).length) return
  gallery.value = { open: true, images: [], roomTypeName: rt.name, loading: true, startIndex: cur(rt) }
  try {
    // the card's inline carousel already shows the cheap, published-only
    // embedded list — reload via room_type_id specifically for the modal's
    // richer per-image metadata (category/alt/source)
    const rich = await fetchRoomTypeImages(rt.id)
    gallery.value.images = rich.map((i) => ({
      url: i.url, thumbnailUrl: i.thumbnailUrl, category: i.category,
      caption: i.caption, altText: i.altText, sourceName: i.sourceName, sourceUrl: i.sourceUrl,
    }))
  } catch {
    gallery.value.images = imagesOf(rt).map((url) => ({ url }))
  } finally {
    gallery.value.loading = false
  }
}
function closeGallery() {
  gallery.value.open = false
}

/* ---------------- display helpers ---------------- */
const VIEW_LABEL = {
  garden: 'วิวสวน', river: 'วิวแม่น้ำ', city: 'วิวเมือง',
  mountain: 'วิวภูเขา', pool: 'วิวสระว่ายน้ำ', none: 'ไม่มีวิวพิเศษ',
}

// key facts line: size · occupancy · bed · bathroom
function keyFacts(rt) {
  const out = []
  if (rt.roomSizeSqm) out.push({ icon: 'ruler', text: `${rt.roomSizeSqm} ตร.ม.` })
  if (p.value.fields.includes('houseCapacity') && rt.maxOccupancy) {
    out.push({ icon: 'users', text: `พักได้ทั้งหลัง ${rt.maxOccupancy} คน` })
  } else if (rt.maxOccupancy) {
    out.push({ icon: 'users', text: `พักได้สูงสุด ${rt.maxOccupancy} คน` })
  }
  if (rt.bedType) out.push({ icon: 'bed', text: rt.bedType })
  if (rt.bedrooms) out.push({ icon: 'door', text: `${rt.bedrooms} ห้องนอน` })
  if (rt.bathrooms) out.push({ icon: 'bath', text: `${rt.bathrooms} ห้องน้ำ` })
  else if (rt.roomAmenities?.includes('private_bath')) out.push({ icon: 'bath', text: 'ห้องน้ำส่วนตัว' })
  return out
}

const ROOM_AMEN = {
  aircon: ['เครื่องปรับอากาศ', 'M3 8h18M3 8v8a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1V8M7 12h.01M11 12h.01M8 17v2M12 17v3M16 17v2'],
  wifi: ['Wi-Fi ฟรี', 'M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0M12 19.5h.01'],
  tv: ['โทรทัศน์', 'M3 5h18v12H3zM8 21h8M12 17v4'],
  fridge: ['ตู้เย็น', 'M6 3h12v18H6zM6 10h12M9 6v2M9 13v3'],
  water_heater: ['เครื่องทำน้ำอุ่น', 'M12 3s5 5.5 5 9a5 5 0 0 1-10 0c0-3.5 5-9 5-9z'],
  private_bath: ['ห้องน้ำส่วนตัว', 'M4 12h16v3a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5zM7 12V6a2 2 0 0 1 4 0M12 20l-1 2M13 20l1 2'],
  desk: ['โต๊ะทำงาน', 'M3 7h18M4 7v13M20 7v13M4 13h16M8 20v-3'],
  balcony: ['ระเบียง', 'M4 21V10h16v11M4 14h16M9 14v7M15 14v7M12 3v7'],
  non_smoking: ['ห้องปลอดบุหรี่', 'M2 13h14v3H2zM18 13h4v3h-4zM18 9V7a2 2 0 0 0-2-2M3 4l17 17'],
}

const FACT_ICONS = {
  ruler: 'm3 16 5-5 3 3 5-5 5 5M3 20h18',
  users: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
  bed: 'M2 4v16M2 8h18a2 2 0 0 1 2 2v10M2 17h20M6 8v9',
  door: 'M14 22V4a1 1 0 0 0-1.2-1L6 4.5A1 1 0 0 0 5 5.5V22M14 12h.01M3 22h18',
  bath: 'M4 12h16v3a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5zM7 12V6a2 2 0 0 1 4 0',
}

// extra info lines shown under the amenities (only when present)
function extraInfo(rt) {
  const out = []
  if (rt.extraBedAvailable) {
    const n = rt.extraBedMax ? `เพิ่มได้ ${rt.extraBedMax} เตียง` : 'เสริมเตียงได้'
    const price = rt.extraBedPrice != null ? ` · ฿${rt.extraBedPrice.toLocaleString()}/คน/คืน` : ''
    out.push(`เตียงเสริม: ${n}${price}`)
  }
  if (rt.childrenAllowed != null) out.push(rt.childrenAllowed ? 'เด็กเข้าพักได้' : 'ไม่รับเด็กเข้าพัก')
  if (rt.smokingAllowed != null) out.push(rt.smokingAllowed ? 'สูบบุหรี่ได้' : 'ห้ามสูบบุหรี่ในห้อง')
  if (rt.petsAllowed != null && rt.petsAllowed) out.push('สัตว์เลี้ยงเข้าพักได้')
  if (rt.unitsAvailable) out.push(`มีห้องประเภทนี้ ${rt.unitsAvailable} ${p.value.unitWord}`)
  return out
}
</script>

<template>
  <div v-if="roomTypes.length">
    <h2 class="text-[22px] font-bold text-ink sm:text-[24px]">{{ p.sectionTitle }}</h2>
    <p class="mb-5 mt-1.5 text-[15px] leading-[1.6] text-ink-soft">{{ p.sectionHint }}</p>

    <div class="flex flex-col gap-5">
      <article
        v-for="rt in roomTypes"
        :key="rt.id"
        class="overflow-hidden rounded-2xl border border-[#E4E1FF] bg-white"
        style="box-shadow: 0 6px 20px rgba(79, 70, 229, 0.07)"
      >
        <div class="flex flex-col sm:flex-row">
          <!-- ---------- image (35%) ---------- -->
          <div class="relative shrink-0 sm:basis-[35%]">
            <button
              type="button"
              class="block h-[210px] w-full bg-cover bg-center sm:h-full sm:min-h-[240px]"
              :style="{ backgroundImage: displayImage(rt) ? `url(${displayImage(rt)})` : 'none', backgroundColor: '#EEECFF' }"
              @click="openGallery(rt)"
              :aria-label="imagesOf(rt).length ? 'ดูรูปห้อง' : undefined"
            />
            <span
              v-if="!imagesOf(rt).length && fallbackImage"
              class="absolute bottom-2.5 left-2.5 rounded-lg bg-black/65 px-2.5 py-1 text-[11px] font-bold text-white backdrop-blur-sm"
            >ภาพตัวอย่างที่พัก</span>
            <template v-if="imagesOf(rt).length > 1">
              <button type="button" class="absolute left-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/85 text-ink shadow hover:bg-white" @click.stop="step(rt, -1)" aria-label="ก่อนหน้า">
                <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="m15 18-6-6 6-6" /></svg>
              </button>
              <button type="button" class="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/85 text-ink shadow hover:bg-white" @click.stop="step(rt, 1)" aria-label="ถัดไป">
                <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="m9 18 6-6-6-6" /></svg>
              </button>
            </template>
            <button
              v-if="imagesOf(rt).length"
              type="button"
              class="absolute bottom-2.5 right-2.5 rounded-lg bg-black/65 px-2.5 py-1 text-[12px] font-bold text-white backdrop-blur-sm"
              @click.stop="openGallery(rt)"
            >{{ imagesOf(rt).length === 1 ? '1 รูป' : `ดูภาพทั้งหมด ${imagesOf(rt).length} รูป` }}</button>
          </div>

          <!-- ---------- details (45%) ---------- -->
          <div class="min-w-0 flex-1 p-5 sm:basis-[45%]">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="text-[22px] font-bold leading-tight text-[#171733]">{{ rt.name }}</h3>
              <span
                v-if="cheapest != null && rt.price === cheapest && roomTypes.length > 1"
                class="rounded-full bg-emerald-50 px-2 py-0.5 text-[11.5px] font-bold text-emerald-700"
              >ราคาประหยัดสุด</span>
            </div>
            <p v-if="rt.description" class="mt-1.5 text-[14px] leading-[1.6] text-ink-soft">{{ rt.description }}</p>

            <!-- key facts -->
            <div class="mt-3 flex flex-wrap gap-x-5 gap-y-2">
              <span v-for="(f, i) in keyFacts(rt)" :key="i" class="inline-flex items-center gap-1.5 text-[14px] font-medium text-[#3F3F57]">
                <svg viewBox="0 0 24 24" class="h-[17px] w-[17px] flex-shrink-0 text-indigo-500" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path :d="FACT_ICONS[f.icon]" /></svg>
                {{ f.text }}
              </span>
            </div>

            <!-- view -->
            <div v-if="rt.view" class="mt-2.5 inline-flex items-center gap-1.5 rounded-lg bg-[#F5F3FF] px-2.5 py-1 text-[13.5px] font-semibold text-indigo-700">
              <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" /><circle cx="12" cy="12" r="3" /></svg>
              {{ VIEW_LABEL[rt.view] || rt.view }}
            </div>

            <!-- in-room amenities -->
            <div v-if="rt.roomAmenities?.length" class="mt-3.5 grid grid-cols-2 gap-x-4 gap-y-2 md:grid-cols-3">
              <span v-for="a in rt.roomAmenities" :key="a" class="inline-flex items-center gap-1.5 text-[13.5px] text-[#37335C]">
                <svg viewBox="0 0 24 24" class="h-[16px] w-[16px] flex-shrink-0 text-indigo-500" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path :d="(ROOM_AMEN[a] || ['', ''])[1]" /></svg>
                {{ (ROOM_AMEN[a] || [a])[0] }}
              </span>
            </div>

            <!-- extra info -->
            <ul v-if="extraInfo(rt).length" class="mt-3.5 flex flex-col gap-1 border-t border-line pt-3 text-[13px] text-ink-faint">
              <li v-for="(line, i) in extraInfo(rt)" :key="i">{{ line }}</li>
            </ul>
          </div>

          <!-- ---------- price (20%) ---------- -->
          <div class="flex shrink-0 flex-row items-center justify-between gap-2 border-t border-line p-5 sm:basis-[20%] sm:flex-col sm:items-end sm:justify-center sm:border-l sm:border-t-0 sm:text-right">
            <div>
              <div class="text-[27px] font-bold leading-none text-indigo-600">฿{{ rt.price.toLocaleString() }}</div>
              <div class="mt-1 text-[14px] text-ink-faint">ต่อคืน</div>
            </div>
            <div class="sm:mt-3">
              <span
                class="inline-block rounded-md px-2 py-1 text-[12px] font-semibold"
                :class="rt.breakfastIncluded ? 'bg-emerald-50 text-emerald-700' : 'bg-pagebg text-ink-faint'"
              >{{ rt.breakfastIncluded ? 'รวมอาหารเช้า' : 'ไม่รวมอาหารเช้า' }}</span>
              <p v-if="rt.extraBedAvailable && rt.extraBedPrice != null" class="mt-1.5 text-[12px] leading-snug text-ink-faint">
                เตียงเสริม +฿{{ rt.extraBedPrice.toLocaleString() }}/คน/คืน
              </p>
            </div>
          </div>
        </div>
      </article>
    </div>

    <ImageGalleryModal
      :visible="gallery.open"
      :title="`ภาพทั้งหมดของ ${gallery.roomTypeName}`"
      :images="gallery.images"
      :initial-index="gallery.startIndex"
      :category-labels="categoryLabels"
      @close="closeGallery"
    />
  </div>
</template>
