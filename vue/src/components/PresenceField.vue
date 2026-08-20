<template>
  <b-field :label-position="label ? 'on-border' : undefined" :label-for="label ? fieldId : undefined" :message="errorMessage" :type="errorMessage ? 'is-danger' : ''">
    <template v-if="label" #label>
      {{ label }}
      <slot name="label-suffix" />
    </template>
    <div class="field has-addons presence-field">
      <div class="control is-expanded">
        <b-input
          :id="fieldId"
          :compat-fallthrough="false"
          :model-value="present ? '' : modelValue"
          @update:model-value="$emit('update:modelValue', $event)"
          :placeholder="present ? '(any value)' : placeholder"
          :disabled="present"
          size="is-small"
          @input="$emit('input', $event)"
        ></b-input>
      </div>
      <div class="control">
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

export default {
  name: 'PresenceField',
  props: {
    label: { type: String, default: '' },
    modelValue: { type: String, default: '' },
    present: { type: Boolean, default: false },
    placeholder: { type: String, default: '' },
    errorMessage: { type: String, default: '' },
  },
  emits: ['update:modelValue', 'update:present', 'input'],
  setup() {
    return { fieldId: useId() }
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
</style>
