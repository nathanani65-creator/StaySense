<script setup>
import { ref, computed, onMounted } from 'vue'
import { fetchAdminAmenities, fetchAmenityCategories, createAmenity, updateAmenity, deleteAmenity } from '../../api/adminAmenities'

const amenities = ref([])
const categories = ref([])
const loading = ref(true)
const errorMessage = ref(null)
const busyId = ref(null)

const editingId = ref(null)
const editForm = ref({ label_th: '', category: '' })

const showNewForm = ref(false)
const newForm = ref({ code: '', label_th: '', category: '' })
const newError = ref(null)
const creating = ref(false)

async function load() {
  loading.value = true
  errorMessage.value = null
  try {
    const [a, c] = await Promise.all([fetchAdminAmenities(), fetchAmenityCategories()])
    amenities.value = a
    categories.value = c
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const categoryLabel = computed(() => {
  const map = {}
  for (const c of categories.value) map[c.key] = c.label
  return map
})

const grouped = computed(() => {
  const byCat = {}
  for (const a of amenities.value) {
    const cat = a.category || 'other'
    if (!byCat[cat]) byCat[cat] = []
    byCat[cat].push(a)
  }
  const order = categories.value.map((c) => c.key)
  return order
    .filter((key) => byCat[key]?.length)
    .map((key) => ({ key, label: categoryLabel.value[key] || key, items: byCat[key] }))
})

function startEdit(a) {
  editingId.value = a.id
  editForm.value = { label_th: a.label, category: a.category || 'other' }
}

function cancelEdit() {
  editingId.value = null
}

async function saveEdit(a) {
  busyId.value = a.id
  try {
    const updated = await updateAmenity(a.id, editForm.value)
    Object.assign(a, updated)
    editingId.value = null
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    busyId.value = null
  }
}

async function onDelete(a) {
  const warn = a.accommodationCount > 0
    ? `ที่พัก ${a.accommodationCount} แห่งใช้สิ่งอำนวยความสะดวกนี้อยู่ — ลบแล้วจะหายไปจากที่พักเหล่านั้นด้วย ต้องการลบ "${a.label}" ใช่หรือไม่?`
    : `ต้องการลบ "${a.label}" ใช่หรือไม่?`
  if (!confirm(warn)) return
  busyId.value = a.id
  try {
    await deleteAmenity(a.id)
    amenities.value = amenities.value.filter((x) => x.id !== a.id)
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    busyId.value = null
  }
}

function openNewForm() {
  showNewForm.value = true
  newForm.value = { code: '', label_th: '', category: categories.value[0]?.key || 'other' }
  newError.value = null
}

async function onCreate() {
  creating.value = true
  newError.value = null
  try {
    const created = await createAmenity(newForm.value)
    amenities.value.push(created)
    showNewForm.value = false
  } catch (e) {
    newError.value = e.message || String(e)
  } finally {
    creating.value = false
  }
}

const inputCls = 'w-full rounded-lg border border-line px-2.5 py-1.5 text-[13px] outline-none focus:border-indigo-400'
</script>

<template>
  <div>
    <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-[22px] font-bold text-ink">สิ่งอำนวยความสะดวก</h1>
        <p class="mt-0.5 text-[13.5px] text-ink-soft">ทั้งหมด {{ amenities.length }} รายการ — จัดกลุ่มตามหมวด พร้อมจำนวนที่พักที่ใช้งานอยู่</p>
      </div>
      <button
        type="button"
        @click="openNewForm"
        class="flex min-h-[40px] items-center rounded-xl bg-indigo-600 px-5 text-[14px] font-semibold text-white hover:brightness-105"
      >+ เพิ่มสิ่งอำนวยความสะดวก</button>
    </div>

    <p v-if="errorMessage" class="mb-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-[13.5px] text-red-700">{{ errorMessage }}</p>

    <!-- new amenity form -->
    <section v-if="showNewForm" class="mb-6 rounded-xl border border-indigo-200 bg-indigo-50/30 p-4">
      <h2 class="mb-3 text-[14px] font-bold text-ink">สิ่งอำนวยความสะดวกใหม่</h2>
      <p v-if="newError" class="mb-3 rounded-lg bg-red-50 px-3 py-2 text-[13px] text-red-700">{{ newError }}</p>
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <label class="mb-1 block text-[12px] font-semibold text-ink-soft">โค้ด (ภาษาอังกฤษ, ไม่ซ้ำ) *</label>
          <input v-model="newForm.code" placeholder="เช่น sauna" :class="inputCls" />
        </div>
        <div>
          <label class="mb-1 block text-[12px] font-semibold text-ink-soft">ชื่อที่แสดง (ไทย) *</label>
          <input v-model="newForm.label_th" placeholder="เช่น ห้องซาวน่า" :class="inputCls" />
        </div>
        <div>
          <label class="mb-1 block text-[12px] font-semibold text-ink-soft">หมวด *</label>
          <select v-model="newForm.category" :class="inputCls">
            <option v-for="c in categories" :key="c.key" :value="c.key">{{ c.label }}</option>
          </select>
        </div>
      </div>
      <div class="mt-3 flex justify-end gap-2.5">
        <button type="button" @click="showNewForm = false" class="rounded-lg border border-line px-4 py-2 text-[13px] font-semibold text-ink-soft hover:bg-white">ยกเลิก</button>
        <button
          type="button"
          :disabled="creating || !newForm.code.trim() || !newForm.label_th.trim()"
          @click="onCreate"
          class="rounded-lg bg-indigo-600 px-5 py-2 text-[13px] font-semibold text-white hover:brightness-105 disabled:opacity-60"
        >{{ creating ? 'กำลังบันทึก...' : 'บันทึก' }}</button>
      </div>
    </section>

    <div v-if="loading" class="rounded-xl border border-dashed border-line bg-white p-10 text-center text-ink-faint">กำลังโหลด...</div>

    <div v-else class="flex flex-col gap-5">
      <section v-for="group in grouped" :key="group.key" class="overflow-hidden rounded-xl border border-line bg-white">
        <div class="border-b border-line bg-pagebg/60 px-4 py-2.5">
          <h2 class="text-[13.5px] font-bold text-ink">{{ group.label }}</h2>
          <span class="text-[12px] text-ink-faint">{{ group.items.length }} รายการ</span>
        </div>
        <div class="divide-y divide-line">
          <div v-for="a in group.items" :key="a.id" class="flex items-center gap-3 px-4 py-3">
            <template v-if="editingId === a.id">
              <input v-model="editForm.label_th" :class="inputCls" class="max-w-[240px]" />
              <select v-model="editForm.category" :class="inputCls" class="max-w-[200px]">
                <option v-for="c in categories" :key="c.key" :value="c.key">{{ c.label }}</option>
              </select>
              <div class="ml-auto flex items-center gap-2">
                <button type="button" @click="cancelEdit" class="rounded-lg border border-line px-3 py-1.5 text-[12.5px] font-semibold text-ink-soft hover:bg-pagebg">ยกเลิก</button>
                <button
                  type="button"
                  :disabled="busyId === a.id"
                  @click="saveEdit(a)"
                  class="rounded-lg bg-indigo-600 px-3.5 py-1.5 text-[12.5px] font-semibold text-white hover:brightness-105 disabled:opacity-60"
                >บันทึก</button>
              </div>
            </template>
            <template v-else>
              <div class="min-w-0 flex-1">
                <p class="text-[13.5px] font-semibold text-ink">{{ a.label }}</p>
                <p class="text-[11.5px] text-ink-faint">{{ a.key }}</p>
              </div>
              <span
                class="rounded-full px-2.5 py-1 text-[12px] font-bold tabular-nums"
                :class="a.accommodationCount > 0 ? 'bg-indigo-50 text-indigo-700' : 'bg-pagebg text-ink-faint/70'"
              >{{ a.accommodationCount }} ที่พัก</span>
              <div class="flex items-center gap-2">
                <button type="button" @click="startEdit(a)" class="rounded-lg border border-line px-2.5 py-1.5 text-[12.5px] font-semibold text-indigo-700 hover:bg-indigo-50">แก้ไข</button>
                <button
                  type="button"
                  :disabled="busyId === a.id"
                  @click="onDelete(a)"
                  class="rounded-lg border border-line px-2.5 py-1.5 text-[12.5px] font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
                >ลบ</button>
              </div>
            </template>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
