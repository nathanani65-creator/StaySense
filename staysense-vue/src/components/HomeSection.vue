<script setup>
import HotelCard from './HotelCard.vue'
import { useCompare } from '../composables/useCompare'
import { useFavorites } from '../composables/useFavorites'
import { useAuth } from '../composables/useAuth'
import { useRouter } from 'vue-router'

const props = defineProps({
  icon: { type: String, default: 'compass' }, // sparkle | fire | compass | search | clock
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  badge: { type: String, default: null },
  items: { type: Array, default: () => [] },
  amenities: { type: Array, default: () => [] },
  query: { type: String, default: '' },
  sectionBadge: { type: String, default: null }, // per-card badge, e.g. "สำหรับคุณ"
})

const router = useRouter()
const { isLoggedIn } = useAuth()
const { toggleFavorite } = useFavorites()
const { isInCompare, toggleCompare, isFull } = useCompare()

async function onToggleFav(id) {
  const item = props.items.find((x) => x.id === id)
  if (!item) return
  if (!isLoggedIn.value) {
    alert('เข้าสู่ระบบเพื่อบันทึกที่พักนี้ไว้ในรายการโปรด')
    router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  try {
    await toggleFavorite(item)
  } catch {
    // toggleFavorite already reverted item.fav
  }
}

function onToggleCompare(item) {
  const res = toggleCompare(item)
  if (!res.ok && res.reason === 'limit') {
    alert('สามารถเปรียบเทียบที่พักได้สูงสุด 3 แห่ง กรุณานำที่พักหนึ่งแห่งออกก่อนเพิ่มรายการใหม่')
  }
}
</script>

<template>
  <section v-if="items.length" class="mx-auto max-w-[1320px] px-8 py-10">
    <div class="mb-5 flex flex-wrap items-center justify-between gap-2">
      <div class="flex items-center gap-2">
        <svg v-if="icon === 'sparkle'" viewBox="0 0 24 24" class="h-[19px] w-[19px] text-indigo-600" fill="currentColor">
          <path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.8 1.5 6.9L12 17.9l-6.1 3.4 1.5-6.9-5.2-4.8 6.9-.7z" />
        </svg>
        <svg v-else-if="icon === 'fire'" viewBox="0 0 24 24" class="h-[19px] w-[19px] text-orange-500" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M8.5 14.5A2.5 2.5 0 0 0 11 17a2.5 2.5 0 0 0 2.5-2.5c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7.5 7.5 0 1 1-15 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
        </svg>
        <svg v-else-if="icon === 'search'" viewBox="0 0 24 24" class="h-[19px] w-[19px] text-indigo-600" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
        </svg>
        <svg v-else-if="icon === 'clock'" viewBox="0 0 24 24" class="h-[19px] w-[19px] text-indigo-600" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" />
        </svg>
        <svg v-else viewBox="0 0 24 24" class="h-[19px] w-[19px] text-indigo-600" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="9" /><path d="m8.5 15.5 2-5.5 5.5-2-2 5.5-5.5 2z" />
        </svg>
        <h2 class="text-[19.5px] font-extrabold">{{ title }}</h2>
        <span v-if="badge" class="ml-1 rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-bold text-indigo-700">{{ badge }}</span>
      </div>
    </div>
    <p v-if="subtitle" class="-mt-3 mb-5 text-[13.5px] text-ink-soft">{{ subtitle }}</p>

    <!-- HotelCard uses a wide 270px-image + text row layout (built for
    HotelsView's single-column list), so this grid stays capped at 2 columns
    — 3 columns leaves too little width for the text side at any normal
    desktop viewport. -->
    <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <HotelCard
        v-for="item in items"
        :key="item.id"
        :hotel="item"
        :amenities="amenities"
        :query="query"
        :section-badge="sectionBadge"
        :in-compare="isInCompare(item.id)"
        :compare-disabled="isFull"
        @toggle-fav="onToggleFav"
        @toggle-compare="onToggleCompare"
      />
    </div>
  </section>
</template>
