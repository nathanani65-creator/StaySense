<script setup>
import { ref, onMounted } from 'vue'
import { fetchAdminRoomTypes, createRoomType, updateRoomType, deleteRoomType } from '../../api/adminRoomTypes'
import { useReferenceData } from '../../composables/useReferenceData'
import AdminImageManager from '../../components/admin/AdminImageManager.vue'

const props = defineProps({ accommodationId: { type: [String, Number], required: true } })
const { amenities } = useReferenceData()

const VIEW_OPTIONS = [
  { value: '', label: 'ไม่ระบุ' },
  { value: 'garden', label: 'วิวสวน' },
  { value: 'river', label: 'วิวแม่น้ำ' },
  { value: 'city', label: 'วิวเมือง' },
  { value: 'mountain', label: 'วิวภูเขา' },
  { value: 'pool', label: 'วิวสระว่ายน้ำ' },
  { value: 'none', label: 'ไม่มีวิวพิเศษ' },
]
const TRI = [
  { value: '', label: 'ไม่ระบุ' },
  { value: 'true', label: 'ได้ / อนุญาต' },
  { value: 'false', label: 'ไม่ได้ / ไม่อนุญาต' },
]

const items = ref([])
const loading = ref(true)
const errorMessage = ref(null)
const openId = ref(null)     // room type id currently being edited, or 'new'
const saving = ref(false)

function blankForm() {
  return {
    name: '', price_per_night: '', standard_occupancy: '', max_occupancy: '',
    bed_type: '', view_type: '', room_size_sqm: '', bedrooms: '', bathrooms: '',
    breakfast_included: false, extra_bed_available: false, extra_bed_price: '', extra_bed_max: '',
    children_allowed: '', smoking_allowed: '', pets_allowed: '',
    units_available: '', description: '', room_amenities: [],
    is_visible: true, sort_order: 0,
  }
}
const form = ref(blankForm())

