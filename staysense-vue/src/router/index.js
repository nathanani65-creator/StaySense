import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import HotelsView from '../views/HotelsView.vue'
import AccommodationDetailView from '../views/AccommodationDetailView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import FavoritesView from '../views/FavoritesView.vue'
import CompareView from '../views/CompareView.vue'
import PrivacySettingsView from '../views/PrivacySettingsView.vue'
import AdminLayout from '../views/admin/AdminLayout.vue'
import AdminAccommodationsView from '../views/admin/AdminAccommodationsView.vue'
import AdminAccommodationFormView from '../views/admin/AdminAccommodationFormView.vue'
import AdminAmenitiesView from '../views/admin/AdminAmenitiesView.vue'
import AdminPlacesView from '../views/admin/AdminPlacesView.vue'
import AdminMembersView from '../views/admin/AdminMembersView.vue'
import { useAuth } from '../composables/useAuth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/hotels', name: 'hotels', component: HotelsView },
    { path: '/accommodations/:id', name: 'accommodation-detail', component: AccommodationDetailView, props: true },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/register', name: 'register', component: RegisterView },
    { path: '/favorites', name: 'favorites', component: FavoritesView },
    { path: '/compare', name: 'compare', component: CompareView },
    { path: '/privacy', name: 'privacy', component: PrivacySettingsView },
    {
      path: '/admin',
      component: AdminLayout,
      meta: { requiresAdmin: true },
      children: [
        { path: '', redirect: { name: 'admin-accommodations' } },
        { path: 'accommodations', name: 'admin-accommodations', component: AdminAccommodationsView },
        { path: 'accommodations/new', name: 'admin-accommodation-new', component: AdminAccommodationFormView },
        { path: 'accommodations/:id', name: 'admin-accommodation-edit', component: AdminAccommodationFormView, props: true },
        { path: 'amenities', name: 'admin-amenities', component: AdminAmenitiesView },
        { path: 'places', name: 'admin-places', component: AdminPlacesView },
        { path: 'members', name: 'admin-members', component: AdminMembersView },
      ],
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

// Gate every /admin/* route behind role==='admin' — a plain member is bounced
// home, an anonymous visitor is sent to log in first.
router.beforeEach((to) => {
  if (!to.meta.requiresAdmin) return true
  const { isLoggedIn, user } = useAuth()
  if (!isLoggedIn.value) return { path: '/login', query: { redirect: to.fullPath } }
  if (user.value?.role !== 'admin') return { path: '/' }
  return true
})

export default router
