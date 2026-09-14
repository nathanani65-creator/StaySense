<script setup>
import { computed, ref } from 'vue'
import { formatDistance } from '../utils/geolocation'
import { logEvent } from '../api/events'

const props = defineProps({
  hotel: { type: Object, required: true },
  matched: { type: Boolean, default: false },
  amenities: { type: Array, default: () => [] }, // [{ key, label }]
  query: { type: String, default: '' },
  // homepage recommendation-section extras — all optional, all default to
  // "plain card" behaviour so HotelsView's existing usage is unaffected.
  sectionBadge: { type: String, default: null },  // "สำหรับคุณ" | "คัดเลือกโดย StaySense" | ...
  showCompare: { type: Boolean, default: true },
  inCompare: { type: Boolean, default: false },
  compareDisabled: { type: Boolean, default: false },
})
const emit = defineEmits(['toggle-fav', 'toggle-compare'])

function amenityLabel(key) {
  return props.amenities.find((a) => a.key === key)?.label || key
}

const detailLink = computed(() => ({
  path: `/accommodations/${props.hotel.id}`,
  query: props.query?.trim() ? { q: props.query.trim() } : {},
}))

// hotel.matchLevel/reason (real, per-viewer, computed server-side by /api/home)
// take priority over the generic `matched` boolean HotelsView passes.
const matchBadgeText = computed(() => props.hotel.matchLevel || (props.matched ? 'ตรงกับที่คุณค้นหา' : null))
// structured, itemized reasons (app/match_reasons.py) take priority — each
// one is backed by real data (a real POI+distance, a real facility, a real
// price fit). Falls back to the older flat string only where a card doesn't
// come from a search at all (e.g. homepage "สำหรับคุณ" sections).
const reasonText = computed(() => props.hotel.matchReason || props.hotel.reason)
const REASON_PREVIEW_COUNT = 3
const reasonsExpanded = ref(false)
// the "และวัดใกล้เคียงอีก X แห่ง" overflow line (spec §3) is informational,
// not another competing reason — always shown alongside the capped list
// rather than hidden behind "ดูเหตุผลทั้งหมด".
const overflowReason = computed(() => (props.hotel.matchReasons || []).find((r) => r.type === 'poi_match_more'))
const coreReasons = computed(() => (props.hotel.matchReasons || []).filter((r) => r.type !== 'poi_match_more'))
const visibleReasons = computed(() => {
  const shown = reasonsExpanded.value ? coreReasons.value : coreReasons.value.slice(0, REASON_PREVIEW_COUNT)
  return overflowReason.value ? [...shown, overflowReason.value] : shown
})
const hasMoreReasons = computed(() => coreReasons.value.length > REASON_PREVIEW_COUNT)
// real distance from the visitor's own geolocation coords — only present
// when this card came back from /api/search/nearby ("ใช้ตำแหน่งปัจจุบัน")
const distanceFromUserText = computed(() =>
  props.hotel.distanceFromUserKm != null ? formatDistance(props.hotel.distanceFromUserKm) : null
)
</script>

