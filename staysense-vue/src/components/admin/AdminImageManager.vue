<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  fetchImageCategories,
  fetchAdminAccommodationImages, uploadAccommodationImages, updateAccommodationImage,
  setAccommodationImageCover, deleteAccommodationImage, reorderAccommodationImages,
  fetchAdminRoomTypeImages, uploadRoomTypeImages, updateRoomTypeImage,
  setRoomTypeImageCover, deleteRoomTypeImage, reorderRoomTypeImages,
} from '../../api/images'

const props = defineProps({
  group: { type: String, required: true }, // 'accommodation' | 'room_type'
  ownerId: { type: [String, Number], required: true },
  title: { type: String, required: true },
  emptyText: { type: String, required: true },
})

const isRoom = computed(() => props.group === 'room_type')
const api = computed(() =>
  isRoom.value
    ? {
        list: fetchAdminRoomTypeImages, upload: uploadRoomTypeImages, update: updateRoomTypeImage,
        cover: setRoomTypeImageCover, remove: deleteRoomTypeImage, reorder: reorderRoomTypeImages,
      }
    : {
        list: fetchAdminAccommodationImages, upload: uploadAccommodationImages, update: updateAccommodationImage,
        cover: setAccommodationImageCover, remove: deleteAccommodationImage, reorder: reorderAccommodationImages,
      }
)

const MAX_FILE_MB = 5
const MAX_FILES = 10
const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']

const images = ref([])
const categories = ref([])
const loading = ref(true)
const errorMessage = ref(null)
const statusFilter = ref('all')
const savedNote = ref(null)

const pendingFiles = ref([]) // [{ file, previewUrl }]
const uploadCategory = ref('')
const uploading = ref(false)
const dropActive = ref(false)

const editingId = ref(null)
const editForm = ref({ category: '', caption: '', altText: '', sourceName: '', sourceUrl: '', status: 'published' })
const draggedId = ref(null)

async function load() {
  loading.value = true
  errorMessage.value = null
  try {
    images.value = await api.value.list(props.ownerId)
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const cats = await fetchImageCategories()
    categories.value = isRoom.value ? cats.roomType : cats.accommodation
  } catch {
    categories.value = []
  }
  await load()
})

const visibleImages = computed(() =>
  statusFilter.value === 'all' ? images.value : images.value.filter((i) => i.status === statusFilter.value)
)

function categoryLabel(key) {
  return categories.value.find((c) => c.key === key)?.label || key || '—'
}

function flash(msg) {
  savedNote.value = msg
  setTimeout(() => {
    if (savedNote.value === msg) savedNote.value = null
  }, 2500)
}

/* --------------------------------------------------------------- staging */

function validateFile(file) {
  if (!ALLOWED_TYPES.includes(file.type)) return `"${file.name}" ไม่ใช่ไฟล์ JPG, PNG หรือ WebP`
  if (file.size > MAX_FILE_MB * 1024 * 1024) return `"${file.name}" มีขนาดเกิน ${MAX_FILE_MB} MB`
  return null
}

function stageFiles(fileList) {
  errorMessage.value = null
  const files = Array.from(fileList || [])
  if (pendingFiles.value.length + files.length > MAX_FILES) {
    errorMessage.value = `อัปโหลดได้สูงสุด ${MAX_FILES} รูปต่อครั้ง`
    return
  }
  for (const file of files) {
    const err = validateFile(file)
    if (err) {
      errorMessage.value = err
      continue
    }
    pendingFiles.value.push({ file, previewUrl: URL.createObjectURL(file) })
  }
}

function onFileInput(e) {
  stageFiles(e.target.files)
  e.target.value = ''
}
function onDrop(e) {
  e.preventDefault()
  dropActive.value = false
  stageFiles(e.dataTransfer.files)
}
function removePending(i) {
  URL.revokeObjectURL(pendingFiles.value[i].previewUrl)
  pendingFiles.value.splice(i, 1)
}
function clearStaged() {
  pendingFiles.value.forEach((p) => URL.revokeObjectURL(p.previewUrl))
  pendingFiles.value = []
  uploadCategory.value = ''
}

