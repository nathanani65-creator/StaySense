<script setup>
const props = defineProps({
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['locate'])

function onClick() {
  if (props.loading) return
  emit('locate')
}
</script>

<template>
  <button
    @click="onClick"
    type="button"
    :disabled="loading"
    class="flex h-[50px] w-full flex-shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-xl border-[1.5px] px-[18px] py-3 text-[13.5px] font-bold transition-colors disabled:cursor-not-allowed sm:h-auto sm:w-auto"
    :class="loading ? 'border-[#8B87ED] bg-indigo-50 text-indigo-700 opacity-80' : 'border-line bg-white text-ink hover:bg-indigo-50 hover:border-[#D8D5F5]'"
  >
    <svg v-if="loading" viewBox="0 0 24 24" class="h-4 w-4 flex-shrink-0 animate-spin text-indigo-600" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
      <path d="M12 3a9 9 0 1 0 9 9" />
    </svg>
    <svg v-else viewBox="0 0 24 24" class="h-4 w-4 flex-shrink-0 text-indigo-600" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v3M12 19v3M22 12h-3M5 12H2" />
    </svg>
    {{ loading ? 'กำลังระบุตำแหน่ง...' : 'ใช้ตำแหน่งปัจจุบัน' }}
  </button>
</template>
