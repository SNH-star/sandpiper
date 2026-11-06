<template>
  <div class="field grid-field">
    <div class="grid-head">
      <span class="label">Graph <slot name="label-suffix" /></span>
      <b-button size="is-small" :type="is_open ? 'is-primary' : ''" :aria-expanded="is_open" aria-controls="grid-field-body" @click="toggle_open">
        {{ is_open ? 'Hide map' : 'Show map' }}
      </b-button>
      <span class="grid-count" aria-live="polite">{{ count_text }}</span>
      <b-button v-if="corners.length" size="is-small" class="grid-clear" @click="clear_all">× Clear all</b-button>
    </div>
    <div v-if="is_open" id="grid-field-body" class="grid-body">
      <p class="grid-note">
        Click circles to pick squares: each square searches the
        sample type shown when you click it. Switch between Host-associated and Ecological to mix both in one search. Click a circle again to drop it. Moving the mouse never changes the search.
      </p>
      <p v-if="error" class="grid-error" role="alert">{{ error }}</p>
      <p v-else-if="!map" class="grid-note">Loading the map…</p>
      <sample-map-chart v-else compact selectable :data="map" :chosen="chosen_keys" @toggle="toggle_square" @view-change="set_view" />
    </div>
  </div>
</template>

<script>
import { fetchSandpiperStatistics } from '@/api'
import SampleMapChart from '@/components/statistics/SampleMapChart.vue'
import { parseGrid, formatGrid, toggleCorner, chosenKeys } from '@/utils/grid'

export default {
  name: 'SearchGridField',
  components: { SampleMapChart },
  props: { modelValue: { type: String, default: '' } },
  // `change` carries the picked squares as the `grid` value; each square names
  // its own sample type, so the Latitude, Longitude and Environment fields are
  // not used.
  emits: ['change'],
  data () { return { is_open: false, map: null, error: '', view: 'host_associated' } },
  computed: {
    corners () { return parseGrid(this.modelValue) },
    chosen_keys () { return chosenKeys(this.corners, this.view) },
    count_text () {
      const n = this.corners.length
      if (!n) return ''
      const by = type => this.corners.filter(c => c[2] === type).length
      const host = by('host')
      const eco = by('ecological')
      if (!host && !eco) return `${n} square${n === 1 ? '' : 's'} picked`
      const parts = [host && `${host} host`, eco && `${eco} ecological`].filter(Boolean)
      return `${parts.join(' + ')} square${n === 1 ? '' : 's'} picked`
    }
  },
  methods: {
    toggle_open () {
      this.is_open = !this.is_open
      if (this.is_open && !this.map) this.load_map()
    },
    load_map () {
      this.error = ''
      fetchSandpiperStatistics()
        .then(response => {
          if (!response.data.map) throw new Error('The statistics response has no map data.')
          this.map = response.data.map
        })
        .catch(error => {
          console.error('Could not load the search map', error)
          this.error = 'The map could not be loaded. Use the Latitude and Longitude fields instead.'
        })
    },
    set_view (view) {
      // Switching only changes what is drawn; the picked squares and the
      // search's environment stay as they were.
      this.view = view
    },
    toggle_square (key) {
      this.emit_corners(toggleCorner(this.corners, key, this.view))
    },
    clear_all () {
      this.emit_corners([])
    },
    emit_corners (corners) {
      this.$emit('change', { grid: formatGrid(corners) })
    }
  }
}
</script>

<style scoped>
.grid-field { flex: 1 1 100%; min-width: 0; max-width: none; }
.grid-head { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-3); }
.grid-head .label { margin: 0; }
.grid-count { font-size: 0.9rem; color: var(--color-ink-muted); }
.grid-note { max-width: 62ch; margin-top: var(--space-2); font-size: 0.85rem; line-height: 1.5; color: var(--color-ink-muted); text-wrap: pretty; }
.grid-error { margin-top: var(--space-2); font-size: 0.9rem; color: var(--color-danger, #c0392b); }
.grid-body { margin-top: var(--space-2); }
</style>
