<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  fetchAdminNearbyPlaces, createAccommodationPlace, updateAccommodationPlace, deleteAccommodationPlace,
  fetchAdminPlaces,
} from '../../api/adminPlaces'
import { PLACE_META, formatDistance } from '../../composables/usePlaceMeta'

const props = defineProps({ accommodationId: { type: [String, Number], required: true } })

const nearbyAll = ref([])       // curated + live-estimated, from GET .../nearby-all
const allPlaces = ref([])       // every place in the system, for the "add one not in the list" fallback
const loading = ref(true)
const errorMessage = ref(null)
const openKey = ref(null)       // 'link-<id>' | 'confirm-<placeId>' | 'manual' | null
const saving = ref(false)

function blankForm() {
  return { place_id: '', distance_km: '', travel_time_minutes: '', travel_method: '', note: '', route_url: '', verified_at: '' }
}
const form = ref(blankForm())
const manualPlaceName = ref('')   // display-only name shown instead of the picker when confirming a known place

function meta(category) {
  return PLACE_META[category] || PLACE_META._
}

// grouped by category, each group sorted by nearest-first, groups ordered by
// their nearest item — mirrors NearbyPlacesModal.vue so the admin browses
// the exact same view a visitor sees on the public detail page
const groups = computed(() => {
  const map = {}
  for (const p of nearbyAll.value) {
    ;(map[p.category] ||= []).push(p)
  }
  return Object.entries(map)
    .map(([category, items]) => ({ category, items, meta: meta(category) }))
    .sort((a, b) => a.items[0].distanceKm - b.items[0].distanceKm)
})

// places not already linked (curated) here, for the manual "add one not in
// the nearby list" fallback — e.g. a far attraction outside the radius
const manualAvailablePlaces = computed(() => {
  const linkedIds = new Set(nearbyAll.value.filter((p) => p.isCurated).map((p) => p.placeId))
  return allPlaces.value.filter((p) => !linkedIds.has(p.id))
})

