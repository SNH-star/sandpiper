<template>
  <div class="field grid-field">
    <div class="grid-head">
      <span class="label">Graph <slot name="label-suffix" /></span>
      <span class="grid-count" aria-live="polite">{{ count_text }}</span>
      <b-button v-if="picked" size="is-small" class="grid-clear" @click="clear_all">× Clear all</b-button>
    </div>
    <div id="grid-field-body" class="grid-body">
      <p class="grid-note">
        Click hexagons to pick them: each picked hexagon searches the
        sample type shown when you click it. Switch between Host-associated and Ecological to mix both in one search. Click a hexagon again to drop it. Moving the mouse never changes the search.
      </p>
      <p v-if="error" class="grid-error" role="alert">{{ error }}</p>
      <p v-else-if="!map" class="grid-note">Loading the map…</p>
      <sample-hex-map-chart v-else compact selectable :data="map" :chosen="chosen_keys" @toggle="toggle_hex" @view-change="set_view" />
    </div>
  </div>
</template>

<script>
import { fetchSandpiperStatistics } from '@/api'
import SampleHexMapChart from '@/components/statistics/SampleHexMapChart.vue'
import { parseGrid, parseHexes, formatPicks, toggleHex, chosenHexKeys } from '@/utils/grid'

const plural = (count, noun) => `${count} ${noun}${count === 1 ? '' : 's'}`

export default {
  name: 'SearchGridField',
  components: { SampleHexMapChart },
  props: { modelValue: { type: String, default: '' } },
  // `change` carries the picked hexagons as the `grid` value; each hexagon names
  // its own sample type, so the Latitude, Longitude and Environment fields are
  // not used. Squares from a search link made with the earlier map stay in the
  // value and are still searched, though this map cannot draw them.
  emits: ['change'],
  data () { return { map: null, error: '', view: 'host_associated' } },
  computed: {
    corners () { return parseGrid(this.modelValue) },
    hexes () { return parseHexes(this.modelValue) },
    picked () { return this.corners.length + this.hexes.length },
    chosen_keys () { return chosenHexKeys(this.hexes, this.view) },
    count_text () {
      if (!this.picked) return ''
      const by = type => this.hexes.filter(hex => hex[2] === type).length
      const parts = [by('host') && `${by('host')} host`, by('ecological') && `${by('ecological')} ecological`].filter(Boolean)
      const texts = [
        this.hexes.length && `${parts.join(' + ')} ${this.hexes.length === 1 ? 'hexagon' : 'hexagons'}`,
        this.corners.length && `${plural(this.corners.length, 'square')} from an earlier search`
      ].filter(Boolean)
      return `${texts.join(' and ')} picked`
    }
  },
  mounted () {
    this.load_map()
  },
  methods: {
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
      // Switching only changes what is drawn; the picked hexagons and the
      // search's environment stay as they were.
      this.view = view
    },
    toggle_hex (key) {
      this.$emit('change', { grid: formatPicks(this.corners, toggleHex(this.hexes, key, this.view)) })
    },
    clear_all () {
      this.$emit('change', { grid: '' })
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
