<template>
  <div class="search-mode-switch" :class="{ 'is-amplicon': modelValue === 'amplicon' }" role="tablist" aria-label="Search mode">
    <span class="search-mode-thumb" aria-hidden="true"></span>
    <button v-for="mode in MODES" :key="mode.value" type="button" role="tab" class="search-mode-tab"
      :class="{ 'is-active': modelValue === mode.value }" :aria-selected="modelValue === mode.value"
      @click="$emit('update:modelValue', mode.value)">
      {{ mode.label }}
    </button>
  </div>
</template>

<script>
// Metagenome / Amplicon slider. The parent owns the mode (v-model).
const MODES = [
  { value: 'metagenome', label: 'Metagenome' },
  { value: 'amplicon', label: 'Amplicon' }
]

export default {
  name: 'SearchModeSwitch',
  props: {
    modelValue: { type: String, required: true }
  },
  emits: ['update:modelValue'],
  data () {
    return { MODES }
  }
}
</script>

<style scoped>
.search-mode-switch {
  position: relative;
  display: inline-grid;
  grid-template-columns: 1fr 1fr;
  padding: 3px;
  background: hsl(174, 25%, 92%);
  border-radius: 999px;
  flex-shrink: 0;
}
/* White pill that slides under the active tab. */
.search-mode-thumb {
  position: absolute;
  top: 3px;
  bottom: 3px;
  left: 3px;
  width: calc(50% - 3px);
  background: #fff;
  border-radius: 999px;
  box-shadow: 0 1px 3px hsla(174, 40%, 20%, 0.18);
  transition: transform 220ms cubic-bezier(0.16, 1, 0.3, 1);
}
.search-mode-switch.is-amplicon .search-mode-thumb {
  transform: translateX(100%);
}
.search-mode-tab {
  position: relative;
  appearance: none;
  border: 0;
  background: transparent;
  border-radius: 999px;
  padding: 0.35rem 1rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: hsl(174, 20%, 35%);
  cursor: pointer;
  transition: color 150ms ease;
}
.search-mode-tab:hover:not(.is-active),
.search-mode-tab.is-active {
  color: hsl(174, 62%, 24%);
}
.search-mode-tab:focus-visible {
  outline: 2px solid hsl(174, 62%, 34%);
  outline-offset: 2px;
}
@media (prefers-reduced-motion: reduce) {
  .search-mode-thumb { transition: none; }
}
</style>
