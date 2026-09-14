<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const { register } = useAuth()

const name = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref(null)

async function onSubmit() {
  if (password.value.length < 8) {
    errorMessage.value = 'รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร'
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    await register(name.value, email.value, password.value)
    router.push(typeof route.query.redirect === 'string' ? route.query.redirect : '/')
  } catch (e) {
    errorMessage.value = /already registered/i.test(e.message)
      ? 'อีเมลนี้ถูกใช้สมัครสมาชิกไปแล้ว'
      : e.message || 'สมัครสมาชิกไม่สำเร็จ'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex min-h-[70vh] max-w-[440px] flex-col justify-center px-5 py-10">
    <div class="rounded-2xl border border-line bg-white p-7 shadow-card">
      <h1 class="text-[24px] font-bold text-ink">สมัครสมาชิก</h1>
      <p class="mt-1.5 text-[14.5px] text-ink-soft">สมัครสมาชิกฟรี เพื่อบันทึกที่พักที่ชอบและดูประวัติการค้นหา</p>

      <form class="mt-6 flex flex-col gap-4" @submit.prevent="onSubmit">
        <div>
          <label class="mb-1.5 block text-[13.5px] font-semibold text-ink">ชื่อ</label>
          <input
            v-model="name"
            type="text"
            required
            autocomplete="name"
            class="w-full rounded-xl border border-line px-4 py-3 text-[15px] text-ink outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
            placeholder="ชื่อของคุณ"
          />
        </div>
        <div>
          <label class="mb-1.5 block text-[13.5px] font-semibold text-ink">อีเมล</label>
          <input
            v-model="email"
            type="email"
            required
            autocomplete="email"
            class="w-full rounded-xl border border-line px-4 py-3 text-[15px] text-ink outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
            placeholder="you@example.com"
          />
        </div>
        <div>
          <label class="mb-1.5 block text-[13.5px] font-semibold text-ink">รหัสผ่าน</label>
          <input
            v-model="password"
            type="password"
            required
            minlength="8"
            autocomplete="new-password"
            class="w-full rounded-xl border border-line px-4 py-3 text-[15px] text-ink outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
            placeholder="อย่างน้อย 8 ตัวอักษร"
          />
        </div>

        <p v-if="errorMessage" class="rounded-lg bg-red-50 px-3.5 py-2.5 text-[13.5px] text-red-700">{{ errorMessage }}</p>

        <button
          type="submit"
          :disabled="loading"
          class="mt-1 min-h-[46px] w-full rounded-xl bg-indigo-600 text-[15px] font-semibold text-white shadow hover:brightness-105 disabled:opacity-60"
        >{{ loading ? 'กำลังสมัครสมาชิก...' : 'สมัครสมาชิก' }}</button>
      </form>

      <p class="mt-5 text-center text-[14px] text-ink-soft">
        มีบัญชีอยู่แล้ว?
        <RouterLink :to="{ path: '/login', query: route.query }" class="font-semibold text-indigo-600 hover:underline">เข้าสู่ระบบ</RouterLink>
      </p>
    </div>
  </div>
</template>
