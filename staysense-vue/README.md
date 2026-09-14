# StaySense Phitsanulok — Vue 3 Frontend

Vue 3 + Vite + Tailwind CSS conversion of the StaySense Phitsanulok mockup
(homepage + hotel search/listing page).

## Setup

```bash
npm install
npm run dev       # http://localhost:5173
```

## Build for production

```bash
npm run build      # outputs to dist/
npm run preview    # serve the production build locally
```

> **Note on routing:** this app uses Vue Router's `createWebHistory` (clean
> URLs like `/hotels`, no `#`). Any static host serving the built `dist/`
> folder must be configured to fall back to `index.html` for unknown paths
> (e.g. Netlify `_redirects`, Vercel rewrites, or nginx `try_files`), or
> deep-linking directly to `/hotels` will 404. Client-side navigation (using
> the nav links / router-link inside the app) always works regardless.

## Project structure

```
src/
  main.js                     — app entry
  App.vue                     — root layout (header + router-view + footer)
  router/index.js             — routes: / (home), /hotels (listing)
  data/mockHotels.js          — districts, amenity list, mock hotel generator
                                 (swap generateHotels() for a real API call
                                 to GET /api/accommodations when the FastAPI
                                 backend is ready)
  composables/
    useSemanticSearch.js      — simulated semantic search (price-ceiling
                                 extraction + Thai concept/synonym expansion).
                                 Replace with a call to the FastAPI semantic
                                 search endpoint for the real implementation.
  components/
    AppHeader.vue             — logo + nav
    SearchCapsule.vue         — reusable search input + primary button
    LocateButton.vue          — "ใช้ตำแหน่งปัจจุบัน" button
    CategoryCard.vue          — homepage type-of-stay card
    StayCard.vue              — homepage featured-stay card
    AreaCard.vue              — homepage popular-area card
    FilterSidebar.vue         — district/price/rating/amenity/distance filters
    HotelCard.vue             — hotel result card (listing page)
    DistrictMap.vue           — SVG district map with clickable count pins
    Pagination.vue
    ChipRow.vue                — active-filter chips
  views/
    HomeView.vue
    HotelsView.vue
public/
  hero-cover.jpg              — shared hero background image
```

## Wiring up the real backend

Two modules are the seams for connecting to the FastAPI/MySQL backend
designed earlier:

1. **`data/mockHotels.js` → `generateHotels()`** — replace with a fetch to
   `GET /api/accommodations` (with query params for type/district/price/etc.)
   and map the response to the same shape used throughout the components
   (`id, name, district, type, price, rating, reviews, distanceKm, landmark,
   amenities, tags, reason, img, fav`).
2. **`composables/useSemanticSearch.js` → `runSemanticSearch()`** — replace
   the local concept-map scoring with a call to the FastAPI semantic-search
   endpoint (which does the embedding + FAISS lookup) and return the same
   `{ scores, priceCeiling, terms }` shape so `HotelsView.vue` doesn't need
   to change.
