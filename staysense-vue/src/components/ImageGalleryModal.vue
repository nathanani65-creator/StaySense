<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, required: true },
  subtitle: { type: String, default: null },
  images: { type: Array, default: () => [] }, // [{ url, thumbnailUrl, category, caption, altText, sourceName, sourceUrl }]
  initialIndex: { type: Number, default: 0 },
  categoryLabels: { type: Object, default: () => ({}) }, // { key: label }
})
const emit = defineEmits(['close'])

const index = ref(props.initialIndex)
const dialogRef = ref(null)
const closeBtnRef = ref(null)
let touchStartX = null
let previousActiveEl = null
let previousOverflow = ''

const current = computed(() => props.images[index.value] || null)
const categoryText = computed(() => {
  const c = current.value?.category
  return c ? props.categoryLabels[c] || c : null
})

function go(delta) {
  if (!props.images.length) return
  index.value = (index.value + delta + props.images.length) % props.images.length
}
function goTo(i) {
  index.value = i
}

function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
  else if (e.key === 'ArrowLeft') go(-1)
  else if (e.key === 'ArrowRight') go(1)
  else if (e.key === 'Tab') trapFocus(e)
}

function trapFocus(e) {
  const root = dialogRef.value
  if (!root) return
  const focusable = root.querySelectorAll('button, [href], [tabindex]:not([tabindex="-1"])')
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}

function onTouchStart(e) {
  touchStartX = e.changedTouches[0].clientX
}
function onTouchEnd(e) {
  if (touchStartX == null) return
  const dx = e.changedTouches[0].clientX - touchStartX
  if (Math.abs(dx) > 40) go(dx > 0 ? -1 : 1)
  touchStartX = null
}

watch(
  () => props.visible,
  async (open) => {
    if (open) {
      index.value = props.initialIndex
      previousActiveEl = document.activeElement
      previousOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      window.addEventListener('keydown', onKeydown)
      await nextTick()
      closeBtnRef.value?.focus()
    } else {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKeydown)
      previousActiveEl?.focus?.()
    }
  }
)
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-[80] flex items-center justify-center bg-black/80 p-3 sm:p-6"
      @click.self="emit('close')"
    >
      <div
        ref="dialogRef"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
        class="flex max-h-full w-full max-w-[1100px] flex-col overflow-hidden rounded-2xl bg-white"
        @touchstart="onTouchStart"
        @touchend="onTouchEnd"
      >
        <div class="flex flex-shrink-0 items-center justify-between gap-3 border-b border-line px-4 py-3 sm:px-5">
          <div class="min-w-0">
            <h3 class="truncate text-[15px] font-extrabold text-ink">{{ title }}</h3>
            <p v-if="subtitle" class="truncate text-[12.5px] text-ink-faint">{{ subtitle }}</p>
          </div>
          <button
            ref="closeBtnRef"
            type="button"
            aria-label="ปิดแกลเลอรีรูปภาพ"
            @click="emit('close')"
            class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border border-line text-ink-soft hover:bg-pagebg"
          >
            <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
          </button>
        </div>

        <div v-if="!images.length" class="p-10 text-center text-[13.5px] text-ink-faint">ยังไม่มีรูปภาพ</div>

        <template v-else>
          <div class="relative flex min-h-0 flex-1 items-center justify-center bg-black/5">
            <button
              v-if="images.length > 1"
              type="button"
              aria-label="รูปก่อนหน้า"
              @click="go(-1)"
              class="absolute left-2 top-1/2 z-10 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-ink shadow hover:bg-white sm:left-4"
            >
              <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6" /></svg>
            </button>
            <img
              :key="current?.url"
              :src="current?.url"
              :alt="current?.altText || title"
              class="max-h-[55vh] max-w-full object-contain sm:max-h-[65vh]"
            />
            <button
              v-if="images.length > 1"
              type="button"
              aria-label="รูปถัดไป"
              @click="go(1)"
              class="absolute right-2 top-1/2 z-10 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-ink shadow hover:bg-white sm:right-4"
            >
              <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6" /></svg>
            </button>
            <span class="absolute bottom-2.5 right-2.5 rounded-full bg-black/65 px-2.5 py-1 text-[12px] font-bold text-white">{{ index + 1 }}/{{ images.length }}</span>
          </div>

          <div v-if="categoryText || current?.caption || current?.sourceName" class="flex-shrink-0 border-t border-line px-4 py-2.5 text-[12.5px] sm:px-5">
            <span v-if="categoryText" class="mr-2 inline-block rounded-full bg-indigo-50 px-2.5 py-0.5 font-bold text-indigo-700">{{ categoryText }}</span>
            <span v-if="current?.caption" class="text-ink-soft">{{ current.caption }}</span>
            <span v-if="current?.sourceName" class="ml-2 text-ink-faint">
              แหล่งที่มา:
              <a v-if="current.sourceUrl" :href="current.sourceUrl" target="_blank" rel="noopener noreferrer" class="underline hover:text-indigo-700">{{ current.sourceName }}</a>
              <template v-else>{{ current.sourceName }}</template>
            </span>
          </div>

          <div v-if="images.length > 1" class="flex flex-shrink-0 gap-2 overflow-x-auto border-t border-line bg-pagebg/60 px-4 py-3 sm:px-5">
            <button
              v-for="(img, i) in images"
              :key="img.url + i"
              type="button"
              @click="goTo(i)"
              class="h-14 w-20 flex-none overflow-hidden rounded-lg border-2"
              :class="i === index ? 'border-indigo-600' : 'border-transparent opacity-70 hover:opacity-100'"
            >
              <img :src="img.thumbnailUrl || img.url" :alt="img.altText || ''" class="h-full w-full object-cover" />
            </button>
          </div>
        </template>
      </div>
    </div>
  </Teleport>
</template>