async function commitUpload() {
  if (!pendingFiles.value.length) return
  uploading.value = true
  errorMessage.value = null
  try {
    images.value = await api.value.upload(props.ownerId, pendingFiles.value.map((p) => p.file), uploadCategory.value || undefined)
    clearStaged()
    flash('อัปโหลดรูปภาพสำเร็จ')
  } catch (e) {
    errorMessage.value = e.message || String(e)
  } finally {
    uploading.value = false
  }
}

/* -------------------------------------------------------------- editing */

function startEdit(img) {
  editingId.value = img.id
  editForm.value = {
    category: img.category || '', caption: img.caption || '', altText: img.altText || '',
    sourceName: img.sourceName || '', sourceUrl: img.sourceUrl || '', status: img.status,
  }
}
function cancelEdit() {
  editingId.value = null
}
async function saveEdit() {
  try {
    const f = editForm.value
    await api.value.update(editingId.value, {
      category: f.category || null, caption: f.caption || null, altText: f.altText || null,
      sourceName: f.sourceName || null, sourceUrl: f.sourceUrl || null, status: f.status,
    })
    editingId.value = null
    await load()
    flash('บันทึกข้อมูลรูปภาพแล้ว')
  } catch (e) {
    errorMessage.value = e.message || String(e)
  }
}

async function onSetCover(img) {
  try {
    await api.value.cover(img.id)
    await load()
    flash('กำหนดรูปหน้าปกแล้ว')
  } catch (e) {
    errorMessage.value = e.message || String(e)
  }
}

async function onDelete(img) {
  if (!confirm('ต้องการลบรูปภาพนี้หรือไม่ การดำเนินการนี้อาจส่งผลต่อรูปภาพที่แสดงบนเว็บไซต์')) return
  try {
    await api.value.remove(img.id)
    await load()
    flash('ลบรูปภาพแล้ว')
  } catch (e) {
    errorMessage.value = e.message || String(e)
  }
}

/* ------------------------------------------------------------- reorder */

async function persistOrder() {
  try {
    await api.value.reorder(props.ownerId, images.value.map((i) => i.id))
    flash('จัดลำดับรูปภาพสำเร็จ')
  } catch (e) {
    errorMessage.value = e.message || String(e)
    await load()
  }
}

function move(i, dir) {
  const j = i + dir
  if (j < 0 || j >= images.value.length) return
  const next = [...images.value]
  ;[next[i], next[j]] = [next[j], next[i]]
  images.value = next
  persistOrder()
}

function onItemDragStart(img) {
  draggedId.value = img.id
}
function onItemDragOver(e) {
  e.preventDefault()
}
function onItemDrop(targetImg) {
  if (draggedId.value == null || draggedId.value === targetImg.id) return
  const from = images.value.findIndex((i) => i.id === draggedId.value)
  const to = images.value.findIndex((i) => i.id === targetImg.id)
  if (from === -1 || to === -1) return
  const next = [...images.value]
  const [moved] = next.splice(from, 1)
  next.splice(to, 0, moved)
  images.value = next
  draggedId.value = null
  persistOrder()
}

const statusLabel = { published: 'เผยแพร่', hidden: 'ซ่อนอยู่', pending: 'รอตรวจสอบ' }
const inputCls = 'w-full rounded-lg border border-line px-2.5 py-1.5 text-[13px] outline-none focus:border-indigo-400'
</script>

