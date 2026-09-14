<script setup>
import { RouterLink, RouterView } from 'vue-router'
import { useAuth } from '../../composables/useAuth'

const { user } = useAuth()

// Scope 4.1–4.6 from the admin spec, all built. 4.2 (room types) and 4.3
// (images) don't get their own nav item/page — they're managed inline from
// within each accommodation's edit form (AdminAccommodationFormView) since
// they only make sense in that context.
const NAV = [
  { label: 'ข้อมูลที่พัก', to: { name: 'admin-accommodations' }, done: true },
  { label: 'ประเภทห้องพัก / รูปภาพ', done: true, hint: '(ในหน้าที่พัก)' },
  { label: 'สิ่งอำนวยความสะดวก', to: { name: 'admin-amenities' }, done: true },
  { label: 'สถานที่สำคัญ', to: { name: 'admin-places' }, done: true },
  { label: 'สมาชิกและสถิติ', to: { name: 'admin-members' }, done: true },
]
</script>

<template>
  <div class="min-h-[calc(100vh-70px)] bg-pagebg">
    <div class="mx-auto flex max-w-[1280px] gap-6 px-6 py-6">
      <!-- sidebar -->
      <aside class="w-[220px] flex-shrink-0">
        <div class="mb-4 rounded-xl border border-line bg-white p-4">
          <div class="text-[12px] font-semibold text-ink-faint">ผู้ดูแลระบบ</div>
          <div class="mt-0.5 truncate text-[15px] font-bold text-ink">{{ user?.name }}</div>
        </div>
        <nav class="flex flex-col gap-1 rounded-xl border border-line bg-white p-2">
          <RouterLink
            v-for="item in NAV"
            :key="item.label"
            :to="item.to || '#'"
            class="rounded-lg px-3.5 py-2.5 text-[14px] font-semibold"
            :class="item.to
              ? 'text-ink-soft hover:bg-pagebg hover:text-indigo-700'
              : 'pointer-events-none text-ink-faint/70'"
            active-class="!bg-indigo-50 !text-indigo-700"
          >
            {{ item.label }}
            <span v-if="item.hint" class="ml-1 text-[11px] font-medium text-ink-faint">{{ item.hint }}</span>
            <span v-else-if="!item.done" class="ml-1 text-[11px] font-medium text-ink-faint">(เร็วๆ นี้)</span>
          </RouterLink>
        </nav>
        <RouterLink to="/" class="mt-4 block text-center text-[13px] font-semibold text-ink-faint hover:text-indigo-700">← กลับหน้าเว็บหลัก</RouterLink>
      </aside>

      <!-- content -->
      <main class="min-w-0 flex-1">
        <RouterView />
      </main>
    </div>
  </div>
</template>
