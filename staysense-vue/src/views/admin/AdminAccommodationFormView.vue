<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchAccommodation } from '../../api/hotels'
import { createAccommodation, updateAccommodation } from '../../api/admin'
import { useReferenceData } from '../../composables/useReferenceData'
import AdminRoomTypeEditor from './AdminRoomTypeEditor.vue'
import AdminImageManager from '../../components/admin/AdminImageManager.vue'

const props = defineProps({ id: { type: String, default: null } })
const router = useRouter()
const { districts, accommodationTypes, amenities, ensureLoaded } = useReferenceData()

const isEdit = computed(() => !!props.id)

const loading = ref(!!props.id)
const saving = ref(false)
const errorMessage = ref(null)
const savedNote = ref(null)

function emptyForm() {
  return {
    name: '', type_code: '', district_name: '', price_per_night: '',
    description: '', address: '', latitude: '', longitude: '', google_maps_url: '', landmark_distance_km: '',
    phone: '', contact_line: '', contact_facebook: '', contact_instagram: '', website_url: '',
    checkin_time: '', checkout_time: '', cancellation_policy: '', min_age: '',
    smoking_allowed: '', deposit_required: false, deposit_note: '', payment_methods: '',
    deposit_amount: '', deposit_percent: '', advance_booking_required: false, advance_booking_days: '', price_conditions: '',
    recommended_reason: '', tags: '', amenity_codes: [],
    status: 'draft', last_verified_at: '', source_note: '', is_featured: false,
  }
}

const form = ref(emptyForm())

