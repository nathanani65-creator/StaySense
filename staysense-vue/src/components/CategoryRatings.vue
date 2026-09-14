<script setup>
import { computed } from 'vue'

const props = defineProps({
  ratings: { type: Object, default: () => ({}) },
})

const CATEGORY_LABELS = {
  cleanliness: 'ความสะอาด',
  location: 'ทำเล',
  service: 'การบริการ',
  value: 'ความคุ้มค่า',
}

// Only render categories that have a real (> 0) average — matches the
// "no fabricated numbers" rule the backend schema comments call out.
const bars = computed(() =>
  Object.entries(CATEGORY_LABELS)
    .map(([key, label]) => ({ key, label, value: Number(props.ratings?.[key]) || 0 }))
    .filter((c) => c.value > 0),
)
</script>

<template>
  <div v-if="bars.length" class="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
    <div v-for="c in bars" :key="c.key" class="flex items-center gap-3">
      <span class="w-20 flex-shrink-0 text-[14px] font-semibold text-ink-soft">{{ c.label }}</span>
      <div class="h-2 flex-1 overflow-hidden rounded-full bg-pagebg">
        <div class="h-full rounded-full bg-indigo-500" :style="{ width: `${(c.value / 5) * 100}%` }"></div>
      </div>
      <span class="w-8 flex-shrink-0 text-right text-[14px] font-bold text-ink">{{ c.value.toFixed(1) }}</span>
    </div>
  </div>
</template>
