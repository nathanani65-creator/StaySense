<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  total: { type: Number, required: true },
})
const emit = defineEmits(['update:page'])

const pages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const windowed = computed(() => {
  const windowSize = 5
  let start = Math.max(1, props.page - 2)
  let end = Math.min(pages.value, start + windowSize - 1)
  start = Math.max(1, end - windowSize + 1)
  const arr = []
  for (let p = start; p <= end; p++) arr.push(p)
  return { start, end, arr }
})

function go(p) {
  if (p >= 1 && p <= pages.value) emit('update:page', p)
}
</script>

<template>
  <div class="mt-[26px] flex items-center justify-center gap-1.5">
    <button
      :disabled="page <= 1"
      @click="go(page - 1)"
      class="flex h-9 min-w-9 items-center justify-center rounded-[9px] border-[1.5px] border-line bg-white text-[13.5px] font-bold text-ink-soft disabled:opacity-40"
    >
      <svg viewBox="0 0 24 24" class="h-[15px] w-[15px]" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="m15 18-6-6 6-6" /></svg>
    </button>

    <button v-if="windowed.start > 1" @click="go(1)" class="flex h-9 min-w-9 items-center justify-center rounded-[9px] border-[1.5px] border-line bg-white text-[13.5px] font-bold text-ink-soft">1</button>
    <span v-if="windowed.start > 2" class="px-0.5 text-ink-faint">…</span>

    <button
      v-for="p in windowed.arr"
      :key="p"
      @click="go(p)"
      class="flex h-9 min-w-9 items-center justify-center rounded-[9px] border-[1.5px] text-[13.5px] font-bold"
      :class="p === page ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-line bg-white text-ink-soft'"
    >
      {{ p }}
    </button>

    <span v-if="windowed.end < pages - 1" class="px-0.5 text-ink-faint">…</span>
    <button v-if="windowed.end < pages" @click="go(pages)" class="flex h-9 min-w-9 items-center justify-center rounded-[9px] border-[1.5px] border-line bg-white text-[13.5px] font-bold text-ink-soft">{{ pages }}</button>

    <button
      :disabled="page >= pages"
      @click="go(page + 1)"
      class="flex h-9 min-w-9 items-center justify-center rounded-[9px] border-[1.5px] border-line bg-white text-[13.5px] font-bold text-ink-soft disabled:opacity-40"
    >
      <svg viewBox="0 0 24 24" class="h-[15px] w-[15px]" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="m9 18 6-6-6-6" /></svg>
    </button>
  </div>
</template>
