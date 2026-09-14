<script setup>
import { ref, computed } from 'vue'
import { useReferenceData } from '../composables/useReferenceData'

const props = defineProps({
  codes: { type: Array, default: () => [] },
  initialCount: { type: Number, default: 6 },
})

const { amenityLabel } = useReferenceData()

const EMOJI = {
  wifi: '📶', parking: '🅿️', breakfast: '🍳', pool: '🏊', family: '👨‍👩‍👧', pet: '🐾',
  aircon: '❄️', tv: '📺', fridge: '🧊', water_heater: '🚿', restaurant: '🍽️', gym: '🏋️',
  elevator: '🛗', laundry: '🧺', reception24: '🛎️', wheelchair: '♿', elderly: '👵',
}

const expanded = ref(false)
const shown = computed(() =>
  expanded.value ? props.codes : props.codes.slice(0, props.initialCount),
)
const hiddenCount = computed(() => Math.max(0, props.codes.length - props.initialCount))
</script>

<template>
  <div v-if="codes.length">
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      <div
        v-for="code in shown"
        :key="code"
        class="flex items-center gap-2.5 rounded-xl border border-line bg-white px-4 py-3.5 text-[15px] font-medium text-ink"
      >
        <span class="text-[18px] leading-none">{{ EMOJI[code] || '✅' }}</span>
        <span>{{ amenityLabel(code) }}</span>
      </div>
    </div>

    <button
      v-if="hiddenCount > 0"
      @click="expanded = !expanded"
      class="mt-4 inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-line bg-white px-4 text-[15px] font-semibold text-indigo-600 hover:bg-indigo-50"
    >
      {{ expanded ? 'แสดงน้อยลง' : `ดูสิ่งอำนวยความสะดวกทั้งหมด (${codes.length})` }}
      <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path :d="expanded ? 'm18 15-6-6-6 6' : 'm6 9 6 6 6-6'" />
      </svg>
    </button>
  </div>
  <p v-else class="text-[15px] text-ink-soft">ยังไม่มีข้อมูลสิ่งอำนวยความสะดวก</p>
</template>
