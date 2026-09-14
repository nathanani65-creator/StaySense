<script setup>
import { ref, onMounted } from 'vue'
import { fetchAdminPlaces, fetchPlaceCategories, createPlace, updatePlace, deletePlace } from '../../api/adminPlaces'
import { useReferenceData } from '../../composables/useReferenceData'

const { districts, ensureLoaded } = useReferenceData()

const places = ref([])
const categories = ref([])
const loading = ref(true)
const errorMessage = ref(null)
const busyId = ref(null)

const district = ref('')
const category = ref('')
const search = ref('')

const editingId = ref(null)
const editForm = ref(blankForm())

const showNewForm = ref(false)
const newForm = ref(blankForm())
const newError = ref(null)
const creating = ref(false)

function blankForm() {
  return { name: '', category: '', latitude: '', longitude: '', address: '', is_popular: false, source_note: '', district_name: '' }
}

async function load() {
  loading.value = true
  errorMessage.value = null
  try {
    places.value = await fetchAdminPlaces({
      district: district.value || undefined,
      category: category.value || undefined,
      search: search.value || undefined,
    })
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await ensureLoaded()
  categories.value = await fetchPlaceCategories()
  load()
})

let searchTimer = null
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 350)
}

function categoryLabel(key) {
  return categories.value.find((c) => c.key === key)?.label || key
}

function startEdit(p) {
  editingId.value = p.id
  editForm.value = {
    name: p.name, category: p.category, latitude: p.latitude, longitude: p.longitude,
    address: p.address || '', is_popular: p.isPopular, source_note: p.sourceNote || '', district_name: p.districtName || '',
  }
}
function cancelEdit() {
  editingId.value = null
}

function buildPayload(f) {
  return {
    name: f.name,
    category: f.category,
    latitude: Number(f.latitude),
    longitude: Number(f.longitude),
    address: f.address || null,
    is_popular: !!f.is_popular,
    source_note: f.source_note || null,
    district_name: f.district_name || null,
  }
}

async function saveEdit(p) {
  busyId.value = p.id
  try {
    const updated = await updatePlace(p.id, buildPayload(editForm.value))
    Object.assign(p, updated)
    editingId.value = null
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    busyId.value = null
  }
}

async function onDelete(p) {
  if (!confirm(`ต้องการลบ "${p.name}" ใช่หรือไม่?`)) return
  busyId.value = p.id
  try {
    await deletePlace(p.id)
    places.value = places.value.filter((x) => x.id !== p.id)
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    busyId.value = null
  }
}

function openNewForm() {
  showNewForm.value = true
  newForm.value = { ...blankForm(), category: categories.value[0]?.key || '' }
  newError.value = null
}

async function onCreate() {
  creating.value = true
  newError.value = null
  try {
    const created = await createPlace(buildPayload(newForm.value))
    places.value.push(created)
    places.value.sort((a, b) => a.name.localeCompare(b.name))
    showNewForm.value = false
  } catch (e) {
    newError.value = e.message || String(e)
  } finally {
    creating.value = false
  }
}

const inputCls = 'w-full rounded-lg border border-line px-2.5 py-1.5 text-[13px] outline-none focus:border-indigo-400'
const labelCls = 'mb-1 block text-[11.5px] font-semibold text-ink-soft'
</script>

