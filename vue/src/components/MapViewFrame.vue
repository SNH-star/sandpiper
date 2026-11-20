<template>
  <figure class="view-frame">
    <div class="view-frame-bar">
      <div class="view-frame-group" role="group" aria-label="Shape of the map">
        <button v-for="option in VIEWS" :key="option.value" type="button" class="view-frame-button" :class="{ 'is-active': view === option.value }"
                :aria-pressed="String(view === option.value)" @click="view = option.value">{{ option.label }}</button>
      </div>
      <div v-if="view === 'globe'" class="view-frame-group" role="group" aria-label="Picture on the globe">
        <button v-for="option in BASES" :key="option.value" type="button" class="view-frame-button" :class="{ 'is-active': base === option.value }"
                :aria-pressed="String(base === option.value)" @click="base = option.value">{{ option.label }}</button>
      </div>
      <div class="view-frame-group" role="group" aria-label="Zoom">
        <button v-for="action in actions" :key="action.name" type="button" class="view-frame-button" @click="$emit('action', action.name)">{{ action.label }}</button>
      </div>
    </div>
    <div class="view-frame-view">
      <slot :view="view" :base="base" />
    </div>
    <figcaption class="view-frame-caption">
      <slot name="caption" />
      <span class="view-frame-hint">Ctrl (⌘ on a Mac) + scroll or pinch to zoom; drag to move.</span>
    </figcaption>
  </figure>
</template>

<script>
// The frame the run page's and the project page's maps share. Each map has two views, both true to the
// sizes of countries: a flat equal-area outline map, shown first, and a globe with street and satellite
// detail. The frame holds the buttons that choose between them, and the page's own zoom buttons
// (`actions`, each { name, label }), which it reports with 'action' for the page to pass to its map.
import { defineAsyncComponent, h } from 'vue'

const VIEWS = [{ value: 'flat', label: 'Flat' }, { value: 'globe', label: 'Globe' }]
const BASES = [{ value: 'map', label: 'Map' }, { value: 'satellite', label: 'Satellite' }]
const message = text => ({ render: () => h('p', { class: 'view-frame-message', role: 'status' }, text) })

// A globe component, fetched only when the globe is first asked for: its map library is large.
export function lazyGlobe (loader) {
  return defineAsyncComponent({
    loader,
    loadingComponent: message('Loading the globe…'),
    errorComponent: message('The globe could not be loaded. Check your connection and reload the page, or use the flat map.')
  })
}

export default {
  name: 'MapViewFrame',
  props: {
    actions: { type: Array, default: () => [] }
  },
  emits: ['action'],
  data () {
    return { view: 'flat', base: 'map', VIEWS, BASES }
  }
}
</script>

<style scoped>
.view-frame { margin: 0 0 1rem; }
.view-frame-bar { display: flex; flex-wrap: wrap; gap: 0.4rem 0.75rem; margin-bottom: 0.4rem; }
.view-frame-group { display: flex; gap: 2px; }
.view-frame-view { border: 1px solid var(--color-rule, var(--color-rule)); border-radius: 2px; }
.view-frame-view :deep(.view-frame-message) { margin: 0; padding: 2rem 1rem; font-size: 0.9rem; color: var(--color-ink-muted); text-align: center; }
.view-frame-button {
  min-height: 2rem;
  padding: 0 0.7rem;
  font: inherit;
  font-size: 0.85rem;
  color: var(--color-text);
  background: var(--color-white);
  border: 1px solid #c8c8c8;
  border-radius: 2px;
  cursor: pointer;
}
.view-frame-button:hover { border-color: #00796b; }
.view-frame-button.is-active { color: var(--color-white); background: #00796b; border-color: #00796b; }
.view-frame-button:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.view-frame-caption { margin-top: 0.4rem; font-size: 0.9rem; color: var(--color-ink-muted); }
.view-frame-hint { display: block; font-size: 0.8rem; }
@media (max-width: 600px) {
  .view-frame-button { min-height: 2.75rem; }
}
</style>
