<script setup>
import { ref, watch, onMounted } from 'vue'
import { fetchReviews } from '../api/hotels'
import Pagination from './Pagination.vue'

const props = defineProps({
  accommodationId: { type: [Number, String], required: true },
  rating: { type: Number, default: 0 },
  reviewCount: { type: Number, default: 0 },
})

const PAGE_SIZE = 10
const SORTS = [
  { key: 'newest', label: 'ใหม่ล่าสุด' },
  { key: 'highest', label: 'คะแนนสูงสุด' },
  { key: 'lowest', label: 'คะแนนต่ำสุด' },
]
const CATEGORY_LABELS = {
  cleanliness: 'ความสะอาด',
  location: 'ทำเล',
  service: 'การบริการ',
  value: 'ความคุ้มค่า',
}

const loading = ref(false)
const errorMessage = ref(null)
const items = ref([])
const total = ref(0)
const page = ref(1)
const sort = ref('newest')

const dateFmt = new Intl.DateTimeFormat('th-TH', { year: 'numeric', month: 'long', day: 'numeric' })
function formatDate(iso) {
  const d = new Date(iso)
  return isNaN(d) ? '' : dateFmt.format(d)
}

// full + half + empty stars for a 0–5 value
function stars(value) {
  const rounded = Math.round((Number(value) || 0) * 2) / 2
  return [1, 2, 3, 4, 5].map((n) => (rounded >= n ? 'full' : rounded >= n - 0.5 ? 'half' : 'empty'))
}

async function load() {
  loading.value = true
  errorMessage.value = null
  try {
    const res = await fetchReviews(props.accommodationId, {
      sort: sort.value,
      page: page.value,
      page_size: PAGE_SIZE,
    })
    items.value = res.items
    total.value = res.total
  } catch (e) {
    errorMessage.value = e.message || String(e)
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(sort, () => {
  page.value = 1
  load()
})
watch(page, load)
watch(() => props.accommodationId, () => {
  page.value = 1
  sort.value = 'newest'
  load()
})

function catChips(r) {
  return Object.entries(CATEGORY_LABELS)
    .map(([key, label]) => ({ label, value: r[`${key}Rating`] }))
    .filter((c) => c.value != null)
}
</script>

<template>
  <div>
    <div class="mb-4 flex flex-wrap items-baseline justify-between gap-2">
      <h2 class="text-[22px] font-bold text-ink sm:text-[24px]">รีวิวจากผู้เข้าพัก</h2>
      <div v-if="reviewCount > 0" class="flex items-center gap-1.5 text-[16px] font-bold text-ink">
        <svg viewBox="0 0 24 24" class="h-[18px] w-[18px] text-gold" fill="currentColor"><path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.8 1.5 6.9L12 17.9l-6.1 3.4 1.5-6.9-5.2-4.8 6.9-.7z" /></svg>
        <span>{{ rating.toFixed(1) }}</span>
        <span class="font-normal text-ink-faint">จาก {{ reviewCount }} รีวิว</span>
      </div>
    </div>

    <!-- no fabricated numbers: whole section stays minimal until real reviews exist -->
    <p v-if="reviewCount === 0" class="rounded-xl border border-dashed border-line bg-white p-6 text-center text-[15px] text-ink-faint">
      ยังไม่มีรีวิวสำหรับที่พักนี้ เป็นคนแรกที่รีวิวได้เมื่อระบบเข้าสู่ระบบพร้อมใช้งาน
    </p>

    <template v-else>
      <!-- sort -->
      <div class="mb-3 flex flex-wrap gap-2">
        <button
          v-for="s in SORTS"
          :key="s.key"
          @click="sort = s.key"
          class="min-h-[40px] rounded-lg border px-3.5 text-[14px] font-semibold transition-colors"
          :class="sort === s.key ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-line bg-white text-ink-soft hover:border-indigo-300'"
        >
          {{ s.label }}
        </button>
      </div>

      <div v-if="loading" class="rounded-xl border border-dashed border-line bg-white p-8 text-center text-[15px] text-ink-soft">
        กำลังโหลดรีวิว...
      </div>
      <div v-else-if="errorMessage" class="rounded-xl border border-red-200 bg-red-50 p-4 text-[15px] text-red-700">
        โหลดรีวิวไม่สำเร็จ: {{ errorMessage }}
      </div>

      <div v-else class="flex flex-col gap-3">
        <article v-for="r in items" :key="r.id" class="rounded-xl border border-line bg-white p-4">
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-2.5">
              <div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-indigo-50 text-[14px] font-bold text-indigo-700">
                {{ (r.userName || 'ผู้เข้าพัก').charAt(0) }}
              </div>
              <div>
                <div class="text-[15px] font-bold text-ink">{{ r.userName || 'ผู้เข้าพัก' }}</div>
                <div class="text-[13px] text-ink-faint">{{ formatDate(r.createdAt) }}</div>
              </div>
            </div>
            <div class="flex gap-0.5">
              <svg v-for="(s, i) in stars(r.rating)" :key="i" viewBox="0 0 24 24" class="h-4 w-4" :class="s === 'empty' ? 'text-line' : 'text-gold'" fill="currentColor">
                <path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.8 1.5 6.9L12 17.9l-6.1 3.4 1.5-6.9-5.2-4.8 6.9-.7z" />
              </svg>
            </div>
          </div>

          <p v-if="r.comment" class="mt-2.5 whitespace-pre-line text-[15px] leading-[1.65] text-ink-soft">{{ r.comment }}</p>

          <div v-if="catChips(r).length" class="mt-2.5 flex flex-wrap gap-1.5">
            <span v-for="c in catChips(r)" :key="c.label" class="rounded-md bg-pagebg px-2 py-1 text-[12px] font-semibold text-ink-soft">
              {{ c.label }} {{ c.value }}/5
            </span>
          </div>
        </article>

        <p v-if="!items.length" class="rounded-xl border border-dashed border-line bg-white p-6 text-center text-[14px] text-ink-faint">
          ไม่พบรีวิวในหน้านี้
        </p>
      </div>

      <Pagination v-if="total > PAGE_SIZE" :page="page" :page-size="PAGE_SIZE" :total="total" @update:page="page = $event" />
    </template>
  </div>
</template>