async function load() {
  loading.value = true
  errorMessage.value = null
  try {
    items.value = await fetchAdminRoomTypes(props.accommodationId)
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

function startNew() {
  form.value = blankForm()
  openId.value = 'new'
}
function startEdit(rt) {
  form.value = {
    name: rt.name, price_per_night: rt.price, standard_occupancy: rt.standardOccupancy ?? '', max_occupancy: rt.maxOccupancy ?? '',
    bed_type: rt.bedType || '', view_type: rt.view || '', room_size_sqm: rt.roomSizeSqm ?? '',
    bedrooms: rt.bedrooms ?? '', bathrooms: rt.bathrooms ?? '',
    breakfast_included: !!rt.breakfastIncluded, extra_bed_available: !!rt.extraBedAvailable,
    extra_bed_price: rt.extraBedPrice ?? '', extra_bed_max: rt.extraBedMax ?? '',
    children_allowed: rt.childrenAllowed === true ? 'true' : rt.childrenAllowed === false ? 'false' : '',
    smoking_allowed: rt.smokingAllowed === true ? 'true' : rt.smokingAllowed === false ? 'false' : '',
    pets_allowed: rt.petsAllowed === true ? 'true' : rt.petsAllowed === false ? 'false' : '',
    units_available: rt.unitsAvailable ?? '', description: rt.description || '',
    room_amenities: [...(rt.roomAmenities || [])],
    is_visible: rt.isVisible !== false, sort_order: 0,
  }
  openId.value = rt.id
}
function cancelEdit() {
  openId.value = null
}

function toggleAmenity(code) {
  const i = form.value.room_amenities.indexOf(code)
  if (i === -1) form.value.room_amenities.push(code)
  else form.value.room_amenities.splice(i, 1)
}

function buildPayload() {
  const f = form.value
  const num = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
  const bool3 = (v) => (v === '' ? null : v === 'true')
  return {
    name: f.name,
    price_per_night: Number(f.price_per_night) || 0,
    standard_occupancy: num(f.standard_occupancy),
    max_occupancy: num(f.max_occupancy),
    bed_type: f.bed_type || null,
    view_type: f.view_type || null,
    room_size_sqm: num(f.room_size_sqm),
    bedrooms: num(f.bedrooms),
    bathrooms: num(f.bathrooms),
    breakfast_included: !!f.breakfast_included,
    extra_bed_available: !!f.extra_bed_available,
    extra_bed_price: num(f.extra_bed_price),
    extra_bed_max: num(f.extra_bed_max),
    children_allowed: bool3(f.children_allowed),
    smoking_allowed: bool3(f.smoking_allowed),
    pets_allowed: bool3(f.pets_allowed),
    units_available: num(f.units_available),
    description: f.description || null,
    room_amenities: f.room_amenities,
    is_visible: !!f.is_visible,
  }
}

async function onSave() {
  saving.value = true
  errorMessage.value = null
  try {
    const payload = buildPayload()
    if (openId.value === 'new') await createRoomType(props.accommodationId, payload)
    else await updateRoomType(openId.value, payload)
    openId.value = null
    await load()
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    saving.value = false
  }
}

async function onDelete(rt) {
  if (!confirm(`ลบประเภทห้อง "${rt.name}" ใช่หรือไม่?`)) return
  try {
    await deleteRoomType(rt.id)
    await load()
  } catch (e) {
    errorMessage.value = e.message || String(e)
  }
}

async function toggleVisible(rt) {
  try {
    await updateRoomType(rt.id, { is_visible: !rt.isVisible })
    rt.isVisible = !rt.isVisible
  } catch (e) {
    errorMessage.value = e.message || String(e)
  }
}

const inputCls = 'w-full rounded-lg border border-line px-3 py-2 text-[13.5px] outline-none focus:border-indigo-400'
const labelCls = 'mb-1 block text-[12px] font-semibold text-ink-soft'
</script>

<template>
  <div>
    <div class="mb-3 flex items-center justify-between">
      <p class="text-[13px] text-ink-faint">ห้อง/บ้านพักของที่พักนี้ — เปิด/ปิดการแสดงผลได้โดยไม่ต้องลบ</p>
      <button type="button" @click="startNew" class="rounded-lg bg-indigo-600 px-4 py-2 text-[13px] font-semibold text-white hover:brightness-105">+ เพิ่มประเภทห้อง</button>
    </div>

    <p v-if="errorMessage" class="mb-3 rounded-lg bg-red-50 px-3.5 py-2.5 text-[13px] text-red-700">{{ errorMessage }}</p>
    <div v-if="loading" class="rounded-lg border border-dashed border-line p-6 text-center text-[13px] text-ink-faint">กำลังโหลด...</div>

    <div v-else class="flex flex-col gap-3">
      <div v-for="rt in items" :key="rt.id" class="rounded-lg border border-line">
        <div class="flex items-center justify-between gap-3 p-3">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="truncate text-[14px] font-semibold text-ink">{{ rt.name }}</span>
              <span v-if="!rt.isVisible" class="flex-shrink-0 rounded-full bg-pagebg px-2 py-0.5 text-[11px] font-bold text-ink-faint">ซ่อนอยู่</span>
            </div>
            <div class="text-[12.5px] text-ink-faint">฿{{ rt.price.toLocaleString() }}/คืน · พักได้สูงสุด {{ rt.maxOccupancy ?? '—' }} คน</div>
          </div>
          <div class="flex flex-shrink-0 items-center gap-2">
            <button type="button" @click="toggleVisible(rt)" class="rounded-lg border border-line px-2.5 py-1.5 text-[12px] font-semibold text-ink-soft hover:bg-pagebg">
              {{ rt.isVisible ? 'ซ่อน' : 'แสดง' }}
            </button>
            <button type="button" @click="startEdit(rt)" class="rounded-lg border border-line px-2.5 py-1.5 text-[12px] font-semibold text-indigo-700 hover:bg-indigo-50">แก้ไข</button>
            <button type="button" @click="onDelete(rt)" class="rounded-lg border border-line px-2.5 py-1.5 text-[12px] font-semibold text-red-700 hover:bg-red-50">ลบ</button>
          </div>
        </div>

        <div v-if="openId === rt.id" class="border-t border-line bg-pagebg/40 p-4">
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div><label :class="labelCls">ชื่อห้อง/บ้านพัก *</label><input v-model="form.name" required :class="inputCls" /></div>
            <div><label :class="labelCls">ราคา/คืน *</label><input v-model="form.price_per_night" type="number" min="0" required :class="inputCls" /></div>
            <div><label :class="labelCls">จำนวนห้อง/หลังที่มี</label><input v-model="form.units_available" type="number" min="0" :class="inputCls" /></div>
            <div><label :class="labelCls">พักปกติ (คน)</label><input v-model="form.standard_occupancy" type="number" min="0" :class="inputCls" /></div>
            <div><label :class="labelCls">พักได้สูงสุด (คน)</label><input v-model="form.max_occupancy" type="number" min="0" :class="inputCls" /></div>
            <div><label :class="labelCls">ประเภทเตียง</label><input v-model="form.bed_type" placeholder="เตียงคู่ 1 เตียง" :class="inputCls" /></div>
            <div><label :class="labelCls">ขนาดห้อง (ตร.ม.)</label><input v-model="form.room_size_sqm" type="number" step="0.1" :class="inputCls" /></div>
            <div><label :class="labelCls">ห้องนอน (สำหรับบ้าน/วิลล่า)</label><input v-model="form.bedrooms" type="number" min="0" :class="inputCls" /></div>
            <div><label :class="labelCls">ห้องน้ำ</label><input v-model="form.bathrooms" type="number" min="0" :class="inputCls" /></div>
            <div>
              <label :class="labelCls">วิวจากห้อง</label>
              <select v-model="form.view_type" :class="inputCls"><option v-for="o in VIEW_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option></select>
            </div>
            <div class="flex items-center gap-2 pt-6"><input v-model="form.breakfast_included" type="checkbox" :id="`bf-${rt.id}`" /><label :for="`bf-${rt.id}`" class="text-[13px] font-semibold text-ink">รวมอาหารเช้า</label></div>
            <div class="flex items-center gap-2 pt-6"><input v-model="form.is_visible" type="checkbox" :id="`vis-${rt.id}`" /><label :for="`vis-${rt.id}`" class="text-[13px] font-semibold text-ink">แสดงผลบนหน้าเว็บ</label></div>
            <div class="flex items-center gap-2 pt-6"><input v-model="form.extra_bed_available" type="checkbox" :id="`eb-${rt.id}`" /><label :for="`eb-${rt.id}`" class="text-[13px] font-semibold text-ink">เสริมเตียงได้</label></div>
            <div><label :class="labelCls">ราคาเสริมเตียง (บาท/คน/คืน)</label><input v-model="form.extra_bed_price" type="number" min="0" :class="inputCls" /></div>
            <div><label :class="labelCls">เสริมได้สูงสุด (เตียง)</label><input v-model="form.extra_bed_max" type="number" min="0" :class="inputCls" /></div>
            <div>
              <label :class="labelCls">เด็กเข้าพักได้ไหม</label>
              <select v-model="form.children_allowed" :class="inputCls"><option v-for="o in TRI" :key="o.value" :value="o.value">{{ o.label }}</option></select>
            </div>
            <div>
              <label :class="labelCls">สูบบุหรี่ได้ไหม</label>
              <select v-model="form.smoking_allowed" :class="inputCls"><option v-for="o in TRI" :key="o.value" :value="o.value">{{ o.label }}</option></select>
            </div>
            <div>
              <label :class="labelCls">สัตว์เลี้ยงเข้าพักได้ไหม</label>
              <select v-model="form.pets_allowed" :class="inputCls"><option v-for="o in TRI" :key="o.value" :value="o.value">{{ o.label }}</option></select>
            </div>
          </div>

          <div class="mt-3"><label :class="labelCls">คำอธิบาย</label><textarea v-model="form.description" rows="2" :class="inputCls"></textarea></div>

          <div class="mt-3">
            <label :class="labelCls">สิ่งอำนวยความสะดวกในห้องนี้</label>
            <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
              <label v-for="a in amenities" :key="a.key" class="flex items-center gap-1.5 rounded-lg border border-line bg-white px-2.5 py-1.5 text-[12.5px] font-medium text-ink-soft">
                <input type="checkbox" :checked="form.room_amenities.includes(a.key)" @change="toggleAmenity(a.key)" />
                {{ a.label }}
              </label>
            </div>
          </div>

          <div class="mt-4 flex justify-end gap-2.5">
            <button type="button" @click="cancelEdit" class="rounded-lg border border-line px-4 py-2 text-[13px] font-semibold text-ink-soft hover:bg-white">ยกเลิก</button>
            <button type="button" :disabled="saving" @click="onSave" class="rounded-lg bg-indigo-600 px-5 py-2 text-[13px] font-semibold text-white hover:brightness-105 disabled:opacity-60">{{ saving ? 'กำลังบันทึก...' : 'บันทึก' }}</button>
          </div>

          <!-- this room type's own gallery — separate from every other room
          type's and from the accommodation-wide gallery -->
          <div class="mt-5 border-t border-line pt-4">
            <AdminImageManager
              group="room_type"
              :owner-id="rt.id"
              title="รูปภาพของห้องพัก"
              empty-text="ยังไม่มีรูปภาพห้องพัก"
            />
          </div>
        </div>
      </div>

      <!-- new room type form -->
      <div v-if="openId === 'new'" class="rounded-lg border border-indigo-200 bg-indigo-50/30 p-4">
        <h3 class="mb-3 text-[13.5px] font-bold text-ink">ประเภทห้องใหม่</h3>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div><label :class="labelCls">ชื่อห้อง/บ้านพัก *</label><input v-model="form.name" required :class="inputCls" /></div>
          <div><label :class="labelCls">ราคา/คืน *</label><input v-model="form.price_per_night" type="number" min="0" required :class="inputCls" /></div>
          <div><label :class="labelCls">จำนวนห้อง/หลังที่มี</label><input v-model="form.units_available" type="number" min="0" :class="inputCls" /></div>
          <div><label :class="labelCls">พักปกติ (คน)</label><input v-model="form.standard_occupancy" type="number" min="0" :class="inputCls" /></div>
          <div><label :class="labelCls">พักได้สูงสุด (คน)</label><input v-model="form.max_occupancy" type="number" min="0" :class="inputCls" /></div>
          <div><label :class="labelCls">ประเภทเตียง</label><input v-model="form.bed_type" placeholder="เตียงคู่ 1 เตียง" :class="inputCls" /></div>
          <div><label :class="labelCls">ขนาดห้อง (ตร.ม.)</label><input v-model="form.room_size_sqm" type="number" step="0.1" :class="inputCls" /></div>
          <div><label :class="labelCls">ห้องนอน (สำหรับบ้าน/วิลล่า)</label><input v-model="form.bedrooms" type="number" min="0" :class="inputCls" /></div>
          <div><label :class="labelCls">ห้องน้ำ</label><input v-model="form.bathrooms" type="number" min="0" :class="inputCls" /></div>
          <div>
            <label :class="labelCls">วิวจากห้อง</label>
            <select v-model="form.view_type" :class="inputCls"><option v-for="o in VIEW_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option></select>
          </div>
          <div class="flex items-center gap-2 pt-6"><input v-model="form.breakfast_included" type="checkbox" id="bf-new" /><label for="bf-new" class="text-[13px] font-semibold text-ink">รวมอาหารเช้า</label></div>
          <div class="flex items-center gap-2 pt-6"><input v-model="form.extra_bed_available" type="checkbox" id="eb-new" /><label for="eb-new" class="text-[13px] font-semibold text-ink">เสริมเตียงได้</label></div>
          <div><label :class="labelCls">ราคาเสริมเตียง (บาท/คน/คืน)</label><input v-model="form.extra_bed_price" type="number" min="0" :class="inputCls" /></div>
          <div><label :class="labelCls">เสริมได้สูงสุด (เตียง)</label><input v-model="form.extra_bed_max" type="number" min="0" :class="inputCls" /></div>
          <div>
            <label :class="labelCls">เด็กเข้าพักได้ไหม</label>
            <select v-model="form.children_allowed" :class="inputCls"><option v-for="o in TRI" :key="o.value" :value="o.value">{{ o.label }}</option></select>
          </div>
          <div>
            <label :class="labelCls">สูบบุหรี่ได้ไหม</label>
            <select v-model="form.smoking_allowed" :class="inputCls"><option v-for="o in TRI" :key="o.value" :value="o.value">{{ o.label }}</option></select>
          </div>
          <div>
            <label :class="labelCls">สัตว์เลี้ยงเข้าพักได้ไหม</label>
            <select v-model="form.pets_allowed" :class="inputCls"><option v-for="o in TRI" :key="o.value" :value="o.value">{{ o.label }}</option></select>
          </div>
        </div>
        <div class="mt-3"><label :class="labelCls">คำอธิบาย</label><textarea v-model="form.description" rows="2" :class="inputCls"></textarea></div>
        <p class="mt-3 rounded-lg border border-dashed border-line bg-white p-3 text-center text-[12.5px] text-ink-faint">
          บันทึกห้องนี้ก่อน จึงจะสามารถเพิ่มรูปภาพห้องพักได้
        </p>
        <div class="mt-3">
          <label :class="labelCls">สิ่งอำนวยความสะดวกในห้องนี้</label>
          <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
            <label v-for="a in amenities" :key="a.key" class="flex items-center gap-1.5 rounded-lg border border-line bg-white px-2.5 py-1.5 text-[12.5px] font-medium text-ink-soft">
              <input type="checkbox" :checked="form.room_amenities.includes(a.key)" @change="toggleAmenity(a.key)" />
              {{ a.label }}
            </label>
          </div>
        </div>
        <div class="mt-4 flex justify-end gap-2.5">
          <button type="button" @click="cancelEdit" class="rounded-lg border border-line px-4 py-2 text-[13px] font-semibold text-ink-soft hover:bg-white">ยกเลิก</button>
          <button type="button" :disabled="saving" @click="onSave" class="rounded-lg bg-indigo-600 px-5 py-2 text-[13px] font-semibold text-white hover:brightness-105 disabled:opacity-60">{{ saving ? 'กำลังบันทึก...' : 'เพิ่มห้อง' }}</button>
        </div>
      </div>

      <p v-if="!items.length && openId !== 'new'" class="rounded-lg border border-dashed border-line p-6 text-center text-[13px] text-ink-faint">ยังไม่มีประเภทห้องพัก</p>
    </div>
  </div>
</template>
