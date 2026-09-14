<script setup>
import { ref, onMounted } from 'vue'
import { fetchAdminMembers, setMemberActive, fetchAdminStats } from '../../api/adminMembers'
import Pagination from '../../components/Pagination.vue'

const PAGE_SIZE = 20

const stats = ref(null)
const statsLoading = ref(true)
const statsError = ref(null)

const members = ref([])
const total = ref(0)
const page = ref(1)
const search = ref('')
const loading = ref(false)
const errorMessage = ref(null)
const busyId = ref(null)

async function loadStats() {
  statsLoading.value = true
  statsError.value = null
  try {
    stats.value = await fetchAdminStats()
  } catch (e) {
    statsError.value = e.message || String(e)
  } finally {
    statsLoading.value = false
  }
}

async function loadMembers() {
  loading.value = true
  errorMessage.value = null
  try {
    const res = await fetchAdminMembers({ search: search.value || undefined, page: page.value, page_size: PAGE_SIZE })
    members.value = res.items
    total.value = res.total
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadStats(); loadMembers() })

let searchTimer = null
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; loadMembers() }, 350)
}

function pageChange(p) {
  page.value = p
  loadMembers()
}

async function toggleActive(m) {
  busyId.value = m.id
  try {
    const updated = await setMemberActive(m.id, !m.isActive)
    m.isActive = updated.isActive
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    busyId.value = null
  }
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('th-TH', { year: 'numeric', month: 'short', day: 'numeric' })
}
</script>

