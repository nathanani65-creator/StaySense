<script setup>
const props = defineProps({
  districts: { type: Array, required: true }, // [{ key, cx, cy, ... }]
  counts: { type: Object, required: true }, // { [districtKey]: number }
  selected: { type: Set, required: true },
})
const emit = defineEmits(['select'])

const BLOBS = {
  ชาติตระการ: 'M40,60 L170,50 L190,150 L120,180 L50,150 Z',
  นครไทย: 'M50,155 L185,155 L200,270 L150,300 L60,275 Z',
  พรหมพิราม: 'M195,150 L340,150 L350,240 L250,260 L200,250 Z',
  วัดโบสถ์: 'M65,280 L195,255 L210,340 L150,390 L80,380 Z',
  บางระกำ: 'M10,340 L150,350 L165,440 L85,480 L15,440 Z',
  เมืองพิษณุโลก: 'M215,255 L350,245 L360,330 L340,380 L250,400 L200,345 Z',
  บางกระทุ่ม: 'M355,245 L400,270 L410,380 L360,400 L340,335 Z',
  วังทอง: 'M215,345 L340,340 L350,410 L280,460 L215,430 Z',
  เนินมะปราง: 'M285,415 L400,395 L410,480 L340,500 L280,470 Z',
}

const isActive = (key) => props.selected.size === 0 || props.selected.has(key)

function onPinClick(key) {
  emit('select', key)
}
</script>

<template>
  <div class="relative h-full min-h-[520px] overflow-hidden rounded-2xl border border-line bg-gradient-to-br from-[#EDEBFB] to-[#F7F6FE] shadow-card">
    <div class="absolute left-3.5 top-3.5 flex items-center gap-1.5 rounded-lg border border-line bg-white px-3 py-2 text-[11.5px] text-ink-soft shadow-card">
      <span class="h-2.5 w-2.5 rounded-full bg-indigo-600"></span> จำนวนโรงแรมต่ออำเภอ
    </div>
    <button
      @click="emit('select', null)"
      class="absolute bottom-3.5 right-3.5 flex items-center gap-1.5 rounded-full border border-line bg-white px-4 py-2.5 text-xs font-bold text-ink shadow-card"
    >
      <svg viewBox="0 0 24 24" class="h-3.5 w-3.5 text-indigo-600" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5" />
      </svg>
      แสดงทั้งหมด
    </button>

    <svg viewBox="0 0 420 520" class="block h-full w-full">
      <g>
        <path
          v-for="d in districts"
          :key="d.key"
          :d="BLOBS[d.key]"
          class="cursor-pointer stroke-[#C9C5EE] stroke-[1.4] transition-colors hover:fill-[#CDC9F2]"
          :class="isActive(d.key) ? 'fill-[#C7C2F5]' : 'fill-[#DEDBF5]'"
          @click="onPinClick(d.key)"
        />
      </g>
      <g>
        <text v-for="d in districts" :key="d.key + '-label'" :x="d.cx" :y="d.cy + 34" text-anchor="middle" class="fill-ink-soft text-[11.5px] font-bold">
          {{ d.key }}
        </text>
      </g>
      <g>
        <g
          v-for="d in districts"
          :key="d.key + '-pin'"
          class="cursor-pointer"
          :transform="`translate(${d.cx},${d.cy})`"
          @click="onPinClick(d.key)"
        >
          <ellipse cx="0" cy="20" rx="10" ry="3" class="fill-[#312A6B]/18" />
          <path
            d="M0,-20 C10,-20 17,-13 17,-4 C17,7 0,20 0,20 C0,20 -17,7 -17,-4 C-17,-13 -10,-20 0,-20 Z"
            :class="isActive(d.key) ? 'fill-indigo-600' : 'fill-[#B7B3E8]'"
            stroke="#fff"
            stroke-width="2"
          />
          <text x="0" y="-2" text-anchor="middle" class="fill-white text-[11px] font-extrabold">{{ counts[d.key] || 0 }}</text>
        </g>
      </g>
    </svg>
  </div>
</template>