async function load() {
  loading.value = true
  errorMessage.value = null
  try {
    const [nearbyRows, placeRows] = await Promise.all([
      fetchAdminNearbyPlaces(props.accommodationId),
      fetchAdminPlaces(),
    ])
    nearbyAll.value = nearbyRows
    allPlaces.value = placeRows
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

function startEdit(item) {
  form.value = {
    place_id: item.placeId,
    distance_km: item.distanceKm ?? '',
    travel_time_minutes: '',
    travel_method: '',
    note: '',
    route_url: '',
    verified_at: '',
  }
  manualPlaceName.value = item.name
  openKey.value = `link-${item.linkId}`
}
function startConfirm(item) {
  form.value = { ...blankForm(), place_id: item.placeId, distance_km: item.distanceKm }
  manualPlaceName.value = item.name
  openKey.value = `confirm-${item.placeId}`
}
function startManual() {
  form.value = blankForm()
  manualPlaceName.value = ''
  openKey.value = 'manual'
}
function cancelEdit() {
  openKey.value = null
}

function buildPayload() {
  const f = form.value
  const num = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
  return {
    distance_km: num(f.distance_km),
    travel_time_minutes: num(f.travel_time_minutes),
    travel_method: f.travel_method || null,
    note: f.note || null,
    route_url: f.route_url || null,
    verified_at: f.verified_at || null,
  }
}

async function onSave(linkId) {
  saving.value = true
  errorMessage.value = null
  try {
    if (linkId) {
      await updateAccommodationPlace(linkId, buildPayload())
    } else {
      await createAccommodationPlace(props.accommodationId, { place_id: Number(form.value.place_id), ...buildPayload() })
    }
    openKey.value = null
    await load()
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    saving.value = false
  }
}

async function onDelete(item) {
  if (!confirm(`ยกเลิกการเชื่อมโยงกับ "${item.name}" ใช่หรือไม่?`)) return
  try {
    await deleteAccommodationPlace(item.linkId)
    await load()
  } catch (e) {
    errorMessage.value = e.message || String(e)
  }
}

const inputCls = 'w-full rounded-lg border border-line px-3 py-2 text-[13.5px] outline-none focus:border-indigo-400'
const labelCls = 'mb-1 block text-[12px] font-semibold text-ink-soft'
</script>

<template>
  <div>
    <div class="mb-3 flex items-start justify-between gap-3">
      <p class="text-[12.5px] text-ink-faint">
        รายการนี้คือสถานที่ใกล้เคียงทั้งหมดในรัศมี 12 กม. เหมือนที่ผู้เข้าชมเห็นในหน้าเว็บ — รายการที่มีป้าย "ประมาณ" ยังใช้ระยะทางเส้นตรงคำนวณอัตโนมัติอยู่ กด "ยืนยันระยะทางจริง" เพื่อกรอกระยะทาง/เส้นทางจริงแทน
      </p>
      <button type="button" @click="startManual" class="flex-shrink-0 rounded-lg border border-line px-3.5 py-2 text-[12.5px] font-semibold text-ink-soft hover:bg-pagebg">
        + สถานที่อื่นนอกรัศมี
      </button>
    </div>

    <p v-if="errorMessage" class="mb-3 rounded-lg bg-red-50 px-3.5 py-2.5 text-[13px] text-red-700">{{ errorMessage }}</p>
    <div v-if="loading" class="rounded-lg border border-dashed border-line p-6 text-center text-[13px] text-ink-faint">กำลังโหลด...</div>

    <div v-else class="flex flex-col gap-5">
      <!-- manual add form (place not in the nearby list) -->
      <div v-if="openKey === 'manual'" class="rounded-lg border border-indigo-200 bg-indigo-50/30 p-4">
        <h4 class="mb-3 text-[13.5px] font-bold text-ink">เชื่อมโยงสถานที่นอกรัศมี</h4>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div class="sm:col-span-2 lg:col-span-3">
            <label :class="labelCls">สถานที่ *</label>
            <select v-model="form.place_id" required :class="inputCls">
              <option value="" disabled>เลือกสถานที่</option>
              <option v-for="p in manualAvailablePlaces" :key="p.id" :value="p.id">{{ p.name }} ({{ meta(p.category).label }})</option>
            </select>
          </div>
          <div><label :class="labelCls">ระยะทาง (กม.)</label><input v-model="form.distance_km" type="number" step="0.01" min="0" :class="inputCls" /></div>
          <div><label :class="labelCls">เวลาเดินทาง (นาที)</label><input v-model="form.travel_time_minutes" type="number" min="0" :class="inputCls" /></div>
          <div><label :class="labelCls">วิธีเดินทาง</label><input v-model="form.travel_method" placeholder="เช่น เดิน, ขับรถ" :class="inputCls" /></div>
          <div class="sm:col-span-2 lg:col-span-3"><label :class="labelCls">หมายเหตุเส้นทาง</label><input v-model="form.note" :class="inputCls" /></div>
          <div class="sm:col-span-2"><label :class="labelCls">ลิงก์เส้นทาง (Google Maps)</label><input v-model="form.route_url" :class="inputCls" /></div>
          <div><label :class="labelCls">ตรวจสอบล่าสุดเมื่อ</label><input v-model="form.verified_at" type="date" :class="inputCls" /></div>
        </div>
        <div class="mt-4 flex justify-end gap-2.5">
          <button type="button" @click="cancelEdit" class="rounded-lg border border-line px-4 py-2 text-[13px] font-semibold text-ink-soft hover:bg-white">ยกเลิก</button>
          <button type="button" :disabled="saving || !form.place_id" @click="onSave(null)" class="rounded-lg bg-indigo-600 px-5 py-2 text-[13px] font-semibold text-white hover:brightness-105 disabled:opacity-60">{{ saving ? 'กำลังบันทึก...' : 'เชื่อมโยง' }}</button>
        </div>
      </div>

      <p v-if="!nearbyAll.length" class="rounded-lg border border-dashed border-line p-6 text-center text-[13px] text-ink-faint">ไม่พบสถานที่ในรัศมี 12 กม. (ที่พักอาจยังไม่มีพิกัด)</p>

      <div v-for="g in groups" :key="g.category">
        <h3 class="mb-2 text-[13.5px] font-bold text-ink"><span class="mr-1">{{ g.meta.emoji }}</span>{{ g.meta.label }}</h3>
        <div class="flex flex-col gap-2.5">
          <div v-for="item in g.items" :key="item.placeId" class="rounded-lg border border-line">
            <div class="flex items-center justify-between gap-3 p-3">
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-1.5">
                  <span class="truncate text-[13.5px] font-semibold text-ink">{{ item.name }}</span>
                  <span v-if="item.isPopular" class="flex-shrink-0 rounded-full bg-amber-50 px-2 py-0.5 text-[10.5px] font-bold text-amber-700">ยอดนิยม</span>
                  <span v-if="!item.isCurated" class="flex-shrink-0 rounded-full bg-pagebg px-2 py-0.5 text-[10.5px] font-bold text-ink-faint">ประมาณ</span>
                </div>
                <div class="text-[12px] text-ink-faint">{{ formatDistance(item.distanceKm) }}</div>
              </div>
              <div class="flex flex-shrink-0 items-center gap-2">
                <template v-if="item.isCurated">
                  <button type="button" @click="startEdit(item)" class="rounded-lg border border-line px-2.5 py-1.5 text-[12px] font-semibold text-indigo-700 hover:bg-indigo-50">แก้ไข</button>
                  <button type="button" @click="onDelete(item)" class="rounded-lg border border-line px-2.5 py-1.5 text-[12px] font-semibold text-red-700 hover:bg-red-50">ลบ</button>
                </template>
                <button v-else type="button" @click="startConfirm(item)" class="rounded-lg border border-indigo-200 bg-indigo-50 px-2.5 py-1.5 text-[12px] font-semibold text-indigo-700 hover:bg-indigo-100">ยืนยันระยะทางจริง</button>
              </div>
            </div>

            <div v-if="openKey === `link-${item.linkId}` || openKey === `confirm-${item.placeId}`" class="border-t border-line bg-pagebg/40 p-4">
              <p class="mb-3 text-[12.5px] font-semibold text-ink-soft">{{ manualPlaceName }}</p>
              <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <div><label :class="labelCls">ระยะทาง (กม.)</label><input v-model="form.distance_km" type="number" step="0.01" min="0" :class="inputCls" /></div>
                <div><label :class="labelCls">เวลาเดินทาง (นาที)</label><input v-model="form.travel_time_minutes" type="number" min="0" :class="inputCls" /></div>
                <div><label :class="labelCls">วิธีเดินทาง</label><input v-model="form.travel_method" placeholder="เช่น เดิน, ขับรถ" :class="inputCls" /></div>
                <div class="sm:col-span-2 lg:col-span-3"><label :class="labelCls">หมายเหตุเส้นทาง</label><input v-model="form.note" :class="inputCls" /></div>
                <div class="sm:col-span-2"><label :class="labelCls">ลิงก์เส้นทาง (Google Maps)</label><input v-model="form.route_url" :class="inputCls" /></div>
                <div><label :class="labelCls">ตรวจสอบล่าสุดเมื่อ</label><input v-model="form.verified_at" type="date" :class="inputCls" /></div>
              </div>
              <div class="mt-4 flex justify-end gap-2.5">
                <button type="button" @click="cancelEdit" class="rounded-lg border border-line px-4 py-2 text-[13px] font-semibold text-ink-soft hover:bg-white">ยกเลิก</button>
                <button type="button" :disabled="saving" @click="onSave(item.linkId)" class="rounded-lg bg-indigo-600 px-5 py-2 text-[13px] font-semibold text-white hover:brightness-105 disabled:opacity-60">{{ saving ? 'กำลังบันทึก...' : 'บันทึก' }}</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
