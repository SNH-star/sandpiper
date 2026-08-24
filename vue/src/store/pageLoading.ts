import { reactive } from 'vue'

// Shared across App.vue and every route view. A route's `created()` hook
// calls stopPageLoading() the moment its content is actually visible --
// immediately for views with no data gate in their template, or once the
// gating fetch settles (success or failure) for views that render nothing
// until then (see the `v-if="... !== null"` guards in Run/Project/
// SearchResult/Accession). This replaces guessing a fixed delay with the
// real per-page signal.
const state = reactive({
  isLoading: false
})

// Bumped on every startPageLoading() call. Views whose "loaded" signal
// fires after an async gap (Run/Project/SearchResult, via .finally() on
// their gating fetch) capture this token when they start loading and pass
// it back to stopPageLoading(). Without it, navigating away from one of
// those pages before its fetch resolves lets the abandoned instance's
// stale .finally() clear the flag for whatever page is loading *now* --
// flashing a blank white page mid-load instead of leaving the backdrop up.
let generation = 0

export function startPageLoading (): void {
  generation += 1
  state.isLoading = true
}

export function currentLoadingToken (): number {
  return generation
}

export function stopPageLoading (token?: number): void {
  if (token !== undefined && token !== generation) return
  state.isLoading = false
}

export const pageLoadingState = state
