// Module-level singleton (same pattern as useReferenceData.js) so every
// component sees the same login state without pulling in a store library.
import { ref, computed } from 'vue'
import { apiLogin, apiRegister, apiMe } from '../api/auth'
import { AUTH_TOKEN_KEY } from '../api/client'

const USER_KEY = 'staysense_user'

function readStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function safeStorage(fn) {
  try {
    fn()
  } catch {
    // localStorage unavailable (private mode, quota, ...) — state still
    // works in-memory for the rest of this session
  }
}

const token = ref(safeGet(AUTH_TOKEN_KEY))
const user = ref(readStoredUser())

function safeGet(key) {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function persist() {
  safeStorage(() => {
    if (token.value) localStorage.setItem(AUTH_TOKEN_KEY, token.value)
    else localStorage.removeItem(AUTH_TOKEN_KEY)
    if (user.value) localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    else localStorage.removeItem(USER_KEY)
  })
}

function setSession(tokenOut) {
  token.value = tokenOut.access_token
  user.value = tokenOut.user
  persist()
}

async function login(email, password) {
  const res = await apiLogin({ email, password })
  setSession(res)
}

async function register(name, email, password) {
  const res = await apiRegister({ name, email, password })
  setSession(res)
}

function logout() {
  token.value = null
  user.value = null
  persist()
}

// Confirms the stored token still works (e.g. after a long absence) and
// refreshes the cached profile. Failure just logs the session out quietly —
// callers don't need to handle it.
async function refreshProfile() {
  if (!token.value) return
  try {
    user.value = await apiMe()
    persist()
  } catch {
    logout()
  }
}

const isLoggedIn = computed(() => !!token.value)

export function useAuth() {
  return { token, user, isLoggedIn, login, register, logout, refreshProfile }
}
