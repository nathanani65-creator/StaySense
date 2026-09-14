<script setup>
import { computed, onMounted, onBeforeUnmount } from 'vue'
import { PLACE_META } from '../composables/usePlaceMeta'

const props = defineProps({
  popular: { type: Array, default: () => [] },
  all: { type: Array, default: () => [] },
})
const emit = defineEmits(['close'])

// group `all` by category, each group sorted by distance (already sorted globally)
const groups = computed(() => {
  const map = {}
  for (const p of props.all) {
    ;(map[p.category] ||= []).push(p)
  }
  return Object.entries(map)
    .map(([category, items]) => ({ category, items, meta: PLACE_META[category] || PLACE_META._ }))
    .sort((a, b) => a.items[0].distanceKm - b.items[0].distanceKm)
})

function fmt(km) {
  return km < 1 ? `${Math.round(km * 1000)} ม.` : `${km.toFixed(1)} กม.`
}
function onKey(e) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => {
  document.addEventListener('keydown', onKey)
  document.body.style.overflow = 'hidden'
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto bg-black/50 p-4 sm:p-8" @click.self="emit('close')">
      <div class="w-full max-w-[680px] rounded-2xl bg-white shadow-xl">
        <div class="sticky top-0 flex items-center justify-between rounded-t-2xl border-b border-line bg-white px-6 py-4">
          <h2 class="text-[19px] font-bold text-[#24214A]">สถานที่ใกล้เคียง</h2>
          <button @click="emit('close')" class="flex h-9 w-9 items-center justify-center rounded-full text-ink-soft hover:bg-pagebg" aria-label="ปิด">
            <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>
        </div>

        <div class="px-6 py-5">
          <!-- popular first -->
          <section v-if="popular.length" class="mb-6">
            <h3 class="mb-2.5 text-[15px] font-bold text-indigo-700">ที่เที่ยวยอดนิยม</h3>
            <ul class="flex flex-col divide-y divide-line">
              <li v-for="(p, i) in popular" :key="'pop' + i" class="flex items-center justify-between gap-3 py-2.5">
                <span class="flex items-center gap-2.5 text-[15px] text-[#3F3F57]">
                  <span class="text-[17px]">{{ (PLACE_META[p.category] || PLACE_META._).emoji }}</span>{{ p.name }}
                </span>
                <span class="flex-shrink-0 text-[14px] font-semibold text-ink-faint">{{ fmt(p.distanceKm) }}</span>
              </li>
            </ul>
          </section>

          <!-- by category -->
          <section v-for="g in groups" :key="g.category" class="mb-5 last:mb-0">
            <h3 class="mb-2 text-[15px] font-bold text-[#24214A]">
              <span class="mr-1.5">{{ g.meta.emoji }}</span>{{ g.meta.label }}
            </h3>
            <ul class="flex flex-col divide-y divide-line">
              <li v-for="(p, i) in g.items" :key="i" class="flex items-center justify-between gap-3 py-2.5">
                <span class="text-[15px] text-[#3F3F57]">{{ p.name }}</span>
                <span class="flex-shrink-0 text-[14px] font-semibold text-ink-faint">{{ fmt(p.distanceKm) }}</span>
              </li>
            </ul>
          </section>

          <p v-if="!all.length" class="py-6 text-center text-[14px] text-ink-faint">ไม่มีข้อมูลสถานที่ใกล้เคียง</p>
        </div>

        <div class="sticky bottom-0 rounded-b-2xl border-t border-line bg-white px-6 py-3.5">
          <button @click="emit('close')" class="min-h-[44px] w-full rounded-xl bg-indigo-600 text-[15px] font-semibold text-white hover:brightness-105">ปิด</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
