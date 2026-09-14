<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { useFavorites } from '../composables/useFavorites'
import { fetchFavorites } from '../api/favorites'
import StayCard from '../components/StayCard.vue'

const router = useRouter()
const { isLoggedIn } = useAuth()
const { toggleFavorite } = useFavorites()

const loading = ref(true)
const errorMessage = ref(null)
const items = ref([])

async function load() {
  if (!isLoggedIn.value) {
    router.replace({ path: '/login', query: { redirect: '/favorites' } })
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    items.value = await fetchFavorites()
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

async function onToggleFav(id) {
  const item = items.value.find((x) => x.id === id)
  if (!item) return
  try {
    await toggleFavorite(item)
    // removed from favorites — drop it from this list
    if (!item.fav) items.value = items.value.filter((x) => x.id !== id)
  } catch {
    // toggleFavorite already reverted item.fav; nothing else to do
  }
}

onMounted(load)
watch(isLoggedIn, load)
</script>

<template>
  <div class="mx-auto max-w-[1180px] px-5 pb-20 pt-6 sm:px-8">
    <h1 class="text-[26px] font-bold text-ink sm:text-[30px]">ที่พักที่บันทึกไว้</h1>
    <p class="mt-1.5 text-[15px] text-ink-soft">รายการที่พักที่คุณกดบันทึกเป็นรายการโปรด</p>

    <div v-if="loading" class="mt-8 rounded-2xl border border-dashed border-line bg-white p-16 text-center text-[15px] text-ink-soft">
      กำลังโหลด...
    </div>

    <div v-else-if="errorMessage" class="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6 text-[15px] text-red-700">
      โหลดรายการโปรดไม่สำเร็จ: {{ errorMessage }}
    </div>

    <div v-else-if="!items.length" class="mt-8 rounded-2xl border border-dashed border-line bg-white p-16 text-center">
      <p class="text-[15px] text-ink-soft">ยังไม่มีที่พักที่บันทึกไว้</p>
      <RouterLink to="/hotels" class="mt-4 inline-flex min-h-[44px] items-center rounded-xl bg-indigo-600 px-6 text-[15px] font-semibold text-white hover:brightness-105">ค้นหาที่พัก</RouterLink>
    </div>

    <div v-else class="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
      <StayCard v-for="stay in items" :key="stay.id" :stay="stay" @toggle-fav="onToggleFav" />
    </div>
  </div>
</template>
