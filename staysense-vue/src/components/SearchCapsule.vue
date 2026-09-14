<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { fetchSearchSuggestions } from '../api/suggestions'
import { useSearchContext } from '../composables/useSearchContext'

const props = defineProps({
  placeholder: { type: String, default: 'ลองค้นหาที่พัก...' },
  modelValue: { type: String, default: '' },
  // HotelsView's own results-search box also uses this component (spec §1:
  // suggestions should appear wherever the search box appears) — this flag
  // exists only so a future non-search usage could opt out.
  enableSuggestions: { type: Boolean, default: true },
})
const emit = defineEmits(['update:modelValue', 'search'])

const router = useRouter()
const { setContext } = useSearchContext()

const localValue = ref(props.modelValue)
// keep the visible input in sync when a parent sets the query programmatically
// (example chips, near-me detection, "ค้นหาจากสถานที่สำคัญ", etc.) — not just
// when the user types into this box themselves.
watch(
  () => props.modelValue,
  (v) => {
    if (v !== localValue.value) localValue.value = v
  }
)

const open = ref(false)
const loading = ref(false)
const suggestions = ref(null)
const highlightIndex = ref(-1)
let debounceTimer = null
let requestSeq = 0

const rows = computed(() => {
  if (!suggestions.value) return []
  const out = []
  for (const text of suggestions.value.querySuggestions || []) out.push({ kind: 'query', text })
  for (const poi of suggestions.value.poiSuggestions || []) out.push({ kind: 'poi', poi })
  for (const acc of suggestions.value.accommodationSuggestions || []) out.push({ kind: 'acc', acc })
  return out
})

function formatKm(km) {
  if (km < 1) return `${Math.round(km * 1000)} เมตร`
  return `${Math.round(km * 10) / 10} กม.`
}

function scheduleFetch(q) {
  clearTimeout(debounceTimer)
  requestSeq++ // invalidate any in-flight request from a previous keystroke
  if (!props.enableSuggestions || q.trim().length < 2) {
    loading.value = false
    suggestions.value = null
    open.value = false
    return
  }
  loading.value = true
  debounceTimer = setTimeout(() => runFetch(q), 350)
}

async function runFetch(q) {
  const seq = requestSeq
  try {
    const result = await fetchSearchSuggestions(q)
    if (seq !== requestSeq) return // a newer query has since been typed — drop this stale response
    suggestions.value = result
    highlightIndex.value = -1
    const hasAny =
      result.querySuggestions?.length || result.poiSuggestions?.length || result.accommodationSuggestions?.length
    open.value = !!hasAny
  } catch {
    if (seq === requestSeq) {
      suggestions.value = null
      open.value = false
    }
  } finally {
    if (seq === requestSeq) loading.value = false
  }
}

// Deliberately does NOT emit `update:modelValue` here — this box's parent
// (HotelsView) reactively re-runs a real, history-logging search whenever
// its bound query changes, so propagating every keystroke upstream would
// mean every keystroke fires a search and writes a search_logs row. Only an
// actual submit (Enter / button / picking a suggestion) may update the
// parent's copy — see submit() below (spec §3/§16).
function onInput(e) {
  localValue.value = e.target.value
  scheduleFetch(localValue.value)
}

function closeDropdown() {
  open.value = false
  highlightIndex.value = -1
}

function submit(text) {
  const value = text ?? localValue.value
  closeDropdown()
  emit('update:modelValue', value)
  emit('search', value)
}

function goToAccommodation(acc) {
  const q = localValue.value.trim()
  const matchReasons = []
  if (acc.matchedPoiName && acc.distanceKm != null) {
    matchReasons.push({ type: 'poi_match', message: `ใกล้${acc.matchedPoiName}ประมาณ ${formatKm(acc.distanceKm)}` })
  }
  // carry the query (and whatever reason we already know) as search context
  // even though the user never actually opened the full results page (§1/§9)
  setContext({
    originalQuery: q,
    normalizedQuery: suggestions.value?.normalizedQuery || q,
    interpretedAs: suggestions.value?.interpretedAs || null,
    detectedFilters: [],
    confidence: null,
    corrections: [],
    items: matchReasons.length ? [{ id: acc.id, matchReasons }] : [],
  })
  closeDropdown()
  emit('update:modelValue', q)
  router.push({ path: `/accommodations/${acc.id}`, query: q ? { q } : {} })
}

