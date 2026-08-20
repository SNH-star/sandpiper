<template>
  <button
    type="button"
    class="info-tooltip-button"
    :aria-label="label"
    aria-haspopup="dialog"
    :aria-expanded="expanded"
    :aria-controls="controls"
    @pointerdown="rememberPointerState"
    @click.stop="handleClick"
    @focus="$emit('open', $event)"
    @blur="$emit('close-delayed')"
    @mouseenter="$emit('open', $event)"
    @mouseleave="$emit('close-delayed')"
    @keydown.esc.stop="$emit('close')"
  >
    <b-icon icon="information-outline" size="is-small" />
  </button>
</template>

<script>
export default {
  name: 'InfoTooltipButton',
  props: {
    label: { type: String, required: true },
    expanded: { type: Boolean, default: false },
    controls: { type: String, required: true },
  },
  emits: ['open', 'close-delayed', 'close'],
  data () {
    return { pointerStartedExpanded: false }
  },
  methods: {
    rememberPointerState () {
      // pointerdown precedes focus/click. Remembering the state here means a
      // first tap opens even though focus also opens the popover, while a
      // second tap closes it.
      this.pointerStartedExpanded = this.expanded
    },
    handleClick (event) {
      if (event.detail > 0 && this.pointerStartedExpanded) this.$emit('close')
      else this.$emit('open', event)
      this.pointerStartedExpanded = false
    },
  },
}
</script>

<style scoped>
.info-tooltip-button {
  appearance: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  padding: 0.1rem;
  margin: 0;
  background: transparent;
  color: #aaa;
  cursor: help;
  line-height: 1;
  vertical-align: middle;
}
.info-tooltip-button:hover,
.info-tooltip-button:focus-visible {
  color: #555;
}
.info-tooltip-button:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
  border-radius: 3px;
}
@media (max-width: 768px) {
  .info-tooltip-button {
    min-width: 44px;
    min-height: 44px;
  }
}
</style>
