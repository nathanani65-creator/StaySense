<script setup>
const props = defineProps({
  visible: { type: Boolean, default: false },
  message: { type: String, default: 'ไม่สามารถเข้าถึงตำแหน่งปัจจุบันได้ กรุณาอนุญาตการเข้าถึงตำแหน่ง หรือเลือกพื้นที่ที่ต้องการค้นหา' },
})
const emit = defineEmits(['retry', 'choose-district', 'search-landmark', 'close'])

const LANDMARKS = ['วัดพระศรีรัตนมหาธาตุ', 'สถานีรถไฟพิษณุโลก', 'มหาวิทยาลัยนเรศวร', 'โรงพยาบาลพุทธชินราช']
</script>

<template>
  <div v-if="visible" class="fixed inset-0 z-[70] flex items-center justify-center bg-black/45 p-4" @click.self="emit('close')">
    <div class="w-full max-w-[420px] rounded-2xl bg-white p-6 shadow-xl">
      <div class="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-amber-bg">
        <svg viewBox="0 0 24 24" class="h-5 w-5 text-amber-icon" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 21s-7-7.5-7-12a7 7 0 0 1 14 0c0 4.5-7 12-7 12z" /><path d="M9.5 9.5 14.5 14.5M14.5 9.5 9.5 14.5" />
        </svg>
      </div>
      <h3 class="mb-1.5 text-[16px] font-extrabold">ไม่สามารถใช้ตำแหน่งปัจจุบันได้</h3>
      <p class="mb-4 text-[13.5px] leading-relaxed text-ink-soft">{{ message }}</p>

      <div class="mb-4 flex flex-col gap-2">
        <button @click="emit('retry')" class="w-full rounded-xl bg-indigo-600 py-2.5 text-[13.5px] font-bold text-white hover:brightness-[1.06]">ลองอีกครั้ง</button>
        <button @click="emit('choose-district')" class="w-full rounded-xl border-[1.5px] border-line py-2.5 text-[13.5px] font-bold text-ink hover:bg-pagebg">เลือกอำเภอ</button>
      </div>

      <div class="border-t border-line pt-3.5">
        <div class="mb-2 text-[12.5px] font-bold text-ink-soft">หรือค้นหาจากสถานที่สำคัญ</div>
        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="lm in LANDMARKS"
            :key="lm"
            @click="emit('search-landmark', lm)"
            class="rounded-full border border-line bg-pagebg px-3 py-1.5 text-[12px] font-semibold text-ink-soft hover:border-[#D8D5F5] hover:text-indigo-700"
          >
            {{ lm }}
          </button>
        </div>
      </div>

      <button @click="emit('close')" class="mt-4 w-full text-center text-[12.5px] font-semibold text-ink-faint hover:text-ink-soft">ปิด</button>
    </div>
  </div>
</template>
