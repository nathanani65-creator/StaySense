<script setup>
import { ref, watch, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchAdminAccommodations, fetchAdminSummary, updateAccommodation } from '../../api/admin'
import { useReferenceData } from '../../composables/useReferenceData'
import Pagination from '../../components/Pagination.vue'

const { districts, accommodationTypes, ensureLoaded } = useReferenceData()

const PAGE_SIZE = 20
const STATUS_LABEL = {
  draft: 'ฉบับร่าง',
  pending_review: 'รอตรวจสอบ',
  published: 'เผยแพร่',
  closed: 'ปิดให้บริการ',
}
const STATUS_STYLE = {
  draft: 'bg-pagebg text-ink-faint',
  pending_review: 'bg-amber-bg text-amber-ink',
  published: 'bg-emerald-50 text-emerald-700',
  closed: 'bg-red-50 text-red-700',
}

const items = ref([])
const total = ref(0)
const page = ref(1)
const status = ref('')
const district = ref('')
const type = ref('')
const search = ref('')
const loading = ref(false)
const errorMessage = ref(null)
const busyId = ref(null)

const summary = ref(null)
const summaryLoading = ref(false)

async function load() {
  loading.value = true
  errorMessage.value = null
  try {
    const res = await fetchAdminAccommodations({
      status: status.value || undefined,
      district: district.value || undefined,
      type: type.value || undefined,
      search: search.value || undefined,
      page: page.value,
      page_size: PAGE_SIZE,
    })
    items.value = res.items
    total.value = res.total
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

// Summary only reacts to status + search — it IS the district/type
// breakdown, so those two aren't filters on it, they're what it shows.
async function loadSummary() {
  summaryLoading.value = true
  try {
    summary.value = await fetchAdminSummary({ status: status.value || undefined, search: search.value || undefined })
  } catch {
    summary.value = null // non-critical section; the table below still works
  } finally {
    summaryLoading.value = false
  }
}

onMounted(() => { ensureLoaded(); load(); loadSummary() })
watch(status, () => { page.value = 1; load(); loadSummary() })
watch([district, type], () => { page.value = 1; load() })
watch(page, load)

let searchTimer = null
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; load(); loadSummary() }, 350)
}

