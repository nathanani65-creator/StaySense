<script setup>
import { ref } from 'vue'

const props = defineProps({
  options: { type: Object, required: true }, // OnboardingOptionsOut
})
const emit = defineEmits(['submit', 'skip'])

const form = ref({
  type_codes: [],
  district_names: [],
  budget_min: '',
  budget_max: '',
  guest_count: '',
  amenity_codes: [],
  atmosphere_codes: [],
  near_place_categories: [],
})

function toggle(list, value) {
  const i = list.indexOf(value)
  if (i === -1) list.push(value)
  else list.splice(i, 1)
}

function onSubmit() {
  emit('submit', {
    type_codes: form.value.type_codes,
    district_names: form.value.district_names,
    budget_min: form.value.budget_min === '' ? null : Number(form.value.budget_min),
    budget_max: form.value.budget_max === '' ? null : Number(form.value.budget_max),
    guest_count: form.value.guest_count === '' ? null : Number(form.value.guest_count),
    amenity_codes: form.value.amenity_codes,
    atmosphere_codes: form.value.atmosphere_codes,
    near_place_categories: form.value.near_place_categories,
  })
}

const chipCls = (active) =>
  active
    ? 'rounded-full border border-indigo-600 bg-indigo-600 px-3.5 py-1.5 text-[13px] font-bold text-white'
    : 'rounded-full border border-line bg-white px-3.5 py-1.5 text-[13px] font-semibold text-ink-soft hover:bg-pagebg'
</script>

<template>
  <section class="mx-auto max-w-[1320px] px-8 py-8">
    <div class="rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50/70 to-white p-6 sm:p-8">
      <div class="mb-1 flex items-center gap-2">
        <svg viewBox="0 0 24 24" class="h-5 w-5 text-indigo-600" fill="currentColor"><path d="M12 2.5l2.9 6.4 6.9.7-5.2 4.8 1.5 6.9L12 17.9l-6.1 3.4 1.5-6.9-5.2-4.8 6.9-.7z" /></svg>
        <h2 class="text-[19.5px] font-extrabold text-ink">{{ options.title }}</h2>
      </div>
      <p class="mb-5 text-[13.5px] text-ink-soft">{{ options.subtitle }}</p>

      <form @submit.prevent="onSubmit" class="flex flex-col gap-5">
        <div>
          <label class="mb-2 block text-[13px] font-bold text-ink">ประเภทที่พักที่สนใจ</label>
          <div class="flex flex-wrap gap-2">
            <button v-for="t in options.typeOptions" :key="t.code" type="button" :class="chipCls(form.type_codes.includes(t.code))" @click="toggle(form.type_codes, t.code)">{{ t.key }}</button>
          </div>
        </div>

        <div>
          <label class="mb-2 block text-[13px] font-bold text-ink">อำเภอที่ต้องการเข้าพัก</label>
          <div class="flex flex-wrap gap-2">
            <button v-for="d in options.districtOptions" :key="d.key" type="button" :class="chipCls(form.district_names.includes(d.key))" @click="toggle(form.district_names, d.key)">{{ d.key }}</button>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label class="mb-1.5 block text-[13px] font-bold text-ink">งบต่ำสุด (บาท/คืน)</label>
            <input v-model="form.budget_min" type="number" min="0" placeholder="ไม่ระบุ" class="w-full rounded-xl border border-line px-3.5 py-2.5 text-[14px] outline-none focus:border-indigo-400" />
          </div>
          <div>
            <label class="mb-1.5 block text-[13px] font-bold text-ink">งบสูงสุด (บาท/คืน)</label>
            <input v-model="form.budget_max" type="number" min="0" placeholder="ไม่ระบุ" class="w-full rounded-xl border border-line px-3.5 py-2.5 text-[14px] outline-none focus:border-indigo-400" />
          </div>
          <div>
            <label class="mb-1.5 block text-[13px] font-bold text-ink">จำนวนผู้เข้าพัก</label>
            <input v-model="form.guest_count" type="number" min="1" placeholder="ไม่ระบุ" class="w-full rounded-xl border border-line px-3.5 py-2.5 text-[14px] outline-none focus:border-indigo-400" />
          </div>
        </div>

        <div>
          <label class="mb-2 block text-[13px] font-bold text-ink">สิ่งอำนวยความสะดวกที่ต้องการ</label>
          <div class="flex flex-wrap gap-2">
            <button v-for="a in options.amenityOptions" :key="a.key" type="button" :class="chipCls(form.amenity_codes.includes(a.key))" @click="toggle(form.amenity_codes, a.key)">{{ a.label }}</button>
          </div>
        </div>

        <div>
          <label class="mb-2 block text-[13px] font-bold text-ink">บรรยากาศที่ชอบ</label>
          <div class="flex flex-wrap gap-2">
            <button v-for="o in options.atmosphereOptions" :key="o.key" type="button" :class="chipCls(form.atmosphere_codes.includes(o.key))" @click="toggle(form.atmosphere_codes, o.key)">{{ o.label }}</button>
          </div>
        </div>

        <div>
          <label class="mb-2 block text-[13px] font-bold text-ink">สถานที่สำคัญที่ต้องการอยู่ใกล้</label>
          <div class="flex flex-wrap gap-2">
            <button v-for="o in options.placeCategoryOptions" :key="o.key" type="button" :class="chipCls(form.near_place_categories.includes(o.key))" @click="toggle(form.near_place_categories, o.key)">{{ o.label }}</button>
          </div>
        </div>

        <div class="mt-1 flex flex-wrap gap-3">
          <button type="submit" class="flex min-h-[44px] items-center rounded-xl bg-indigo-600 px-7 text-[14.5px] font-bold text-white hover:brightness-105">ดูคำแนะนำ</button>
          <button type="button" @click="emit('skip')" class="flex min-h-[44px] items-center rounded-xl border border-line bg-white px-7 text-[14.5px] font-semibold text-ink-soft hover:bg-pagebg">ข้ามไปก่อน</button>
        </div>
      </form>
    </div>
  </section>
</template>