function selectRow(row) {
  if (!row) {
    submit()
    return
  }
  if (row.kind === 'query') {
    localValue.value = row.text
    submit(row.text)
  } else if (row.kind === 'poi') {
    const text = `ใกล้${row.poi.name}`
    localValue.value = text
    submit(text)
  } else if (row.kind === 'acc') {
    goToAccommodation(row.acc)
  }
}

function onKeydown(e) {
  if (e.key === 'Enter') {
    if (open.value && highlightIndex.value >= 0) {
      e.preventDefault()
      selectRow(rows.value[highlightIndex.value])
    } else {
      submit()
    }
  } else if (e.key === 'ArrowDown') {
    if (!open.value) return
    e.preventDefault()
    highlightIndex.value = Math.min(highlightIndex.value + 1, rows.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    if (!open.value) return
    e.preventDefault()
    highlightIndex.value = Math.max(highlightIndex.value - 1, -1)
  } else if (e.key === 'Escape') {
    closeDropdown()
  }
}

function onFocus() {
  if (suggestions.value && localValue.value.trim().length >= 2) {
    const hasAny =
      suggestions.value.querySuggestions?.length ||
      suggestions.value.poiSuggestions?.length ||
      suggestions.value.accommodationSuggestions?.length
    if (hasAny) open.value = true
  }
}
function onBlur() {
  // small delay so a click on a dropdown row registers before it closes
  setTimeout(() => closeDropdown(), 150)
}

onBeforeUnmount(() => clearTimeout(debounceTimer))
</script>

<template>
  <div class="relative min-w-0 flex-1">
    <div
      class="flex items-stretch overflow-hidden rounded-xl border-[1.5px] border-line bg-pagebg transition-colors focus-within:border-indigo-500 focus-within:bg-white focus-within:ring-4 focus-within:ring-indigo-100"
    >
      <div class="flex min-w-0 flex-1 items-center gap-2.5 px-4 py-3">
        <svg viewBox="0 0 24 24" class="h-[18px] w-[18px] flex-shrink-0 text-ink-faint" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input
          :value="localValue"
          @input="onInput"
          @keydown="onKeydown"
          @focus="onFocus"
          @blur="onBlur"
          type="text"
          role="combobox"
          aria-autocomplete="list"
          :aria-expanded="open"
          autocomplete="off"
          :placeholder="placeholder"
          class="w-full min-w-0 border-none bg-transparent text-[14.5px] text-ink outline-none placeholder:text-ink-faint"
        />
      </div>
      <button
        @click="submit()"
        class="flex flex-shrink-0 items-center gap-2 bg-gradient-to-b from-indigo-600 to-indigo-700 px-6 py-3 text-[14.5px] font-bold text-white transition hover:brightness-[1.06]"
      >
        <svg viewBox="0 0 24 24" class="h-[18px] w-[18px]" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        ค้นหาที่พัก
      </button>
    </div>

    <div
      v-if="open"
      class="absolute left-0 right-0 top-[calc(100%+8px)] z-40 max-h-[70vh] overflow-y-auto rounded-xl border-[1.5px] border-[#DCD8F7] bg-white p-2 text-left shadow-xl"
    >
      <div v-if="loading" class="flex items-center gap-2 px-3 py-3 text-[13px] font-semibold text-ink-faint">
        <svg viewBox="0 0 24 24" class="h-4 w-4 animate-spin text-indigo-500" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-9-9" /></svg>
        กำลังค้นหา...
      </div>

      <template v-else>
        <div v-if="suggestions?.querySuggestions?.length" class="mb-1">
          <p class="px-3 pb-1 pt-1.5 text-[11px] font-bold uppercase tracking-wide text-ink-faint">คำค้นที่แนะนำ</p>
          <button
            v-for="(text, i) in suggestions.querySuggestions"
            :key="'q' + i"
            type="button"
            @mousedown.prevent="selectRow({ kind: 'query', text })"
            @mouseenter="highlightIndex = rows.findIndex((r) => r.kind === 'query' && r.text === text)"
            class="flex w-full items-center gap-2.5 rounded-lg border-l-[3px] px-3 py-2.5 text-left text-[13.5px] font-semibold transition-colors"
            :class="rows[highlightIndex]?.kind === 'query' && rows[highlightIndex]?.text === text ? 'border-indigo-600 bg-indigo-50 text-indigo-800' : 'border-transparent text-ink-soft hover:border-indigo-200 hover:bg-indigo-50/60'"
          >
            <svg viewBox="0 0 24 24" class="h-4 w-4 flex-shrink-0 text-ink-faint" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
            <span class="truncate">{{ text }}</span>
          </button>
        </div>

        <div v-if="suggestions?.poiSuggestions?.length" class="mb-1 border-t border-line pt-1">
          <p class="px-3 pb-1 pt-1.5 text-[11px] font-bold uppercase tracking-wide text-ink-faint">สถานที่สำคัญ</p>
          <button
            v-for="(poi, i) in suggestions.poiSuggestions"
            :key="'p' + i"
            type="button"
            @mousedown.prevent="selectRow({ kind: 'poi', poi })"
            @mouseenter="highlightIndex = rows.findIndex((r) => r.kind === 'poi' && r.poi === poi)"
            class="flex w-full items-center gap-2.5 rounded-lg border-l-[3px] px-3 py-2.5 text-left text-[13.5px] font-semibold transition-colors"
            :class="rows[highlightIndex]?.kind === 'poi' && rows[highlightIndex]?.poi === poi ? 'border-indigo-600 bg-indigo-50 text-indigo-800' : 'border-transparent text-ink-soft hover:border-indigo-200 hover:bg-indigo-50/60'"
          >
            <svg viewBox="0 0 24 24" class="h-4 w-4 flex-shrink-0 text-ink-faint" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s-7-7.5-7-12a7 7 0 0 1 14 0c0 4.5-7 12-7 12z" /><circle cx="12" cy="9" r="2.4" /></svg>
            <span class="truncate">{{ poi.name }}</span>
          </button>
        </div>

        <div v-if="suggestions?.accommodationSuggestions?.length" class="border-t border-line pt-1">
          <p class="px-3 pb-1 pt-1.5 text-[11px] font-bold uppercase tracking-wide text-ink-faint">ที่พักที่เกี่ยวข้อง</p>
          <button
            v-for="(acc, i) in suggestions.accommodationSuggestions"
            :key="'a' + i"
            type="button"
            @mousedown.prevent="selectRow({ kind: 'acc', acc })"
            @mouseenter="highlightIndex = rows.findIndex((r) => r.kind === 'acc' && r.acc === acc)"
            class="flex w-full items-start gap-2.5 rounded-lg border-l-[3px] px-3 py-2.5 text-left transition-colors"
            :class="rows[highlightIndex]?.kind === 'acc' && rows[highlightIndex]?.acc === acc ? 'border-indigo-600 bg-indigo-50' : 'border-transparent hover:border-indigo-200 hover:bg-indigo-50/60'"
          >
            <svg viewBox="0 0 24 24" class="mt-0.5 h-4 w-4 flex-shrink-0 text-ink-faint" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="1.5" /><path d="M8 21V5a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v16" /></svg>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-[13.5px] font-bold text-ink">{{ acc.name }}</span>
              <span class="block text-[11.5px] font-semibold text-ink-faint">{{ acc.type }} · อำเภอ{{ acc.district }}</span>
              <span v-if="acc.matchedPoiName && acc.distanceKm != null" class="mt-0.5 block text-[11.5px] font-bold text-indigo-700">
                ใกล้{{ acc.matchedPoiName }} {{ formatKm(acc.distanceKm) }}
              </span>
            </span>
          </button>
        </div>
      </template>
    </div>
  </div>
</template>
