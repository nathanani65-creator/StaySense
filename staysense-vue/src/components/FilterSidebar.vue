<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Object, required: true },
  districts: { type: Array, default: () => [] }, // [{ key, ... }]
  amenities: { type: Array, default: () => [] }, // [{ key, label }]
})
const emit = defineEmits(['update:modelValue', 'clear'])

const filters = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

function toggleDistrict(key) {
  const next = new Set(filters.value.districts)
  next.has(key) ? next.delete(key) : next.add(key)
  filters.value = { ...filters.value, districts: next }
}

function toggleAmenity(key) {
  const next = new Set(filters.value.amenities)
  next.has(key) ? next.delete(key) : next.add(key)
  filters.value = { ...filters.value, amenities: next }
}

function setTier(tier) {
  filters.value = { ...filters.value, tier: filters.value.tier === tier ? null : tier }
}
function setRating(rating) {
  filters.value = { ...filters.value, ratingMin: filters.value.ratingMin === rating ? null : rating }
}
function setDistance(distance) {
  filters.value = { ...filters.value, distance: filters.value.distance === distance ? null : distance }
}
function setPriceMin(e) {
  let v = parseInt(e.target.value) || 200
  filters.value = { ...filters.value, priceMin: Math.min(v, filters.value.priceMax) }
}
function setPriceMax(e) {
  let v = parseInt(e.target.value) || 5000
  filters.value = { ...filters.value, priceMax: Math.max(v, filters.value.priceMin) }
}

const TIERS = [
  { key: '0-1000', label: 'ไม่เกิน 1,000 บาท' },
  { key: '1001-2000', label: '1,001–2,000 บาท' },
  { key: '2001-3000', label: '2,001–3,000 บาท' },
  { key: '3000+', label: 'มากกว่า 3,000 บาท' },
]
const RATINGS = [4.5, 4.0, 3.5]
const DISTANCES = [
  { key: 'nearest', label: 'ใกล้ที่สุดก่อน' },
  { key: '5', label: 'ไม่เกิน 5 กม.' },
  { key: '10', label: 'ไม่เกิน 10 กม.' },
]

const sliderLo = computed(() => ((filters.value.priceMin - 200) / (5000 - 200)) * 100)
const sliderHi = computed(() => ((filters.value.priceMax - 200) / (5000 - 200)) * 100)
</script>

<template>
  <aside class="sticky top-[86px] rounded-2xl border border-line bg-white p-5 shadow-card">
    <div class="mb-3.5 flex items-center justify-between">
      <h3 class="text-[15.5px] font-extrabold">ตัวกรอง</h3>
      <button @click="emit('clear')" class="flex items-center gap-1 text-xs font-bold text-indigo-600 hover:underline">
        <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5" />
        </svg>
        ล้างตัวกรอง
      </button>
    </div>

    <!-- districts -->
    <div class="border-t border-line py-3.5 first:border-t-0 first:pt-0">
      <div class="mb-3 text-[13.5px] font-bold">อำเภอ (9 อำเภอ)</div>
      <div class="flex flex-col gap-2">
        <label v-for="d in districts" :key="d.key" class="flex cursor-pointer items-center gap-2 text-[13.5px] text-ink-soft hover:text-ink">
          <input type="checkbox" class="h-[15px] w-[15px] accent-indigo-600" :checked="filters.districts.has(d.key)" @change="toggleDistrict(d.key)" />
          {{ d.key }}
        </label>
      </div>
    </div>

    <!-- price range -->
    <div class="border-t border-line py-3.5">
      <div class="mb-3 text-[13.5px] font-bold">ราคา (บาท/คืน)</div>
      <div class="relative mb-2 h-6">
        <div class="absolute left-0 right-0 top-2 h-1 rounded-full bg-line"></div>
        <div class="absolute top-2 h-1 rounded-full bg-indigo-600" :style="{ left: sliderLo + '%', width: Math.max(0, sliderHi - sliderLo) + '%' }"></div>
        <input type="range" class="price-range absolute top-2 h-1 w-full" min="200" max="5000" step="50" :value="filters.priceMin" @input="setPriceMin" />
        <input type="range" class="price-range absolute top-2 h-1 w-full" min="200" max="5000" step="50" :value="filters.priceMax" @input="setPriceMax" />
      </div>
      <div class="flex items-center gap-2 text-[13px] text-ink-faint">
        <input type="number" class="w-full rounded-lg border-[1.5px] border-line px-2 py-2 text-center text-ink" :value="filters.priceMin" @change="setPriceMin" />
        <span>–</span>
        <input type="text" class="w-full rounded-lg border-[1.5px] border-line px-2 py-2 text-center text-ink" :value="filters.priceMax >= 5000 ? '5000+' : filters.priceMax" @change="setPriceMax" />
      </div>
    </div>

    <!-- tier -->
    <div class="border-t border-line py-3.5">
      <div class="mb-3 text-[13.5px] font-bold">ระดับราคา</div>
      <div class="flex flex-col gap-2">
        <label v-for="t in TIERS" :key="t.key" class="flex cursor-pointer items-center gap-2 text-[13.5px] text-ink-soft hover:text-ink">
          <input type="radio" class="h-[15px] w-[15px] accent-indigo-600" :checked="filters.tier === t.key" @change="setTier(t.key)" />
          {{ t.label }}
        </label>
      </div>
    </div>

    <!-- rating -->
    <div class="border-t border-line py-3.5">
      <div class="mb-3 text-[13.5px] font-bold">คะแนนผู้เข้าพัก</div>
      <div class="flex flex-col gap-2">
        <label v-for="r in RATINGS" :key="r" class="flex cursor-pointer items-center gap-2 text-[13.5px] text-ink-soft hover:text-ink">
          <input type="radio" class="h-[15px] w-[15px] accent-indigo-600" :checked="filters.ratingMin === r" @change="setRating(r)" />
          <svg viewBox="0 0 24 24" class="h-3.5 w-3.5 text-gold" fill="currentColor"><path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.8 1.5 6.9L12 17.9l-6.1 3.4 1.5-6.9-5.2-4.8 6.9-.7z" /></svg>
          {{ r.toFixed(1) }} ขึ้นไป
        </label>
      </div>
    </div>

    <!-- amenities -->
    <div class="border-t border-line py-3.5">
      <div class="mb-3 text-[13.5px] font-bold">สิ่งอำนวยความสะดวก</div>
      <div class="flex flex-col gap-2">
        <label v-for="a in amenities" :key="a.key" class="flex cursor-pointer items-center gap-2 text-[13.5px] text-ink-soft hover:text-ink">
          <input type="checkbox" class="h-[15px] w-[15px] accent-indigo-600" :checked="filters.amenities.has(a.key)" @change="toggleAmenity(a.key)" />
          {{ a.label }}
        </label>
      </div>
    </div>

    <!-- distance -->
    <div class="border-t border-line py-3.5">
      <div class="mb-3 text-[13.5px] font-bold">ระยะทาง</div>
      <div class="flex flex-col gap-2">
        <label v-for="d in DISTANCES" :key="d.key" class="flex cursor-pointer items-center gap-2 text-[13.5px] text-ink-soft hover:text-ink">
          <input type="radio" class="h-[15px] w-[15px] accent-indigo-600" :checked="filters.distance === d.key" @change="setDistance(d.key)" />
          {{ d.label }}
        </label>
      </div>
    </div>
  </aside>
</template>
