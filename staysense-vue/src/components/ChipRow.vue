<script setup>
import { computed } from 'vue'

const props = defineProps({
  filters: { type: Object, required: true },
  query: { type: String, default: '' },
  amenities: { type: Array, default: () => [] }, // [{ key, label }]
})
const emit = defineEmits(['update:filters', 'update:query', 'clear-all'])

const TIER_LABELS = {
  '0-1000': 'ไม่เกิน 1,000 บาท',
  '1001-2000': '1,001–2,000 บาท',
  '2001-3000': '2,001–3,000 บาท',
  '3000+': 'มากกว่า 3,000 บาท',
}
const DISTANCE_LABELS = { nearest: 'ใกล้ที่สุดก่อน', '5': 'ไม่เกิน 5 กม.', '10': 'ไม่เกิน 10 กม.' }

const chips = computed(() => {
  const list = []
  props.filters.districts.forEach((d) =>
    list.push({ label: d, remove: () => removeDistrict(d) })
  )
  if (props.filters.tier) list.push({ label: TIER_LABELS[props.filters.tier], remove: () => update({ tier: null }) })
  if (props.filters.ratingMin) list.push({ label: `${props.filters.ratingMin.toFixed(1)} ดาวขึ้นไป`, remove: () => update({ ratingMin: null }) })
  props.filters.amenities.forEach((a) => {
    const found = props.amenities.find((x) => x.key === a)
    list.push({ label: found ? found.label : a, remove: () => removeAmenity(a) })
  })
  if (props.filters.distance) list.push({ label: DISTANCE_LABELS[props.filters.distance], remove: () => update({ distance: null }) })
  if (props.filters.priceMin > 200 || props.filters.priceMax < 5000) {
    list.push({
      label: `฿${props.filters.priceMin} – ${props.filters.priceMax >= 5000 ? '5,000+' : props.filters.priceMax}`,
      remove: () => update({ priceMin: 200, priceMax: 5000 }),
    })
  }
  if (props.query) list.push({ label: `ค้นหา: "${props.query}"`, remove: () => emit('update:query', '') })
  return list
})

function update(patch) {
  emit('update:filters', { ...props.filters, ...patch })
}
function removeDistrict(d) {
  const next = new Set(props.filters.districts)
  next.delete(d)
  update({ districts: next })
}
function removeAmenity(a) {
  const next = new Set(props.filters.amenities)
  next.delete(a)
  update({ amenities: next })
}
</script>

<template>
  <div v-if="chips.length" class="mb-4 flex flex-wrap gap-2">
    <span v-for="(c, i) in chips" :key="i" class="flex items-center gap-1.5 rounded-full border border-[#DEDBF9] bg-indigo-50 py-1.5 pl-3.5 pr-1.5 text-[12.5px] font-bold text-indigo-700">
      {{ c.label }}
      <button @click="c.remove" class="flex p-0.5 text-indigo-500">
        <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
      </button>
    </span>
    <button @click="emit('clear-all')" class="rounded-full border border-line bg-white px-3.5 py-1.5 text-[12.5px] font-bold text-ink-soft">ล้างทั้งหมด</button>
  </div>
</template>
