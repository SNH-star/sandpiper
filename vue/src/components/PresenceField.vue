<template>
  <b-field :label-position="label ? 'on-border' : undefined" :label-for="label ? fieldId : undefined" :message="errorMessage" :type="errorMessage ? 'is-danger' : ''">
    <template v-if="label" #label>
      {{ label }}
      <slot name="label-suffix" />
    </template>
    <div class="field has-addons presence-field">
      <div class="control is-expanded search-autocomplete-wrap">
        <b-input
          ref="fieldInput"
          :id="fieldId"
          :compat-fallthrough="false"
          :model-value="present ? '' : modelValue"
          @update:model-value="$emit('update:modelValue', $event)"
          :placeholder="present ? '(any value)' : placeholder"
          :disabled="present"
          size="is-small"
          @input="on_input"
          @keydown="on_keydown"
        ></b-input>
        <template v-if="searchField && !present">
          <div v-if="ghost_suffix" class="search-ghost-overlay" aria-hidden="true">
            <span class="search-ghost-typed">{{ modelValue }}</span><span class="search-ghost-suffix">{{ ghost_suffix }}</span>
          </div>
          <ul v-if="ac_suggestions.length" class="search-suggest-dropdown" role="listbox">
            <li v-for="(s, i) in ac_suggestions" :key="s.label" role="option" :aria-selected="i === ac_active_index"
              :class="{ 'is-active': i === ac_active_index }" @mousedown.prevent="accept_suggestion(s)">
              {{ s.label }}
            </li>
          </ul>
        </template>
      </div>
      <div v-if="allowAny" class="control">
        <b-button
          size="is-small"
          class="presence-any-btn"
          :type="present ? 'is-primary' : ''"
          :aria-pressed="present"
          @click="$emit('update:present', !present)"
          title="Match any run where this field is present, regardless of value"
        >Any</b-button>
      </div>
    </div>
  </b-field>
</template>

<script>
import { useId } from 'vue'
import { fetchTaxonomySearchHints, fetchSearchFieldValues } from '@/api'
import { useFieldValueAutocomplete } from '@/composables/useSearchAutocomplete'

export default {
  name: 'PresenceField',
  props: {
    label: { type: String, default: '' },
    modelValue: { type: String, default: '' },
    present: { type: Boolean, default: false },
    placeholder: { type: String, default: '' },
    errorMessage: { type: String, default: '' },
    // Canonical searchFields.ts key (e.g. 'country', 'platform') -- when
    // given, wires up the same value-autocomplete engine as the universal
    // search bar (ghost text, dropdown, Tab-cycle) for this field alone.
    // Omit for fields with no enumerable/lookupable value set (numeric
    // ranges, free-text abstract, etc.).
    searchField: { type: String, default: '' },
    // false hides the "Any" button, for fields where "has any value" means
    // nothing (every run has a taxonomy and a BioProject).
    allowAny: { type: Boolean, default: true },
  },
  emits: ['update:modelValue', 'update:present', 'input'],
  setup (props) {
    const autocomplete = useFieldValueAutocomplete(props.searchField || undefined, async (field, q, signal) => {
      if (field === 'taxonomy') {
        const { data } = await fetchTaxonomySearchHints(q, undefined, signal)
        // Names in both GTDB and GlobDB come back twice; list each once.
        return [...new Set(data.taxonomies || [])].map(name => ({ value: name, count: null }))
      }
      const { data } = await fetchSearchFieldValues(field, q, signal)
      return data.values
    })
    return {
      fieldId: useId(),
      ac_suggestions: autocomplete.suggestions,
      ac_active_index: autocomplete.activeIndex,
      ac_on_input: autocomplete.onInput,
      ac_cycle_next: autocomplete.cycleNext,
      ac_accept_value: autocomplete.acceptValue,
      ac_clear: autocomplete.clear,
    }
  },
  computed: {
    // Same "only a literal prefix match gets grey inline completion" rule as
    // Search.vue's/App.vue's ghost_suffix -- see their comments for why.
    ghost_suffix () {
      const s = this.ac_suggestions[this.ac_active_index]
      if (!s || !s.insertValue) return ''
      const typed = this.modelValue || ''
      if (!s.insertValue.toLowerCase().startsWith(typed.toLowerCase())) return ''
      return s.insertValue.slice(typed.length)
    },
  },
  methods: {
    on_input (eventOrValue) {
      // With :compat-fallthrough="false", b-input passes this listener to the
      // native <input>, so it receives the browser's input event, not the text.
      // Taking .length of the event was undefined, so suggestions never loaded.
      const value = typeof eventOrValue === 'string' ? eventOrValue : (eventOrValue?.target?.value ?? '')
      this.$emit('input', value)
      if (!this.searchField) return
      this.ac_on_input(value)
    },
    on_keydown (event) {
      if (!this.searchField) return
      if (event.key === 'Tab') {
        if (this.ac_suggestions.length === 0) return
        event.preventDefault()
        this.ac_cycle_next()
        return
      }
      if (event.key === 'Enter') {
        if (this.ac_suggestions.length === 0) return
        event.preventDefault()
        this.accept_suggestion(this.ac_suggestions[this.ac_active_index])
        return
      }
      if (event.key === 'ArrowRight') {
        const el = event.target
        const atEnd = el.selectionStart === el.value.length && el.selectionStart === el.selectionEnd
        if (atEnd && this.ac_suggestions.length > 0) {
          event.preventDefault()
          this.accept_suggestion(this.ac_suggestions[this.ac_active_index])
        }
        return
      }
      if (event.key === 'Escape') this.ac_clear()
    },
    accept_suggestion (s) {
      if (!s) return
      const value = this.ac_accept_value(s)
      this.$emit('update:modelValue', value)
      this.$emit('input', value)
      this.$nextTick(() => {
        const inputEl = this.$refs.fieldInput && this.$refs.fieldInput.$el.querySelector('input')
        if (!inputEl) return
        inputEl.setSelectionRange(value.length, value.length)
        inputEl.focus()
      })
    },
  },
}
</script>

<style scoped>
.presence-field {
  margin-bottom: 0;
}
.presence-any-btn {
  min-width: 46px;
}
.search-autocomplete-wrap {
  position: relative;
}
.search-ghost-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  white-space: pre;
  overflow: hidden;
}
.search-ghost-typed {
  visibility: hidden;
}
.search-ghost-suffix {
  color: rgba(60, 60, 60, 0.45);
}
.search-suggest-dropdown {
  position: absolute;
  left: 0;
  right: auto;
  /* As wide as the longest suggestion (never narrower than the input), so
     values aren't cut off; anything past the cap wraps instead. */
  min-width: 100%;
  width: max-content;
  max-width: min(40rem, calc(100vw - 2rem));
  top: 100%;
  margin-top: 0.25rem;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  max-height: 240px;
  overflow-y: auto;
  z-index: 30;
  list-style: none;
  padding: 0.25rem 0;
  margin-left: 0;
  font-size: 0.85rem;
}
.search-suggest-dropdown li {
  padding: 0.35rem 0.65rem;
  cursor: pointer;
  white-space: normal;
  overflow-wrap: anywhere;
}
.search-suggest-dropdown li.is-active,
.search-suggest-dropdown li:hover {
  background: rgba(50, 115, 220, 0.1);
}
</style>