<template>
  <div class="relative grid grid-cols-1 overflow-hidden rounded-2xl border border-line bg-white shadow-card transition-all hover:-translate-y-0.5 hover:shadow-lg sm:grid-cols-[270px_1fr]">
    <span
      v-if="hotel.rank"
      class="absolute left-3 top-3 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-[#211D3A] text-[12.5px] font-extrabold text-white shadow"
    >{{ hotel.rank }}</span>

    <RouterLink :to="detailLink" class="relative min-h-[180px] bg-cover bg-center sm:min-h-[210px]" :style="{ backgroundImage: `url(${hotel.img})` }">
      <button @click.stop.prevent="emit('toggle-fav', hotel.id)" class="absolute right-3 top-3 flex h-[34px] w-[34px] items-center justify-center rounded-full bg-white/92 shadow">
        <svg viewBox="0 0 24 24" class="h-[17px] w-[17px]" :class="hotel.fav ? 'fill-red-500 text-red-500' : 'text-[#C7C3DE]'" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20.8 8.6c0 4.4-8.8 10-8.8 10s-8.8-5.6-8.8-10a4.8 4.8 0 0 1 8.8-2.7 4.8 4.8 0 0 1 8.8 2.7z" />
        </svg>
      </button>
      <span class="absolute bottom-3 left-3 rounded-full bg-[#211D3A]/72 px-2.5 py-1.5 text-[11px] font-bold text-white backdrop-blur-sm">{{ hotel.district }}</span>
    </RouterLink>

    <div class="flex flex-col gap-2.5 p-5">
      <div class="flex items-start justify-between gap-2.5">
        <RouterLink :to="detailLink">
          <h3 class="text-[16.5px] font-extrabold hover:text-indigo-700">{{ hotel.name }}</h3>
          <div class="mt-0.5 flex items-center gap-1.5 text-xs text-ink-faint">
            <svg viewBox="0 0 24 24" class="h-3 w-3 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 21s-7-7.5-7-12a7 7 0 0 1 14 0c0 4.5-7 12-7 12z" /><circle cx="12" cy="9" r="2.4" />
            </svg>
            <span>อำเภอ{{ hotel.district }}</span>
          </div>
        </RouterLink>
        <div class="flex-shrink-0 text-right">
          <div class="text-[19px] font-extrabold text-indigo-700">฿{{ hotel.price.toLocaleString() }}</div>
          <div class="text-xs font-semibold text-ink-faint">/ คืน</div>
        </div>
      </div>

      <div v-if="sectionBadge || matchBadgeText" class="flex flex-wrap gap-1.5">
        <span v-if="sectionBadge" class="inline-flex w-fit items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-extrabold text-indigo-700">
          <svg viewBox="0 0 24 24" class="h-[11px] w-[11px]" fill="currentColor"><path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.8 1.5 6.9L12 17.9l-6.1 3.4 1.5-6.9-5.2-4.8 6.9-.7z" /></svg>
          {{ sectionBadge }}
        </span>
        <span v-if="matchBadgeText" class="inline-flex w-fit items-center gap-1.5 rounded-full bg-indigo-600 px-2.5 py-1 text-[11px] font-extrabold text-white">
          <svg viewBox="0 0 24 24" class="h-[11px] w-[11px]" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M12 3v3M12 18v3M4.2 4.2l2.2 2.2M17.6 17.6l2.2 2.2M3 12h3M18 12h3M4.2 19.8l2.2-2.2M17.6 6.4l2.2-2.2" />
          </svg>
          {{ matchBadgeText }}
        </span>
      </div>

      <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] font-bold">
        <template v-if="hotel.reviews > 0">
          <span class="flex items-center gap-1.5">
            <svg viewBox="0 0 24 24" class="h-3.5 w-3.5 text-gold" fill="currentColor"><path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.8 1.5 6.9L12 17.9l-6.1 3.4 1.5-6.9-5.2-4.8 6.9-.7z" /></svg>
            <span>{{ hotel.rating.toFixed(1) }}</span>
            <span class="font-semibold text-ink-faint">({{ hotel.reviews }} รีวิว)</span>
          </span>
        </template>
        <span v-else class="font-semibold text-ink-faint">ยังไม่มีรีวิว</span>
        <span v-if="hotel.statLabel" class="flex items-center gap-1 font-semibold text-ink-faint">
          <svg viewBox="0 0 24 24" class="h-3.5 w-3.5 text-rose-500" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l6-6 4 4 8-8M21 7v6h-6" /></svg>
          {{ hotel.statLabel }}
        </span>
        <span v-if="distanceFromUserText" class="flex items-center gap-1 font-extrabold text-indigo-700">
          <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M22 12h-3M5 12H2" />
          </svg>
          ห่างจากคุณประมาณ {{ distanceFromUserText }}
        </span>
      </div>

      <div class="flex flex-wrap gap-1.5">
        <span v-for="a in hotel.amenities.slice(0, 4)" :key="a" class="rounded-full bg-indigo-50 px-2.5 py-1 text-[11.5px] font-bold text-indigo-700">{{ amenityLabel(a) }}</span>
      </div>

      <div v-if="hotel.landmark && hotel.distanceKm != null" class="flex items-center gap-1.5 text-[12.5px] text-ink-soft">
        <svg viewBox="0 0 24 24" class="h-[13px] w-[13px] text-ink-faint" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m3 16 5-5 3 3 5-5 5 5" /><path d="M3 20h18" />
        </svg>
        <span>ห่างจาก{{ hotel.landmark }} {{ hotel.distanceKm }} กม.</span>
      </div>

      <div v-if="hotel.matchReasons?.length" class="mt-0.5 rounded-[10px] border border-amber-line bg-amber-bg p-2.5">
        <div class="mb-1 flex items-center gap-1.5 text-[11.5px] font-extrabold text-amber-ink">
          <svg viewBox="0 0 24 24" class="h-[14px] w-[14px] flex-shrink-0 text-amber-icon" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 18h6M10 22h4M12 2a6 6 0 0 0-4 10.5c.7.6 1 1.2 1 2.5h6c0-1.3.3-1.9 1-2.5A6 6 0 0 0 12 2z" />
          </svg>
          เหตุผลที่ตรงกับการค้นหา
        </div>
        <ul class="space-y-1">
          <li v-for="(r, i) in visibleReasons" :key="i" class="flex items-start gap-1.5 text-[12.5px] leading-relaxed text-amber-ink">
            <svg viewBox="0 0 24 24" class="mt-[3px] h-3 w-3 flex-shrink-0 text-amber-icon" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
            <span>{{ r.message }}</span>
          </li>
        </ul>
        <button
          v-if="hasMoreReasons"
          type="button"
          @click.stop.prevent="reasonsExpanded = !reasonsExpanded"
          class="mt-1.5 text-[11.5px] font-extrabold text-amber-icon underline underline-offset-2"
        >
          {{ reasonsExpanded ? 'ย่อเหตุผล' : 'ดูเหตุผลทั้งหมด' }}
        </button>
      </div>
      <div v-else-if="reasonText" class="mt-0.5 flex gap-2 rounded-[10px] border border-amber-line bg-amber-bg p-2.5">
        <svg viewBox="0 0 24 24" class="mt-px h-[15px] w-[15px] flex-shrink-0 text-amber-icon" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 18h6M10 22h4M12 2a6 6 0 0 0-4 10.5c.7.6 1 1.2 1 2.5h6c0-1.3.3-1.9 1-2.5A6 6 0 0 0 12 2z" />
        </svg>
        <div class="text-[12.5px] leading-relaxed text-amber-ink"><b class="font-extrabold">เหตุผลที่แนะนำ:</b> {{ reasonText }}</div>
      </div>

      <div class="mt-0.5 flex flex-wrap gap-2">
        <a
          v-if="hotel.googleMapsUrl"
          :href="hotel.googleMapsUrl"
          target="_blank"
          rel="noopener noreferrer"
          @click.stop="logEvent(hotel.id, 'direction_click')"
          class="flex w-fit items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-[12px] font-bold text-ink-soft hover:bg-pagebg"
        >
          <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m3 11 19-9-9 19-2-8-8-2z" />
          </svg>
          เปิดเส้นทาง
        </a>
        <button
          v-if="showCompare"
          type="button"
          @click.stop.prevent="emit('toggle-compare', hotel)"
          :disabled="compareDisabled && !inCompare"
          class="flex w-fit items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[12px] font-bold disabled:cursor-not-allowed disabled:opacity-50"
          :class="inCompare ? 'border-indigo-600 bg-indigo-50 text-indigo-700' : 'border-line text-ink-soft hover:bg-pagebg'"
        >
          <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="7" height="16" rx="1.5" /><rect x="14" y="4" width="7" height="16" rx="1.5" /><path d="M10 12h4" />
          </svg>
          {{ inCompare ? 'เพิ่มเพื่อเปรียบเทียบแล้ว' : 'เพิ่มเพื่อเปรียบเทียบ' }}
        </button>
      </div>
    </div>
  </div>
</template>
