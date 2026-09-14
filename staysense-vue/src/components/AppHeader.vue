<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { useCompare } from '../composables/useCompare'

const router = useRouter()
const { user, isLoggedIn, logout } = useAuth()
const { count: compareCount } = useCompare()

const menuOpen = ref(false)
function onLogout() {
  menuOpen.value = false
  logout()
  router.push('/')
}
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-line bg-white">
    <div class="mx-auto flex max-w-[1320px] items-center justify-between gap-6 px-8 py-3.5">
      <RouterLink to="/" class="flex items-center gap-2.5">
        <svg viewBox="0 0 28 34" class="h-[42px] w-[34px] flex-shrink-0" fill="none">
          <defs>
            <linearGradient id="pinGrad" x1="4" y1="0" x2="24" y2="30" gradientUnits="userSpaceOnUse">
              <stop offset="0" stop-color="#3B2F91" />
              <stop offset="1" stop-color="#5B4FE8" />
            </linearGradient>
          </defs>
          <path
            d="M14 0C6.8 0 1 5.7 1 12.7 1 22 14 34 14 34s13-12 13-21.3C27 5.7 21.2 0 14 0z"
            fill="url(#pinGrad)"
          />
          <path d="M14 8.2 7.8 13v9.4h4.1v-5.6h4.2v5.6h4.1V13z" fill="#fff" />
        </svg>
        <div>
          <div class="text-[19px] font-extrabold leading-tight">
            <span class="text-[#211D3A]">Stay</span><span class="text-indigo-600">Sense</span>
          </div>
          <div class="text-[10.5px] font-bold tracking-[2.5px] text-indigo-600">PHITSANULOK</div>
        </div>
      </RouterLink>

      <nav class="hidden items-center gap-8 md:flex">
        <RouterLink
          to="/"
          class="border-b-2 border-transparent pb-1.5 text-[15px] font-semibold text-ink-soft hover:text-indigo-700"
          active-class="!border-indigo-600 !text-indigo-700"
          >หน้าแรก</RouterLink
        >
        <RouterLink
          to="/hotels"
          class="border-b-2 border-transparent pb-1.5 text-[15px] font-semibold text-ink-soft hover:text-indigo-700"
          active-class="!border-indigo-600 !text-indigo-700"
          >ค้นหาที่พัก</RouterLink
        >
        <RouterLink
          v-if="isLoggedIn"
          to="/favorites"
          class="border-b-2 border-transparent pb-1.5 text-[15px] font-semibold text-ink-soft hover:text-indigo-700"
          active-class="!border-indigo-600 !text-indigo-700"
          >รายการโปรด</RouterLink
        >
        <RouterLink
          to="/compare"
          class="relative border-b-2 border-transparent pb-1.5 text-[15px] font-semibold text-ink-soft hover:text-indigo-700"
          active-class="!border-indigo-600 !text-indigo-700"
        >
          เปรียบเทียบ
          <span v-if="compareCount > 0" class="absolute -right-3.5 -top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">{{ compareCount }}</span>
        </RouterLink>
        <a href="#" class="text-[15px] font-semibold text-ink-soft hover:text-indigo-700">เกี่ยวกับระบบ</a>
      </nav>

      <RouterLink
        v-if="!isLoggedIn"
        to="/login"
        class="flex items-center gap-2 rounded-full border-[1.5px] border-[#D8D5F5] bg-white px-[18px] py-2.5 text-sm font-bold text-indigo-700 hover:bg-indigo-50"
      >
        <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
        เข้าสู่ระบบ
      </RouterLink>

      <div v-else class="relative">
        <button
          @click="menuOpen = !menuOpen"
          class="flex items-center gap-2 rounded-full border-[1.5px] border-[#D8D5F5] bg-white px-4 py-2 text-sm font-bold text-indigo-700 hover:bg-indigo-50"
        >
          <span class="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-100 text-[13px] font-extrabold text-indigo-700">
            {{ (user?.name || 'U').charAt(0) }}
          </span>
          <span class="max-w-[120px] truncate">{{ user?.name || 'สมาชิก' }}</span>
          <svg viewBox="0 0 24 24" class="h-3.5 w-3.5 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="m6 9 6 6 6-6" /></svg>
        </button>

        <div
          v-if="menuOpen"
          class="absolute right-0 top-full z-10 mt-2 w-48 rounded-xl border border-line bg-white p-1.5 shadow-card"
          @click="menuOpen = false"
        >
          <RouterLink to="/favorites" class="block rounded-lg px-3.5 py-2.5 text-[14px] font-semibold text-ink-soft hover:bg-pagebg hover:text-indigo-700">รายการโปรด</RouterLink>
          <RouterLink to="/privacy" class="block rounded-lg px-3.5 py-2.5 text-[14px] font-semibold text-ink-soft hover:bg-pagebg hover:text-indigo-700">ความเป็นส่วนตัว</RouterLink>
          <RouterLink v-if="user?.role === 'admin'" to="/admin" class="block rounded-lg px-3.5 py-2.5 text-[14px] font-semibold text-ink-soft hover:bg-pagebg hover:text-indigo-700">จัดการระบบ (Admin)</RouterLink>
          <button @click="onLogout" class="block w-full rounded-lg px-3.5 py-2.5 text-left text-[14px] font-semibold text-red-600 hover:bg-red-50">ออกจากระบบ</button>
        </div>
        <button v-if="menuOpen" class="fixed inset-0 z-[5] cursor-default" @click="menuOpen = false" aria-hidden="true" tabindex="-1"></button>
      </div>
    </div>
  </header>
</template>
