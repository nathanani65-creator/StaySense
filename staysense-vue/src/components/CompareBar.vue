<script setup>
import { useCompare } from '../composables/useCompare'

const { items, count, maxCompare, removeFromCompare, clearCompare } = useCompare()
</script>

<template>
  <div
    v-if="count > 0"
    class="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-white/95 px-4 py-3 shadow-[0_-8px_24px_rgba(20,16,60,0.08)] backdrop-blur-sm sm:px-8"
  >
    <div class="mx-auto flex max-w-[1320px] flex-wrap items-center gap-3">
      <span class="text-[13px] font-bold text-ink-soft">เปรียบเทียบ ({{ count }}/{{ maxCompare }})</span>

      <div class="flex flex-1 flex-wrap items-center gap-2">
        <div v-for="it in items" :key="it.id" class="flex items-center gap-2 rounded-full border border-line bg-pagebg py-1 pl-1 pr-2.5">
          <div class="h-7 w-7 flex-none rounded-full bg-cover bg-center" :style="{ backgroundImage: `url(${it.img})` }" />
          <span class="max-w-[140px] truncate text-[12.5px] font-semibold text-ink">{{ it.name }}</span>
          <button type="button" @click="removeFromCompare(it.id)" class="text-ink-faint hover:text-red-600" :aria-label="`นำ ${it.name} ออกจากรายการเปรียบเทียบ`">
            <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      <div class="flex flex-none items-center gap-2">
        <button type="button" @click="clearCompare" class="rounded-xl border border-line px-3.5 py-2 text-[13px] font-semibold text-ink-faint hover:bg-pagebg">ล้างรายการ</button>
        <RouterLink
          to="/compare"
          class="flex min-h-[40px] items-center rounded-xl bg-indigo-600 px-5 text-[13.5px] font-bold text-white hover:brightness-105"
        >เปรียบเทียบ</RouterLink>
      </div>
    </div>
  </div>
</template>