<template>
  <div>
    <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h3 class="text-[14.5px] font-bold text-ink">{{ title }}</h3>
      <div class="flex items-center gap-2">
        <select v-model="statusFilter" class="rounded-lg border border-line px-2.5 py-1.5 text-[12.5px]">
          <option value="all">ทุกสถานะ</option>
          <option value="published">เผยแพร่</option>
          <option value="hidden">ซ่อนอยู่</option>
          <option value="pending">รอตรวจสอบ</option>
        </select>
        <transition name="fade">
          <span v-if="savedNote" class="rounded-full bg-green-50 px-2.5 py-1 text-[12px] font-semibold text-green-700">{{ savedNote }}</span>
        </transition>
      </div>
    </div>

    <p v-if="errorMessage" class="mb-3 rounded-lg bg-red-50 px-3.5 py-2.5 text-[13px] text-red-700">{{ errorMessage }}</p>

    <!-- upload dropzone -->
    <div
      class="mb-4 rounded-xl border-2 border-dashed p-5 text-center transition-colors"
      :class="dropActive ? 'border-indigo-400 bg-indigo-50/60' : 'border-line bg-pagebg/40'"
      @dragover.prevent="dropActive = true"
      @dragleave.prevent="dropActive = false"
      @drop="onDrop"
    >
      <p class="mb-2 text-[13px] text-ink-soft">ลากไฟล์มาวางที่นี่ หรือ</p>
      <label class="inline-block cursor-pointer rounded-lg bg-indigo-600 px-4 py-2 text-[13px] font-semibold text-white hover:brightness-105">
        เลือกไฟล์จากเครื่อง
        <input type="file" multiple accept="image/jpeg,image/png,image/webp" class="hidden" @change="onFileInput" />
      </label>
      <p class="mt-2 text-[11.5px] text-ink-faint">JPG, PNG, WebP · ไม่เกิน {{ MAX_FILE_MB }} MB ต่อรูป · สูงสุด {{ MAX_FILES }} รูปต่อครั้ง</p>
    </div>

    <!-- staged previews -->
    <div v-if="pendingFiles.length" class="mb-5 rounded-xl border border-indigo-200 bg-indigo-50/30 p-4">
      <div class="mb-3 flex flex-wrap items-center gap-3">
        <label class="text-[12.5px] font-semibold text-ink-soft">หมวดหมู่ของรูปที่จะอัปโหลด (ใช้กับทุกรูปในชุดนี้)</label>
        <select v-model="uploadCategory" class="rounded-lg border border-line px-2.5 py-1.5 text-[12.5px]">
          <option value="">ไม่ระบุ</option>
          <option v-for="c in categories" :key="c.key" :value="c.key">{{ c.label }}</option>
        </select>
      </div>
      <div class="flex flex-wrap gap-3">
        <div v-for="(p, i) in pendingFiles" :key="i" class="relative h-20 w-28 flex-none overflow-hidden rounded-lg border border-line">
          <img :src="p.previewUrl" class="h-full w-full object-cover" />
          <button type="button" @click="removePending(i)" class="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-black/60 text-[11px] text-white">✕</button>
        </div>
      </div>
      <div class="mt-3 flex gap-2">
        <button type="button" :disabled="uploading" @click="commitUpload" class="rounded-lg bg-indigo-600 px-4 py-2 text-[13px] font-semibold text-white hover:brightness-105 disabled:opacity-60">
          {{ uploading ? 'กำลังอัปโหลด...' : `อัปโหลด ${pendingFiles.length} รูป` }}
        </button>
        <button type="button" @click="clearStaged" class="rounded-lg border border-line px-4 py-2 text-[13px] font-semibold text-ink-soft hover:bg-white">ยกเลิก</button>
      </div>
    </div>

    <div v-if="loading" class="rounded-lg border border-dashed border-line p-6 text-center text-[13px] text-ink-faint">กำลังโหลด...</div>
    <p v-else-if="!images.length" class="rounded-lg border border-dashed border-line p-6 text-center text-[13px] text-ink-faint">{{ emptyText }}</p>
    <p v-else-if="!visibleImages.length" class="rounded-lg border border-dashed border-line p-6 text-center text-[13px] text-ink-faint">ไม่มีรูปภาพในสถานะนี้</p>

    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="(img, i) in visibleImages"
        :key="img.id"
        draggable="true"
        @dragstart="onItemDragStart(img)"
        @dragover="onItemDragOver"
        @drop="onItemDrop(img)"
        class="cursor-move rounded-xl border border-line bg-white p-2.5"
        :class="draggedId === img.id ? 'opacity-50' : ''"
      >
        <div class="relative mb-2 h-32 w-full overflow-hidden rounded-lg bg-pagebg">
          <img :src="img.thumbnailUrl || img.url" class="h-full w-full object-cover" @error="($event.target.style.visibility = 'hidden')" />
          <span v-if="img.isCover" class="absolute left-1.5 top-1.5 rounded-full bg-indigo-600 px-2 py-0.5 text-[10.5px] font-bold text-white">รูปหน้าปก</span>
          <span
            class="absolute right-1.5 top-1.5 rounded-full px-2 py-0.5 text-[10.5px] font-bold"
            :class="img.status === 'published' ? 'bg-green-100 text-green-700' : img.status === 'pending' ? 'bg-amber-100 text-amber-700' : 'bg-pagebg text-ink-faint'"
          >
            {{ statusLabel[img.status] }}
          </span>
        </div>

        <div class="mb-1.5 flex items-center justify-between text-[11.5px] text-ink-faint">
          <span>{{ categoryLabel(img.category) }}</span>
          <span>ลำดับ {{ i + 1 }}</span>
        </div>
        <p class="mb-2 truncate text-[12.5px] text-ink-soft">{{ img.caption || 'ไม่มีคำอธิบาย' }}</p>

        <div v-if="editingId === img.id" class="mb-2 flex flex-col gap-1.5 rounded-lg border border-line bg-pagebg/50 p-2.5">
          <select v-model="editForm.category" :class="inputCls">
            <option value="">ไม่ระบุหมวดหมู่</option>
            <option v-for="c in categories" :key="c.key" :value="c.key">{{ c.label }}</option>
          </select>
          <input v-model="editForm.caption" placeholder="คำอธิบายรูป" :class="inputCls" />
          <input v-model="editForm.altText" placeholder="ข้อความ alt (สำหรับผู้ใช้โปรแกรมอ่านหน้าจอ)" :class="inputCls" />
          <input v-model="editForm.sourceName" placeholder="ชื่อแหล่งที่มา (ถ้ามี)" :class="inputCls" />
          <input v-model="editForm.sourceUrl" placeholder="URL แหล่งที่มา (ถ้ามี)" :class="inputCls" />
          <select v-model="editForm.status" :class="inputCls">
            <option value="published">เผยแพร่</option>
            <option value="hidden">ซ่อน</option>
            <option value="pending">รอตรวจสอบ</option>
          </select>
          <div class="mt-1 flex gap-1.5">
            <button type="button" @click="saveEdit" class="flex-1 rounded-lg bg-indigo-600 py-1.5 text-[12px] font-semibold text-white">บันทึก</button>
            <button type="button" @click="cancelEdit" class="flex-1 rounded-lg border border-line py-1.5 text-[12px] font-semibold text-ink-soft">ยกเลิก</button>
          </div>
        </div>

        <div v-else class="flex flex-wrap gap-1.5">
          <button type="button" @click="move(i, -1)" :disabled="i === 0" class="rounded-md border border-line px-1.5 py-1 text-[11px] text-ink-faint disabled:opacity-30">↑</button>
          <button type="button" @click="move(i, 1)" :disabled="i === visibleImages.length - 1" class="rounded-md border border-line px-1.5 py-1 text-[11px] text-ink-faint disabled:opacity-30">↓</button>
          <button type="button" @click="startEdit(img)" class="rounded-md border border-line px-2 py-1 text-[11.5px] font-semibold text-ink-soft hover:bg-pagebg">แก้ไข</button>
          <button type="button" v-if="!img.isCover" @click="onSetCover(img)" class="rounded-md border border-indigo-200 px-2 py-1 text-[11.5px] font-semibold text-indigo-700 hover:bg-indigo-50">ตั้งเป็นหน้าปก</button>
          <button type="button" @click="onDelete(img)" class="rounded-md border border-red-200 px-2 py-1 text-[11.5px] font-semibold text-red-700 hover:bg-red-50">ลบ</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
