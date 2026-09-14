// Toggling a favorite needs a logged-in user (StaySense has no anonymous
// favorites store — see AccommodationDetailView's old "local-only" note).
// This composable calls the real API and reverts the optimistic UI update
// if the request fails, so `item.fav` never lies about server state.
import { useAuth } from './useAuth'
import { addFavorite, removeFavorite } from '../api/favorites'

export function useFavorites() {
  const { isLoggedIn } = useAuth()

  // `item` is any object shaped like AccommodationOut ({ id, fav, ... }).
  // Returns false (and does nothing) when the user isn't logged in, so the
  // caller can redirect to /login instead.
  async function toggleFavorite(item) {
    if (!isLoggedIn.value) return false

    const wasFav = !!item.fav
    item.fav = !wasFav // optimistic
    try {
      if (wasFav) await removeFavorite(item.id)
      else await addFavorite(item.id)
      return true
    } catch (e) {
      item.fav = wasFav // revert — the request didn't actually succeed
      throw e
    }
  }

  return { toggleFavorite }
}
