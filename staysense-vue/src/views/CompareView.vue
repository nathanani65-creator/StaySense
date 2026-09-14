<script setup>
import { computed } from 'vue'
import { useCompare } from '../composables/useCompare'
import { useReferenceData } from '../composables/useReferenceData'

const { items, removeFromCompare, clearCompare } = useCompare()
const { amenities, amenityLabel, ensureLoaded } = useReferenceData()
ensureLoaded()

// union of amenity codes across the compared items, so the grid shows every
// relevant row even if only one accommodation has it
const amenityRows = computed(() => {
  const codes = new Set()
  items.value.forEach((it) => (it.amenities || []).forEach((c) => codes.add(c)))
  return amenities.value.filter((a) => codes.has(a.key))
})
</script>

<template>
  <div class="mx-auto max-w-[1320px] px-8 py-10">
    <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-[24px] font-extrabold text-ink">เปรียบเทียบที่พัก</h1>
        <p class="mt-1 text-[13.5px] text-ink-soft">เปรียบเทียบได้สูงสุด 3 แห่ง</p>
      </div>
      <button v-if="items.length" type="button" @click="clearCompare" class="rounded-xl border border-line px-4 py-2 text-[13px] font-semibold text-ink-faint hover:bg-pagebg">ล้างรายการทั้งหมด</button>
    </div>

    <div v-if="!items.length" class="rounded-2xl border border-dashed border-line bg-white p-14 text-center">
      <p class="text-[15px] font-semibold text-ink-soft">ยังไม่มีที่พักในรายการเปรียบเทียบ</p>
      <RouterLink to="/hotels" class="mt-4 inline-flex min-h-[44px] items-center rounded-xl bg-indigo-600 px-6 text-[14.5px] font-semibold text-white hover:brightness-105">ค้นหาที่พัก</RouterLink>
    </div>

    <div v-else class="overflow-x-auto">
      <table class="w-full min-w-[640px] border-separate border-spacing-0">
        <thead>
          <tr>
            <th class="w-[160px]"></th>
            <th v-for="it in items" :key="it.id" class="p-3 text-left align-top">
              <div class="relative overflow-hidden rounded-2xl border border-line bg-white shadow-card">
                <button
                  type="button"
                  @click="removeFromCompare(it.id)"
                  class="absolute right-2 top-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-white/92 text-ink-faint shadow hover:text-red-600"
                  :aria-label="`นำ ${it.name} ออก`"
                >
                  <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
                </button>
                <div class="h-[130px] bg-cover bg-center" :style="{ backgroundImage: `url(${it.img})` }" />
                <div class="p-3">
                  <RouterLink :to="`/accommodations/${it.id}`" class="line-clamp-2 text-[14px] font-extrabold text-ink hover:text-indigo-700">{{ it.name }}</RouterLink>
                  <p class="mt-1 text-[12px] text-ink-faint">อำเภอ{{ it.district }}</p>
                </div>
              </div>
            </th>
          </tr>
        </thead>
        <tbody class="text-[13.5px]">
          <tr class="border-b border-line">
            <td class="py-3 font-semibold text-ink-faint">ประเภท</td>
            <td v-for="it in items" :key="it.id" class="px-3 py-3 text-ink">{{ it.type }}</td>
          </tr>
          <tr class="border-b border-line">
            <td class="py-3 font-semibold text-ink-faint">ราคาเริ่มต้น</td>
            <td v-for="it in items" :key="it.id" class="px-3 py-3 font-extrabold text-indigo-700">฿{{ it.price.toLocaleString() }} / คืน</td>
          </tr>
          <tr class="border-b border-line">
            <td class="py-3 font-semibold text-ink-faint">คะแนนรีวิว</td>
            <td v-for="it in items" :key="it.id" class="px-3 py-3 text-ink">
              <span v-if="it.reviews > 0">{{ it.rating.toFixed(1) }} ({{ it.reviews }} รีวิว)</span>
              <span v-else class="text-ink-faint">ยังไม่มีรีวิว</span>
            </td>
          </tr>
          <tr v-for="a in amenityRows" :key="a.key" class="border-b border-line last:border-0">
            <td class="py-2.5 text-ink-faint">{{ amenityLabel(a.key) }}</td>
            <td v-for="it in items" :key="it.id" class="px-3 py-2.5">
              <svg v-if="(it.amenities || []).includes(a.key)" viewBox="0 0 24 24" class="h-4 w-4 text-emerald-600" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
              <span v-else class="text-ink-faint/50">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