// clicking a cell in the summary grid drills the table below into that
// district/type combo — this is the "ง่ายต่อการตรวจสอบ" part
function drillInto(districtName, typeCode) {
  district.value = districtName || ''
  type.value = typeCode || ''
  page.value = 1
  load()
  document.getElementById('admin-acc-table')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function clearDrill() {
  district.value = ''
  type.value = ''
  page.value = 1
  load()
}

async function quickSetStatus(item, newStatus) {
  busyId.value = item.id
  try {
    await updateAccommodation(item.id, { status: newStatus })
    item.status = newStatus
    loadSummary()
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <div>
    <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-[22px] font-bold text-ink">ข้อมูลที่พัก</h1>
        <p class="mt-0.5 text-[13.5px] text-ink-soft">ทั้งหมด {{ total }} แห่ง</p>
      </div>
      <RouterLink
        :to="{ name: 'admin-accommodation-new' }"
        class="flex min-h-[40px] items-center rounded-xl bg-indigo-600 px-5 text-[14px] font-semibold text-white hover:brightness-105"
      >+ เพิ่มที่พักใหม่</RouterLink>
    </div>

    <!-- summary: district x type breakdown -->
    <section class="mb-6 overflow-hidden rounded-xl border border-line bg-white">
      <div class="border-b border-line px-4 py-3">
        <h2 class="text-[14.5px] font-bold text-ink">สรุปจำนวนที่พักตามอำเภอและประเภท</h2>
        <p class="mt-0.5 text-[12.5px] text-ink-faint">คลิกตัวเลขเพื่อดูรายการเฉพาะอำเภอ/ประเภทนั้น — ช่วยตรวจสอบว่าข้อมูลครบทุกหมวดหรือยัง</p>
      </div>
      <div v-if="summaryLoading" class="p-6 text-center text-[13.5px] text-ink-faint">กำลังโหลด...</div>
      <div v-else-if="summary" class="overflow-x-auto">
        <table class="w-full text-left text-[13px]">
          <thead>
            <tr class="border-b border-line text-[12px] font-semibold text-ink-faint">
              <th class="px-4 py-2.5">อำเภอ</th>
              <th v-for="code in summary.typeCodes" :key="code" class="px-3 py-2.5 text-right">{{ summary.typeLabels[code] }}</th>
              <th class="px-4 py-2.5 text-right">รวม</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in summary.rows" :key="row.district" class="border-b border-line last:border-0 hover:bg-pagebg/60">
              <td class="px-4 py-2 font-semibold text-ink">
                <button type="button" class="hover:text-indigo-700 hover:underline" @click="drillInto(row.district, '')">{{ row.district }}</button>
              </td>
              <td v-for="code in summary.typeCodes" :key="code" class="px-3 py-2 text-right">
                <button
                  type="button"
                  class="tabular-nums hover:text-indigo-700 hover:underline"
                  :class="row.counts[code] === 0 ? 'text-ink-faint/60' : 'font-semibold text-ink-soft'"
                  @click="drillInto(row.district, code)"
                >{{ row.counts[code] }}</button>
              </td>
              <td class="px-4 py-2 text-right font-bold text-ink">{{ row.total }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="border-t-2 border-line bg-pagebg/60 text-[13px] font-bold text-ink">
              <td class="px-4 py-2.5">รวมทั้งหมด</td>
              <td v-for="code in summary.typeCodes" :key="code" class="px-3 py-2.5 text-right tabular-nums">
                <button type="button" class="hover:text-indigo-700 hover:underline" @click="drillInto('', code)">{{ summary.totals[code] }}</button>
              </td>
              <td class="px-4 py-2.5 text-right">{{ summary.grandTotal }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>

    <div class="mb-4 flex flex-wrap gap-2.5">
      <input
        v-model="search"
        @input="onSearchInput"
        type="text"
        placeholder="ค้นหาชื่อที่พัก..."
        class="min-w-[220px] flex-1 rounded-xl border border-line px-3.5 py-2.5 text-[14px] outline-none focus:border-indigo-400"
      />
      <select v-model="status" class="rounded-xl border border-line px-3.5 py-2.5 text-[14px] outline-none focus:border-indigo-400">
        <option value="">ทุกสถานะ</option>
        <option v-for="(label, code) in STATUS_LABEL" :key="code" :value="code">{{ label }}</option>
      </select>
      <select v-model="district" class="rounded-xl border border-line px-3.5 py-2.5 text-[14px] outline-none focus:border-indigo-400">
        <option value="">ทุกอำเภอ</option>
        <option v-for="d in districts" :key="d.key" :value="d.key">{{ d.key }}</option>
      </select>
      <select v-model="type" class="rounded-xl border border-line px-3.5 py-2.5 text-[14px] outline-none focus:border-indigo-400">
        <option value="">ทุกประเภท</option>
        <option v-for="t in accommodationTypes" :key="t.code" :value="t.code">{{ t.key }}</option>
      </select>
      <button
        v-if="district || type"
        type="button"
        @click="clearDrill"
        class="rounded-xl border border-line px-3.5 py-2.5 text-[13.5px] font-semibold text-ink-faint hover:bg-pagebg"
      >ล้างตัวกรองอำเภอ/ประเภท ✕</button>
    </div>

    <p v-if="errorMessage" class="mb-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-[13.5px] text-red-700">{{ errorMessage }}</p>

    <div id="admin-acc-table" class="scroll-mt-6 overflow-x-auto rounded-xl border border-line bg-white">
      <table class="w-full text-left text-[13.5px]">
        <thead>
          <tr class="border-b border-line text-[12.5px] font-semibold text-ink-faint">
            <th class="px-4 py-3">ชื่อที่พัก</th>
            <th class="px-4 py-3">ประเภท</th>
            <th class="px-4 py-3">อำเภอ</th>
            <th class="px-4 py-3">ราคา</th>
            <th class="px-4 py-3">สถานะ</th>
            <th class="px-4 py-3">ตรวจสอบล่าสุด</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="7" class="px-4 py-10 text-center text-ink-faint">กำลังโหลด...</td></tr>
          <tr v-else-if="!items.length"><td colspan="7" class="px-4 py-10 text-center text-ink-faint">ไม่พบที่พัก</td></tr>
          <tr v-for="item in items" :key="item.id" class="border-b border-line last:border-0 hover:bg-pagebg/60">
            <td class="px-4 py-3 font-semibold text-ink">{{ item.name }}</td>
            <td class="px-4 py-3 text-ink-soft">{{ item.type }}</td>
            <td class="px-4 py-3 text-ink-soft">{{ item.district }}</td>
            <td class="px-4 py-3 text-ink-soft">฿{{ item.price.toLocaleString() }}</td>
            <td class="px-4 py-3">
              <span class="rounded-full px-2.5 py-1 text-[12px] font-bold" :class="STATUS_STYLE[item.status]">{{ STATUS_LABEL[item.status] || item.status }}</span>
            </td>
            <td class="px-4 py-3 text-ink-faint">{{ item.lastVerifiedAt || '—' }}</td>
            <td class="px-4 py-3">
              <div class="flex items-center justify-end gap-2">
                <button
                  v-if="item.status !== 'published'"
                  :disabled="busyId === item.id"
                  @click="quickSetStatus(item, 'published')"
                  class="rounded-lg border border-line px-2.5 py-1.5 text-[12.5px] font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
                >เผยแพร่</button>
                <button
                  v-if="item.status !== 'closed'"
                  :disabled="busyId === item.id"
                  @click="quickSetStatus(item, 'closed')"
                  class="rounded-lg border border-line px-2.5 py-1.5 text-[12.5px] font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
                >ปิดให้บริการ</button>
                <RouterLink
                  :to="{ name: 'admin-accommodation-edit', params: { id: item.id } }"
                  class="rounded-lg border border-line px-2.5 py-1.5 text-[12.5px] font-semibold text-indigo-700 hover:bg-indigo-50"
                >แก้ไข</RouterLink>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination v-if="total > PAGE_SIZE" :page="page" :page-size="PAGE_SIZE" :total="total" @update:page="page = $event" />
  </div>
</template>
