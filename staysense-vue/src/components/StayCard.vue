<script setup>
defineProps({
  stay: { type: Object, required: true },
})
const emit = defineEmits(['toggle-fav'])
</script>

<template>
  <RouterLink :to="`/accommodations/${stay.id}`" class="block overflow-hidden rounded-2xl border border-line bg-white shadow-card transition-transform hover:-translate-y-1 hover:shadow-lg">
    <div class="relative h-[190px] bg-cover bg-center" :style="{ backgroundImage: `url(${stay.img})` }">
      <button @click.stop.prevent="emit('toggle-fav', stay.id)" class="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-full bg-white/90 shadow">
        <svg viewBox="0 0 24 24" class="h-4 w-4" :class="stay.fav ? 'fill-red-500 text-red-500' : 'text-[#C7C3DE]'" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20.8 8.6c0 4.4-8.8 10-8.8 10s-8.8-5.6-8.8-10a4.8 4.8 0 0 1 8.8-2.7 4.8 4.8 0 0 1 8.8 2.7z" />
        </svg>
      </button>
    </div>
    <div class="flex flex-col gap-2.5 p-[18px]">
      <div class="flex items-start justify-between gap-2.5">
        <div>
          <h3 class="text-[16px] font-extrabold">{{ stay.name }}</h3>
          <div class="mt-0.5 flex items-center gap-1.5 text-xs text-ink-faint">
            <svg viewBox="0 0 24 24" class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 21s-7-7.5-7-12a7 7 0 0 1 14 0c0 4.5-7 12-7 12z" />
              <circle cx="12" cy="9" r="2.4" />
            </svg>
            <span>อำเภอ{{ stay.district }}</span>
          </div>
        </div>
        <div class="flex-shrink-0 text-right">
          <div class="text-[17px] font-extrabold text-indigo-700">฿{{ stay.price.toLocaleString() }}</div>
          <div class="text-[11.5px] font-semibold text-ink-faint">/ คืน</div>
        </div>
      </div>

      <div class="flex items-center gap-1.5 text-[13px] font-bold">
        <template v-if="stay.reviews > 0">
          <svg viewBox="0 0 24 24" class="h-[13px] w-[13px] text-gold" fill="currentColor">
            <path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.8 1.5 6.9L12 17.9l-6.1 3.4 1.5-6.9-5.2-4.8 6.9-.7z" />
          </svg>
          <span>{{ stay.rating.toFixed(1) }}</span>
          <span class="font-semibold text-ink-faint">({{ stay.reviews }} รีวิว)</span>
        </template>
        <span v-else class="font-semibold text-ink-faint">ยังไม่มีรีวิว</span>
      </div>

      <div class="flex flex-wrap gap-1.5">
        <span v-for="tag in stay.tags" :key="tag" class="rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-bold text-indigo-700">{{ tag }}</span>
      </div>

      <div v-if="stay.reason" class="flex gap-2 rounded-[10px] border border-amber-line bg-amber-bg p-2.5">
        <svg viewBox="0 0 24 24" class="mt-px h-[14px] w-[14px] flex-shrink-0 text-amber-icon" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 18h6M10 22h4M12 2a6 6 0 0 0-4 10.5c.7.6 1 1.2 1 2.5h6c0-1.3.3-1.9 1-2.5A6 6 0 0 0 12 2z" />
        </svg>
        <div class="text-xs leading-relaxed text-amber-ink"><b class="font-extrabold">เหตุผลที่แนะนำ:</b> {{ stay.reason }}</div>
      </div>
    </div>
  </RouterLink>
</template>
