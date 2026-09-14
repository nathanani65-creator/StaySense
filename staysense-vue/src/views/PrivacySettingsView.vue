<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import {
  fetchMyPreferences,
  saveMyPreferences,
  fetchPersonalizationSettings,
  setPersonalizationSettings,
  clearSearchHistory,
  fetchSearchHistorySetting,
  setSearchHistorySetting,
} from '../api/preferences'

const router = useRouter()
const { isLoggedIn } = useAuth()

const loading = ref(true)
const errorMessage = ref(null)
const note = ref(null)

const allowPersonalization = ref(true)
const saveSearchHistory = ref(true)
const hasPreferences = ref(false)
const savingToggle = ref(false)
const savingHistoryToggle = ref(false)
const clearingHistory = ref(false)
const clearingPreferences = ref(false)

async function load() {
  if (!isLoggedIn.value) {
    router.replace({ path: '/login', query: { redirect: '/privacy' } })
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    const [settings, historySetting, pref] = await Promise.all([
      fetchPersonalizationSettings(),
      fetchSearchHistorySetting(),
      fetchMyPreferences(),
    ])
    allowPersonalization.value = settings.allowPersonalization
    saveSearchHistory.value = historySetting.saveSearchHistory
    hasPreferences.value = !!pref
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(isLoggedIn, load)

async function onToggle() {
  savingToggle.value = true
  note.value = null
  try {
    const res = await setPersonalizationSettings(!allowPersonalization.value)
    allowPersonalization.value = res.allowPersonalization
    note.value = allowPersonalization.value
      ? 'เปิดใช้ประวัติการค้นหาเพื่อแนะนำที่พักแล้ว'
      : 'ปิดการใช้ประวัติการค้นหาแล้ว — StaySense จะไม่นำประวัติการค้นหาของคุณมาแนะนำที่พักอีก'
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    savingToggle.value = false
  }
}

async function onToggleSaveHistory() {
  savingHistoryToggle.value = true
  note.value = null
  try {
    const res = await setSearchHistorySetting(!saveSearchHistory.value)
    saveSearchHistory.value = res.saveSearchHistory
    note.value = saveSearchHistory.value
      ? 'เปิดการบันทึกประวัติการค้นหาแล้ว'
      : 'ปิดการบันทึกประวัติการค้นหาแล้ว — การค้นหาครั้งต่อไปจะไม่ถูกบันทึกไว้'
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    savingHistoryToggle.value = false
  }
}

async function onClearHistory() {
  if (!confirm('ต้องการลบประวัติการค้นหาทั้งหมดใช่หรือไม่?')) return
  clearingHistory.value = true
  note.value = null
  try {
    await clearSearchHistory()
    note.value = 'ลบประวัติการค้นหาแล้ว'
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    clearingHistory.value = false
  }
}

async function onClearPreferences() {
  if (!confirm('ต้องการล้างความต้องการที่เคยตั้งไว้ใช่หรือไม่? หน้าแรกจะกลับไปถามความต้องการของคุณใหม่')) return
  clearingPreferences.value = true
  note.value = null
  try {
    await saveMyPreferences({
      type_codes: [], district_names: [], budget_min: null, budget_max: null,
      guest_count: null, amenity_codes: [], atmosphere_codes: [], near_place_categories: [],
    })
    hasPreferences.value = false
    note.value = 'ล้างความต้องการแล้ว'
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    clearingPreferences.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-[720px] px-5 pb-20 pt-6 sm:px-8">
    <h1 class="text-[26px] font-bold text-ink sm:text-[28px]">ความเป็นส่วนตัวและการแนะนำที่พัก</h1>
    <p class="mt-1.5 text-[14.5px] text-ink-soft">จัดการว่า StaySense ใช้ข้อมูลใดของคุณในการแนะนำที่พัก</p>

    <div v-if="loading" class="mt-8 rounded-2xl border border-dashed border-line bg-white p-16 text-center text-ink-soft">กำลังโหลด...</div>

    <div v-else class="mt-8 flex flex-col gap-5">
      <p v-if="errorMessage" class="rounded-lg bg-red-50 px-3.5 py-2.5 text-[13.5px] text-red-700">{{ errorMessage }}</p>
      <p v-if="note" class="rounded-lg bg-emerald-50 px-3.5 py-2.5 text-[13.5px] text-emerald-700">{{ note }}</p>

      <section class="rounded-2xl border border-line bg-white p-5">
        <h2 class="text-[15px] font-bold text-ink">ข้อมูลที่ใช้สร้างคำแนะนำ</h2>
        <p class="mt-1.5 text-[13.5px] leading-relaxed text-ink-soft">
          StaySense ใช้ความต้องการที่คุณกรอกไว้ รายการโปรด ที่พักที่คุณเคยเปิดดู และ (ถ้าคุณอนุญาต) ประวัติการค้นหา
          เพื่อคัดเลือกที่พักในส่วน "ที่พักที่แนะนำสำหรับคุณ" — ไม่มีการนำข้อมูลนี้ไปเปิดเผยให้ผู้ใช้งานรายอื่นเห็น
          และผู้ดูแลระบบเห็นได้เฉพาะสถิติภาพรวม ไม่เห็นประวัติการค้นหาส่วนบุคคลของคุณ
        </p>
      </section>

      <section class="rounded-2xl border border-line bg-white p-5">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-[15px] font-bold text-ink">ใช้ประวัติการค้นหาเพื่อแนะนำที่พัก</h2>
            <p class="mt-1 text-[13px] text-ink-soft">เมื่อปิด StaySense จะไม่นำประวัติการค้นหาของคุณมาใช้แนะนำที่พักอีก (ยังคงแนะนำจากความต้องการที่ตั้งไว้และรายการโปรดได้ตามปกติ)</p>
          </div>
          <button
            type="button"
            role="switch"
            :aria-checked="allowPersonalization"
            :disabled="savingToggle"
            @click="onToggle"
            class="relative h-7 w-12 flex-none rounded-full transition disabled:opacity-60"
            :class="allowPersonalization ? 'bg-indigo-600' : 'bg-line'"
          >
            <span class="absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition" :class="allowPersonalization ? 'left-[22px]' : 'left-0.5'" />
          </button>
        </div>
      </section>

      <section class="rounded-2xl border border-line bg-white p-5">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-[15px] font-bold text-ink">บันทึกประวัติการค้นหา</h2>
            <p class="mt-1 text-[13px] text-ink-soft">
              เมื่อปิด การค้นหาของคุณ (ตอนกด Enter หรือกดปุ่มค้นหา) จะไม่ถูกบันทึกไว้เลย — ไม่ใช่แค่ไม่นำไปแนะนำที่พัก
            </p>
          </div>
          <button
            type="button"
            role="switch"
            :aria-checked="saveSearchHistory"
            :disabled="savingHistoryToggle"
            @click="onToggleSaveHistory"
            class="relative h-7 w-12 flex-none rounded-full transition disabled:opacity-60"
            :class="saveSearchHistory ? 'bg-indigo-600' : 'bg-line'"
          >
            <span class="absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition" :class="saveSearchHistory ? 'left-[22px]' : 'left-0.5'" />
          </button>
        </div>
      </section>

      <section class="rounded-2xl border border-line bg-white p-5">
        <h2 class="text-[15px] font-bold text-ink">ลบประวัติการค้นหา</h2>
        <p class="mt-1 text-[13px] text-ink-soft">ลบประวัติการค้นหาทั้งหมดของคุณออกจากระบบถาวร</p>
        <button
          type="button"
          :disabled="clearingHistory"
          @click="onClearHistory"
          class="mt-3 rounded-xl border border-red-200 px-4 py-2 text-[13.5px] font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60"
        >{{ clearingHistory ? 'กำลังลบ...' : 'ลบประวัติการค้นหา' }}</button>
      </section>

      <section v-if="hasPreferences" class="rounded-2xl border border-line bg-white p-5">
        <h2 class="text-[15px] font-bold text-ink">ปรับความต้องการ</h2>
        <p class="mt-1 text-[13px] text-ink-soft">ล้างความต้องการที่เคยตั้งไว้ — หน้าแรกจะแสดงกล่อง "บอกความต้องการของคุณ" ให้ตั้งใหม่</p>
        <button
          type="button"
          :disabled="clearingPreferences"
          @click="onClearPreferences"
          class="mt-3 rounded-xl border border-line px-4 py-2 text-[13.5px] font-semibold text-ink-soft hover:bg-pagebg disabled:opacity-60"
        >{{ clearingPreferences ? 'กำลังล้าง...' : 'ล้างความต้องการ' }}</button>
      </section>
    </div>
  </div>
</template>
