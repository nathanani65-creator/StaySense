<script setup>
defineProps({
  name: { type: String, required: true },
  img: { type: String, required: true },
  to: { type: String, default: '/hotels' },
})
</script>

<template>
  <RouterLink
    :to="to"
    class="group relative block h-[190px] overflow-hidden rounded-2xl bg-cover bg-center shadow-card transition-transform hover:-translate-y-1"
    :style="{ backgroundImage: `url(${img})` }"
  >
    <div class="absolute inset-0 bg-gradient-to-t from-[#0F0D28]/75 to-transparent to-55%"></div>
    <span class="absolute bottom-4 left-4 z-[1] text-[15.5px] font-extrabold text-white drop-shadow">{{ name }}</span>
    <span class="absolute bottom-3.5 right-3.5 z-[1] flex h-8 w-8 items-center justify-center rounded-full bg-white/90">
      <svg viewBox="0 0 24 24" class="h-4 w-4 text-indigo-700" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 6l6 6-6 6" />
      </svg>
    </span>
  </RouterLink>
</template>