<template>
  <div>
    <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-[22px] font-bold text-ink">สถานที่สำคัญ</h1>
        <p class="mt-0.5 text-[13.5px] text-ink-soft">ทั้งหมด {{ places.length }} แห่ง — ใช้คำนวณ "สถานที่ใกล้เคียง" บนหน้ารายละเอียดที่พักโดยอัตโนมัติตามระยะทาง</p>
      </div>
      <button
        type="button"
        @click="openNewForm"
        class="flex min-h-[40px] items-center rounded-xl bg-indigo-600 px-5 text-[14px] font-semibold text-white hover:brightness-105"
      >+ เพิ่มสถานที่</button>
    </div>

    <div class="mb-4 flex flex-wrap gap-2.5">
      <input
        v-model="search"
        @input="onSearchInput"
        type="text"
        placeholder="ค้นหาชื่อสถานที่..."
        class="min-w-[220px] flex-1 rounded-xl border border-line px-3.5 py-2.5 text-[14px] outline-none focus:border-indigo-400"
      />
      <select v-model="district" @change="load" class="rounded-xl border border-line px-3.5 py-2.5 text-[14px] outline-none focus:border-indigo-400">
        <option value="">ทุกอำเภอ</option>
        <option v-for="d in districts" :key="d.key" :value="d.key">{{ d.key }}</option>
      </select>
      <select v-model="category" @change="load" class="rounded-xl border border-line px-3.5 py-2.5 text-[14px] outline-none focus:border-indigo-400">
        <option value="">ทุกประเภท</option>
        <option v-for="c in categories" :key="c.key" :value="c.key">{{ c.label }}</option>
      </select>
    </div>

    <p v-if="errorMessage" class="mb-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-[13.5px] text-red-700">{{ errorMessage }}</p>

    <!-- new place form -->
    <section v-if="showNewForm" class="mb-6 rounded-xl border border-indigo-200 bg-indigo-50/30 p-4">
      <h2 class="mb-3 text-[14px] font-bold text-ink">สถานที่ใหม่</h2>
      <p v-if="newError" class="mb-3 rounded-lg bg-red-50 px-3 py-2 text-[13px] text-red-700">{{ newError }}</p>
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div><label :class="labelCls">ชื่อสถานที่ *</label><input v-model="newForm.name" :class="inputCls" /></div>
        <div>
          <label :class="labelCls">ประเภท *</label>
          <select v-model="newForm.category" :class="inputCls">
            <option v-for="c in categories" :key="c.key" :value="c.key">{{ c.label }}</option>
          </select>
        </div>
        <div>
          <label :class="labelCls">อำเภอ</label>
          <select v-model="newForm.district_name" :class="inputCls">
            <option value="">ไม่ระบุ</option>
            <option v-for="d in districts" :key="d.key" :value="d.key">{{ d.key }}</option>
          </select>
        </div>
        <div><label :class="labelCls">Latitude *</label><input v-model="newForm.latitude" type="number" step="0.0000001" :class="inputCls" /></div>
        <div><label :class="labelCls">Longitude *</label><input v-model="newForm.longitude" type="number" step="0.0000001" :class="inputCls" /></div>
        <div><label :class="labelCls">ที่อยู่</label><input v-model="newForm.address" :class="inputCls" /></div>
        <div class="sm:col-span-2"><label :class="labelCls">แหล่งข้อมูล/หมายเหตุ</label><input v-model="newForm.source_note" :class="inputCls" /></div>
        <div class="flex items-center gap-2 pt-6"><input v-model="newForm.is_popular" type="checkbox" id="pop-new" /><label for="pop-new" class="text-[13px] font-semibold text-ink">สถานที่ท่องเที่ยวยอดนิยม</label></div>
      </div>
      <div class="mt-3 flex justify-end gap-2.5">
        <button type="button" @click="showNewForm = false" class="rounded-lg border border-line px-4 py-2 text-[13px] font-semibold text-ink-soft hover:bg-white">ยกเลิก</button>
        <button
          type="button"
          :disabled="creating || !newForm.name.trim() || !newForm.category || newForm.latitude === '' || newForm.longitude === ''"
          @click="onCreate"
          class="rounded-lg bg-indigo-600 px-5 py-2 text-[13px] font-semibold text-white hover:brightness-105 disabled:opacity-60"
        >{{ creating ? 'กำลังบันทึก...' : 'บันทึก' }}</button>
      </div>
    </section>

    <div v-if="loading" class="rounded-xl border border-dashed border-line bg-white p-10 text-center text-ink-faint">กำลังโหลด...</div>
    <div v-else-if="!places.length" class="rounded-xl border border-dashed border-line bg-white p-10 text-center text-ink-faint">ไม่พบสถานที่</div>

    <div v-else class="overflow-hidden rounded-xl border border-line bg-white">
      <div class="divide-y divide-line">
        <div v-for="p in places" :key="p.id" class="p-4">
          <template v-if="editingId === p.id">
            <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div><label :class="labelCls">ชื่อสถานที่ *</label><input v-model="editForm.name" :class="inputCls" /></div>
              <div>
                <label :class="labelCls">ประเภท *</label>
                <select v-model="editForm.category" :class="inputCls">
                  <option v-for="c in categories" :key="c.key" :value="c.key">{{ c.label }}</option>
                </select>
              </div>
              <div>
                <label :class="labelCls">อำเภอ</label>
                <select v-model="editForm.district_name" :class="inputCls">
                  <option value="">ไม่ระบุ</option>
                  <option v-for="d in districts" :key="d.key" :value="d.key">{{ d.key }}</option>
                </select>
              </div>
              <div><label :class="labelCls">Latitude *</label><input v-model="editForm.latitude" type="number" step="0.0000001" :class="inputCls" /></div>
              <div><label :class="labelCls">Longitude *</label><input v-model="editForm.longitude" type="number" step="0.0000001" :class="inputCls" /></div>
              <div><label :class="labelCls">ที่อยู่</label><input v-model="editForm.address" :class="inputCls" /></div>
              <div class="sm:col-span-2"><label :class="labelCls">แหล่งข้อมูล/หมายเหตุ</label><input v-model="editForm.source_note" :class="inputCls" /></div>
              <div class="flex items-center gap-2 pt-6"><input v-model="editForm.is_popular" type="checkbox" :id="`pop-${p.id}`" /><label :for="`pop-${p.id}`" class="text-[13px] font-semibold text-ink">สถานที่ท่องเที่ยวยอดนิยม</label></div>
            </div>
            <div class="mt-3 flex justify-end gap-2.5">
              <button type="button" @click="cancelEdit" class="rounded-lg border border-line px-4 py-2 text-[13px] font-semibold text-ink-soft hover:bg-pagebg">ยกเลิก</button>
              <button
                type="button"
                :disabled="busyId === p.id"
                @click="saveEdit(p)"
                class="rounded-lg bg-indigo-600 px-5 py-2 text-[13px] font-semibold text-white hover:brightness-105 disabled:opacity-60"
              >บันทึก</button>
            </div>
          </template>
          <template v-else>
            <div class="flex items-center gap-3">
              <div class="min-w-0 flex-1">
                <p class="flex items-center gap-2 text-[14px] font-semibold text-ink">
                  {{ p.name }}
                  <span v-if="p.isPopular" class="rounded-full bg-amber-bg px-2 py-0.5 text-[11px] font-bold text-amber-ink">ยอดนิยม</span>
                </p>
                <p class="mt-0.5 text-[12px] text-ink-faint">
                  {{ categoryLabel(p.category) }}
                  <span v-if="p.districtName"> · {{ p.districtName }}</span>
                  <span v-if="p.address"> · {{ p.address }}</span>
                </p>
              </div>
              <div class="flex flex-none items-center gap-2">
                <button type="button" @click="startEdit(p)" class="rounded-lg border border-line px-2.5 py-1.5 text-[12.5px] font-semibold text-indigo-700 hover:bg-indigo-50">แก้ไข</button>
                <button
                  type="button"
                  :disabled="busyId === p.id"
                  @click="onDelete(p)"
                  class="rounded-lg border border-line px-2.5 py-1.5 text-[12.5px] font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
                >ลบ</button>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
