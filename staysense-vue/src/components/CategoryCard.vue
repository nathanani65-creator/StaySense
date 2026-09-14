<script setup>
defineProps({
  label: { type: String, required: true },
  img: { type: String, required: true },
  iconPath: { type: String, required: true },
  to: { type: String, default: '/hotels' },
})
</script>

<template>
  <RouterLink
    :to="to"
    class="block overflow-hidden rounded-2xl border border-line bg-white text-center shadow-card transition-transform hover:-translate-y-1 hover:shadow-lg"
  >
    <div class="h-[130px] bg-cover bg-center" :style="{ backgroundImage: `url(${img})` }"></div>
    <div class="relative px-2.5 pb-4 pt-[26px]">
      <div
        class="absolute left-1/2 top-[-24px] flex h-12 w-12 -translate-x-1/2 items-center justify-center rounded-full border border-line bg-white shadow"
      >
        <svg viewBox="0 0 24 24" class="h-[22px] w-[22px] text-indigo-600" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" v-html="iconPath"></svg>
      </div>
      <div class="text-[14.5px] font-extrabold text-ink">{{ label }}</div>
    </div>
  </RouterLink>
</template>
