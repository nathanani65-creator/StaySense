<script setup>
import AppHeader from './components/AppHeader.vue'
import CompareBar from './components/CompareBar.vue'
</script>

<template>
  <div class="min-h-screen bg-pagebg font-sans text-ink antialiased">
    <AppHeader />
    <router-view />
    <footer class="border-t border-line px-8 py-6 text-center text-xs text-ink-faint">
      © 2026 StaySense Phitsanulok — ค้นหาที่พักทั่วจังหวัดพิษณุโลก ด้วยระบบค้นหาเชิงความหมาย
    </footer>
    <CompareBar />
  </div>
</template>