async function load() {
  await ensureLoaded()
  if (!props.id) return
  loading.value = true
  try {
    const d = await fetchAccommodation(props.id)
    form.value = {
      name: d.name, type_code: d.typeCode, district_name: d.district, price_per_night: d.price,
      description: d.description || '', address: d.address || '',
      latitude: d.latitude ?? '', longitude: d.longitude ?? '', google_maps_url: d.googleMapsUrl || '',
      landmark_distance_km: d.distanceKm ?? '',
      phone: d.contact?.phone || '', contact_line: d.contact?.line || '', contact_facebook: d.contact?.facebook || '',
      contact_instagram: d.contact?.instagram || '', website_url: d.contact?.website || '',
      checkin_time: d.policies?.checkinTime || '', checkout_time: d.policies?.checkoutTime || '',
      cancellation_policy: d.policies?.cancellationPolicy || '', min_age: d.policies?.minAge ?? '',
      smoking_allowed: d.policies?.smokingAllowed === true ? 'true' : d.policies?.smokingAllowed === false ? 'false' : '',
      deposit_required: !!d.policies?.depositRequired, deposit_note: d.policies?.depositNote || '',
      payment_methods: (d.policies?.paymentMethods || []).join(', '),
      deposit_amount: d.policies?.depositAmount ?? '', deposit_percent: d.policies?.depositPercent ?? '',
      advance_booking_required: !!d.policies?.advanceBookingRequired, advance_booking_days: d.policies?.advanceBookingDays ?? '',
      price_conditions: d.policies?.priceConditions || '',
      recommended_reason: d.reason || '', tags: (d.tags || []).join(', '), amenity_codes: [...(d.amenities || [])],
      status: d.status || 'draft', last_verified_at: d.lastVerifiedAt || '', source_note: d.sourceNote || '',
      is_featured: !!d.isFeatured,
    }
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

function buildPayload() {
  const f = form.value
  const num = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
  return {
    name: f.name,
    type_code: f.type_code,
    district_name: f.district_name,
    price_per_night: Number(f.price_per_night) || 0,
    description: f.description || null,
    address: f.address || null,
    latitude: num(f.latitude),
    longitude: num(f.longitude),
    google_maps_url: f.google_maps_url || null,
    landmark_distance_km: num(f.landmark_distance_km),
    phone: f.phone || null,
    contact_line: f.contact_line || null,
    contact_facebook: f.contact_facebook || null,
    contact_instagram: f.contact_instagram || null,
    website_url: f.website_url || null,
    checkin_time: f.checkin_time || null,
    checkout_time: f.checkout_time || null,
    cancellation_policy: f.cancellation_policy || null,
    min_age: num(f.min_age),
    smoking_allowed: f.smoking_allowed === '' ? null : f.smoking_allowed === 'true',
    deposit_required: !!f.deposit_required,
    deposit_note: f.deposit_note || null,
    payment_methods: f.payment_methods.split(',').map((s) => s.trim()).filter(Boolean),
    deposit_amount: num(f.deposit_amount),
    deposit_percent: num(f.deposit_percent),
    advance_booking_required: !!f.advance_booking_required,
    advance_booking_days: num(f.advance_booking_days),
    price_conditions: f.price_conditions || null,
    recommended_reason: f.recommended_reason || null,
    tags: f.tags.split(',').map((s) => s.trim()).filter(Boolean),
    amenity_codes: f.amenity_codes,
    status: f.status,
    last_verified_at: f.last_verified_at || null,
    source_note: f.source_note || null,
    is_featured: !!f.is_featured,
  }
}

async function onSubmit() {
  saving.value = true
  errorMessage.value = null
  savedNote.value = null
  try {
    const payload = buildPayload()
    if (isEdit.value) {
      await updateAccommodation(props.id, payload)
    } else {
      const created = await createAccommodation(payload)
      router.replace({ name: 'admin-accommodation-edit', params: { id: created.id } })
    }
    savedNote.value = 'บันทึกแล้ว'
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    saving.value = false
  }
}

function toggleAmenity(code) {
  const i = form.value.amenity_codes.indexOf(code)
  if (i === -1) form.value.amenity_codes.push(code)
  else form.value.amenity_codes.splice(i, 1)
}

const inputCls = 'w-full rounded-lg border border-line px-3 py-2 text-[14px] outline-none focus:border-indigo-400'
const labelCls = 'mb-1 block text-[12.5px] font-semibold text-ink-soft'
</script>

<template>
  <div>
    <div class="mb-5 flex items-center justify-between">
      <h1 class="text-[22px] font-bold text-ink">{{ isEdit ? 'แก้ไขที่พัก' : 'เพิ่มที่พักใหม่' }}</h1>
      <RouterLink :to="{ name: 'admin-accommodations' }" class="text-[13.5px] font-semibold text-ink-faint hover:text-indigo-700">← กลับไปรายการ</RouterLink>
    </div>

    <div v-if="loading" class="rounded-xl border border-dashed border-line bg-white p-10 text-center text-ink-faint">กำลังโหลด...</div>

    <form v-else class="flex flex-col gap-6" @submit.prevent="onSubmit">
      <p v-if="errorMessage" class="rounded-lg bg-red-50 px-3.5 py-2.5 text-[13.5px] text-red-700">{{ errorMessage }}</p>
      <p v-if="savedNote" class="rounded-lg bg-emerald-50 px-3.5 py-2.5 text-[13.5px] text-emerald-700">{{ savedNote }}</p>

      <!-- basic -->
      <section class="rounded-xl border border-line bg-white p-5">
        <h2 class="mb-4 text-[15px] font-bold text-ink">ข้อมูลพื้นฐาน</h2>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div><label :class="labelCls">ชื่อที่พัก *</label><input v-model="form.name" required :class="inputCls" /></div>
          <div><label :class="labelCls">ราคาเริ่มต้น (บาท/คืน) *</label><input v-model="form.price_per_night" type="number" min="0" required :class="inputCls" /></div>
          <div>
            <label :class="labelCls">ประเภทที่พัก *</label>
            <select v-model="form.type_code" required :class="inputCls">
              <option value="" disabled>เลือกประเภท</option>
              <option v-for="t in accommodationTypes" :key="t.code" :value="t.code">{{ t.key }}</option>
            </select>
          </div>
          <div>
            <label :class="labelCls">อำเภอ *</label>
            <select v-model="form.district_name" required :class="inputCls">
              <option value="" disabled>เลือกอำเภอ</option>
              <option v-for="d in districts" :key="d.key" :value="d.key">{{ d.key }}</option>
            </select>
          </div>
          <div>
            <label :class="labelCls">สถานะ *</label>
            <select v-model="form.status" required :class="inputCls">
              <option value="draft">ฉบับร่าง</option>
              <option value="pending_review">รอตรวจสอบ</option>
              <option value="published">เผยแพร่</option>
              <option value="closed">ปิดให้บริการ</option>
            </select>
          </div>
          <div><label :class="labelCls">เหตุผลที่แนะนำ</label><input v-model="form.recommended_reason" :class="inputCls" /></div>
          <div class="flex items-center gap-2 pt-6">
            <input v-model="form.is_featured" type="checkbox" id="is_featured" />
            <label for="is_featured" class="text-[13.5px] font-semibold text-ink">แสดงในหน้าแรก "ที่พักน่าสนใจในพิษณุโลก"</label>
          </div>
        </div>
      </section>

      <!-- description / location -->
      <section class="rounded-xl border border-line bg-white p-5">
        <h2 class="mb-4 text-[15px] font-bold text-ink">คำอธิบายและที่ตั้ง</h2>
        <div class="flex flex-col gap-4">
          <div><label :class="labelCls">คำอธิบาย</label><textarea v-model="form.description" rows="3" :class="inputCls"></textarea></div>
          <div><label :class="labelCls">ที่อยู่</label><input v-model="form.address" :class="inputCls" /></div>
          <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div><label :class="labelCls">Latitude</label><input v-model="form.latitude" type="number" step="0.0000001" :class="inputCls" /></div>
            <div><label :class="labelCls">Longitude</label><input v-model="form.longitude" type="number" step="0.0000001" :class="inputCls" /></div>
            <div><label :class="labelCls">ระยะจาก landmark (กม.)</label><input v-model="form.landmark_distance_km" type="number" step="0.1" :class="inputCls" /></div>
            <div><label :class="labelCls">ลิงก์ Google Maps</label><input v-model="form.google_maps_url" :class="inputCls" /></div>
          </div>
        </div>
      </section>

      <!-- contact -->
      <section class="rounded-xl border border-line bg-white p-5">
        <h2 class="mb-4 text-[15px] font-bold text-ink">ช่องทางติดต่อ</h2>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div><label :class="labelCls">โทรศัพท์</label><input v-model="form.phone" :class="inputCls" /></div>
          <div><label :class="labelCls">LINE</label><input v-model="form.contact_line" :class="inputCls" /></div>
          <div><label :class="labelCls">Facebook</label><input v-model="form.contact_facebook" :class="inputCls" /></div>
          <div><label :class="labelCls">Instagram</label><input v-model="form.contact_instagram" :class="inputCls" /></div>
          <div><label :class="labelCls">เว็บไซต์</label><input v-model="form.website_url" :class="inputCls" /></div>
        </div>
      </section>

      <!-- policies -->
      <section class="rounded-xl border border-line bg-white p-5">
        <h2 class="mb-4 text-[15px] font-bold text-ink">นโยบายและเงื่อนไข</h2>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div><label :class="labelCls">เวลาเช็คอิน</label><input v-model="form.checkin_time" placeholder="14:00" :class="inputCls" /></div>
          <div><label :class="labelCls">เวลาเช็คเอาต์</label><input v-model="form.checkout_time" placeholder="12:00" :class="inputCls" /></div>
          <div class="sm:col-span-2"><label :class="labelCls">นโยบายการยกเลิก/คืนเงิน</label><textarea v-model="form.cancellation_policy" rows="2" :class="inputCls"></textarea></div>
          <div><label :class="labelCls">อายุขั้นต่ำผู้เช็คอิน</label><input v-model="form.min_age" type="number" min="0" :class="inputCls" /></div>
          <div>
            <label :class="labelCls">สูบบุหรี่ได้ไหม</label>
            <select v-model="form.smoking_allowed" :class="inputCls">
              <option value="">ไม่ระบุ</option>
              <option value="true">ได้</option>
              <option value="false">ไม่ได้</option>
            </select>
          </div>
          <div><label :class="labelCls">วิธีชำระเงิน (คั่นด้วย ,)</label><input v-model="form.payment_methods" placeholder="เงินสด, โอนธนาคาร" :class="inputCls" /></div>
          <div class="flex items-center gap-2 pt-6"><input v-model="form.deposit_required" type="checkbox" id="dep" /><label for="dep" class="text-[13.5px] font-semibold text-ink">ต้องวางเงินมัดจำ</label></div>
          <div><label :class="labelCls">จำนวนเงินมัดจำ (บาท)</label><input v-model="form.deposit_amount" type="number" min="0" :class="inputCls" /></div>
          <div><label :class="labelCls">มัดจำ (% ของยอดจอง)</label><input v-model="form.deposit_percent" type="number" min="0" max="100" :class="inputCls" /></div>
          <div class="sm:col-span-2"><label :class="labelCls">รายละเอียดมัดจำ</label><input v-model="form.deposit_note" :class="inputCls" /></div>
          <div class="flex items-center gap-2 pt-6"><input v-model="form.advance_booking_required" type="checkbox" id="adv" /><label for="adv" class="text-[13.5px] font-semibold text-ink">ต้องจองล่วงหน้า</label></div>
          <div><label :class="labelCls">จองล่วงหน้าอย่างน้อย (วัน)</label><input v-model="form.advance_booking_days" type="number" min="0" :class="inputCls" /></div>
          <div class="sm:col-span-2"><label :class="labelCls">เงื่อนไขราคาเพิ่มเติม</label><textarea v-model="form.price_conditions" rows="2" :class="inputCls"></textarea></div>
        </div>
      </section>

      <!-- amenities -->
      <section class="rounded-xl border border-line bg-white p-5">
        <h2 class="mb-4 text-[15px] font-bold text-ink">สิ่งอำนวยความสะดวก</h2>
        <div class="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4">
          <label v-for="a in amenities" :key="a.key" class="flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-[13px] font-medium text-ink-soft">
            <input type="checkbox" :checked="form.amenity_codes.includes(a.key)" @change="toggleAmenity(a.key)" />
            {{ a.label }}
          </label>
        </div>
      </section>

      <!-- accommodation-wide gallery — separate from room-type galleries;
      needs a real accommodation_id, so it only appears once one exists -->
      <section v-if="isEdit" class="rounded-xl border border-line bg-white p-5">
        <AdminImageManager
          group="accommodation"
          :owner-id="id"
          title="รูปภาพรวมของที่พัก"
          empty-text="ยังไม่มีรูปภาพรวมของที่พัก"
        />
      </section>
      <p v-else class="rounded-xl border border-dashed border-line bg-white p-4 text-center text-[13px] text-ink-faint">
        บันทึกที่พักนี้ก่อน จึงจะเพิ่มรูปภาพรวมของที่พักได้
      </p>

      <!-- room types — only meaningful once the accommodation exists -->
      <section v-if="isEdit" class="rounded-xl border border-line bg-white p-5">
        <h2 class="mb-4 text-[15px] font-bold text-ink">ประเภทห้องพัก</h2>
        <AdminRoomTypeEditor :accommodation-id="id" />
      </section>
      <p v-else class="rounded-xl border border-dashed border-line bg-white p-4 text-center text-[13px] text-ink-faint">
        บันทึกที่พักนี้ก่อน จึงจะเพิ่มประเภทห้องพักได้
      </p>

      <!-- tags / verification -->
      <section class="rounded-xl border border-line bg-white p-5">
        <h2 class="mb-4 text-[15px] font-bold text-ink">แท็ก และการตรวจสอบข้อมูล</h2>
        <div class="flex flex-col gap-4">
          <div><label :class="labelCls">แท็ก (คั่นด้วย ,)</label><input v-model="form.tags" placeholder="ริมน้ำ, เงียบสงบ" :class="inputCls" /></div>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div><label :class="labelCls">ตรวจสอบข้อมูลล่าสุดเมื่อ</label><input v-model="form.last_verified_at" type="date" :class="inputCls" /></div>
            <div><label :class="labelCls">แหล่งข้อมูล/ลิงก์อ้างอิง</label><input v-model="form.source_note" :class="inputCls" /></div>
          </div>
        </div>
      </section>

      <div class="flex justify-end gap-3">
        <RouterLink :to="{ name: 'admin-accommodations' }" class="flex min-h-[44px] items-center rounded-xl border border-line px-6 text-[14.5px] font-semibold text-ink-soft hover:bg-pagebg">ยกเลิก</RouterLink>
        <button type="submit" :disabled="saving" class="min-h-[44px] rounded-xl bg-indigo-600 px-8 text-[14.5px] font-semibold text-white shadow hover:brightness-105 disabled:opacity-60">
          {{ saving ? 'กำลังบันทึก...' : 'บันทึก' }}
        </button>
      </div>
    </form>
  </div>
</template>