<template>
  <div>
    <div class="mb-5">
      <h1 class="text-[22px] font-bold text-ink">สมาชิกและสถิติ</h1>
      <p class="mt-0.5 text-[13.5px] text-ink-soft">ภาพรวมการใช้งานระบบ และการจัดการสมาชิก</p>
    </div>

    <!-- stats dashboard -->
    <div v-if="statsLoading" class="mb-6 rounded-xl border border-dashed border-line bg-white p-8 text-center text-ink-faint">กำลังโหลดสถิติ...</div>
    <p v-else-if="statsError" class="mb-6 rounded-lg bg-red-50 px-3.5 py-2.5 text-[13.5px] text-red-700">{{ statsError }}</p>
    <div v-else-if="stats" class="mb-6 flex flex-col gap-5">
      <!-- top numbers -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div class="rounded-xl border border-line bg-white p-4">
          <p class="text-[12px] font-semibold text-ink-faint">สมาชิกทั้งหมด</p>
          <p class="mt-1 text-[24px] font-bold text-ink">{{ stats.totalMembers }}</p>
        </div>
        <div class="rounded-xl border border-line bg-white p-4">
          <p class="text-[12px] font-semibold text-ink-faint">สมาชิกที่ใช้งานได้</p>
          <p class="mt-1 text-[24px] font-bold text-emerald-700">{{ stats.activeMembers }}</p>
        </div>
        <div class="rounded-xl border border-line bg-white p-4">
          <p class="text-[12px] font-semibold text-ink-faint">ถูกระงับใช้งาน</p>
          <p class="mt-1 text-[24px] font-bold text-red-700">{{ stats.suspendedMembers }}</p>
        </div>
        <div class="rounded-xl border border-line bg-white p-4">
          <p class="text-[12px] font-semibold text-ink-faint">จำนวนการค้นหาทั้งหมด</p>
          <p class="mt-1 text-[24px] font-bold text-ink">{{ stats.totalSearches }}</p>
        </div>
      </div>

      <!-- data quality -->
      <section class="rounded-xl border border-line bg-white p-4">
        <h2 class="mb-3 text-[14px] font-bold text-ink">คุณภาพข้อมูลที่พัก (เผยแพร่แล้ว {{ stats.dataQuality.totalPublished }} แห่ง)</h2>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div class="flex items-center justify-between rounded-lg bg-pagebg/60 px-3.5 py-2.5">
            <span class="text-[13px] text-ink-soft">ยังไม่เคยตรวจสอบข้อมูล</span>
            <span class="text-[15px] font-bold" :class="stats.dataQuality.missingVerification > 0 ? 'text-amber-ink' : 'text-ink'">{{ stats.dataQuality.missingVerification }}</span>
          </div>
          <div class="flex items-center justify-between rounded-lg bg-pagebg/60 px-3.5 py-2.5">
            <span class="text-[13px] text-ink-soft">ตรวจสอบล่าสุดเกิน 90 วัน</span>
            <span class="text-[15px] font-bold" :class="stats.dataQuality.staleVerification > 0 ? 'text-amber-ink' : 'text-ink'">{{ stats.dataQuality.staleVerification }}</span>
          </div>
        </div>
      </section>

      <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <!-- top favorited -->
        <section class="rounded-xl border border-line bg-white p-4">
          <h2 class="mb-3 text-[14px] font-bold text-ink">ที่พักที่ถูกบุ๊กมาร์กมากที่สุด</h2>
          <div v-if="!stats.topFavorited.length" class="rounded-lg border border-dashed border-line p-4 text-center text-[12.5px] text-ink-faint">
            ยังไม่มีข้อมูลรายการโปรด
          </div>
          <ol v-else class="flex flex-col gap-2">
            <li v-for="(f, i) in stats.topFavorited" :key="f.id" class="flex items-center justify-between text-[13px]">
              <span class="text-ink-soft">{{ i + 1 }}. {{ f.name }}</span>
              <span class="font-bold text-ink">{{ f.favoriteCount }} คน</span>
            </li>
          </ol>
        </section>

        <!-- search terms -->
        <section class="rounded-xl border border-line bg-white p-4">
          <h2 class="mb-3 text-[14px] font-bold text-ink">คำค้นหายอดนิยม</h2>
          <div v-if="!stats.topSearchTerms.length" class="rounded-lg border border-dashed border-line p-4 text-center text-[12.5px] text-ink-faint">
            ยังไม่มีข้อมูลการค้นหา
          </div>
          <ol v-else class="flex flex-col gap-2">
            <li v-for="(t, i) in stats.topSearchTerms" :key="t.term + i" class="flex items-center justify-between gap-2 text-[13px]">
              <span class="truncate text-ink-soft">{{ i + 1 }}. "{{ t.term }}"</span>
              <span class="flex-none font-bold text-ink">{{ t.count }} ครั้ง</span>
            </li>
          </ol>
        </section>
      </div>

      <section v-if="stats.noResultSearchTerms.length" class="rounded-xl border border-amber-bg bg-amber-bg/40 p-4">
        <h2 class="mb-3 text-[14px] font-bold text-ink">คำค้นหาที่ไม่พบผลลัพธ์ — โอกาสเพิ่มข้อมูล/คำพ้องความหมาย</h2>
        <ol class="flex flex-col gap-2">
          <li v-for="(t, i) in stats.noResultSearchTerms" :key="t.term + i" class="flex items-center justify-between gap-2 text-[13px]">
            <span class="truncate text-ink-soft">{{ i + 1 }}. "{{ t.term }}"</span>
            <span class="flex-none font-bold text-ink">{{ t.count }} ครั้ง</span>
          </li>
        </ol>
      </section>

      <p v-if="!stats.comparisonFeatureBuilt" class="rounded-xl border border-dashed border-line bg-white px-4 py-3 text-[13px] text-ink-faint">
        สถิติการใช้งาน "เปรียบเทียบที่พัก" ยังไม่พร้อมแสดง เนื่องจากฟีเจอร์เปรียบเทียบยังไม่ได้พัฒนาในระบบ
      </p>
    </div>

    <!-- member list -->
    <div class="mb-3 flex items-center justify-between">
      <h2 class="text-[16px] font-bold text-ink">รายชื่อสมาชิก ({{ total }})</h2>
    </div>
    <input
      v-model="search"
      @input="onSearchInput"
      type="text"
      placeholder="ค้นหาชื่อหรืออีเมล..."
      class="mb-4 w-full max-w-[320px] rounded-xl border border-line px-3.5 py-2.5 text-[14px] outline-none focus:border-indigo-400"
    />

    <p v-if="errorMessage" class="mb-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-[13.5px] text-red-700">{{ errorMessage }}</p>

    <div class="overflow-x-auto rounded-xl border border-line bg-white">
      <table class="w-full text-left text-[13.5px]">
        <thead>
          <tr class="border-b border-line text-[12.5px] font-semibold text-ink-faint">
            <th class="px-4 py-3">ชื่อ</th>
            <th class="px-4 py-3">อีเมล</th>
            <th class="px-4 py-3">บทบาท</th>
            <th class="px-4 py-3">รายการโปรด</th>
            <th class="px-4 py-3">สมัครเมื่อ</th>
            <th class="px-4 py-3">สถานะ</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="7" class="px-4 py-10 text-center text-ink-faint">กำลังโหลด...</td></tr>
          <tr v-else-if="!members.length"><td colspan="7" class="px-4 py-10 text-center text-ink-faint">ไม่พบสมาชิก</td></tr>
          <tr v-for="m in members" :key="m.id" class="border-b border-line last:border-0 hover:bg-pagebg/60">
            <td class="px-4 py-3 font-semibold text-ink">{{ m.name }}</td>
            <td class="px-4 py-3 text-ink-soft">{{ m.email }}</td>
            <td class="px-4 py-3">
              <span class="rounded-full px-2.5 py-1 text-[12px] font-bold" :class="m.role === 'admin' ? 'bg-indigo-50 text-indigo-700' : 'bg-pagebg text-ink-faint'">
                {{ m.role === 'admin' ? 'ผู้ดูแลระบบ' : 'สมาชิก' }}
              </span>
            </td>
            <td class="px-4 py-3 text-ink-soft">{{ m.favoriteCount }}</td>
            <td class="px-4 py-3 text-ink-faint">{{ formatDate(m.createdAt) }}</td>
            <td class="px-4 py-3">
              <span class="rounded-full px-2.5 py-1 text-[12px] font-bold" :class="m.isActive ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'">
                {{ m.isActive ? 'ใช้งานได้' : 'ถูกระงับ' }}
              </span>
            </td>
            <td class="px-4 py-3 text-right">
              <button
                v-if="m.role !== 'admin'"
                type="button"
                :disabled="busyId === m.id"
                @click="toggleActive(m)"
                class="rounded-lg border border-line px-2.5 py-1.5 text-[12.5px] font-semibold hover:bg-pagebg disabled:opacity-50"
                :class="m.isActive ? 'text-red-700' : 'text-emerald-700'"
              >{{ m.isActive ? 'ระงับใช้งาน' : 'เปิดใช้งาน' }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination v-if="total > PAGE_SIZE" :page="page" :page-size="PAGE_SIZE" :total="total" @update:page="pageChange" />
  </div>
</template>
