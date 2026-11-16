<template>
  <map-view-frame class="location-map" :actions="ACTIONS" @action="zoom">
    <template #default="{ view, base }">
      <run-location-flat-map v-if="view === 'flat'" ref="shown" :lat="lat" :lon="lon" :label="aria(view)" />
      <run-location-globe v-else ref="shown" :lat="lat" :lon="lon" :base="base" :label="aria(view)" />
    </template>
    <template #caption>
      <span>
        {{ coordinate(lat, 'N', 'S') }}, {{ coordinate(lon, 'E', 'W') }}<template v-if="country">, {{ country }}</template>.
      </span>
      <span v-if="mismatch" class="location-flag">
        <b-icon icon="alert-outline" size="is-small" />
        Does not match the geo loc name
      </span>
    </template>
  </map-view-frame>
</template>

<script>
// Where a run's sample was collected, as a flat map or a globe (see MapViewFrame).
import countries110m from 'world-atlas/countries-110m.json'
import MapViewFrame, { lazyGlobe } from '@/components/MapViewFrame.vue'
import RunLocationFlatMap from '@/components/RunLocationFlatMap.vue'
import { countryAt } from '@/components/statistics/worldGeometry'

// Each button calls the method of its name on whichever view is shown.
const ACTIONS = [{ name: 'zoom_to_sample', label: 'Sample' }, { name: 'zoom_world', label: 'World' }]

export default {
  name: 'RunLocationMap',
  components: {
    MapViewFrame,
    RunLocationFlatMap,
    RunLocationGlobe: lazyGlobe(() => import('@/components/RunLocationGlobe.vue'))
  },
  props: {
    lat: { type: Number, required: true },
    lon: { type: Number, required: true },
    // True when the recorded geo loc name disagrees with these coordinates (see RunMetadata).
    mismatch: { type: Boolean, default: false }
  },
  data () {
    return { ACTIONS }
  },
  computed: {
    // The country the sample lies in, from the coarse world outline (nothing when it is at sea).
    country () { return countryAt(countries110m, this.lon, this.lat) }
  },
  methods: {
    // e.g. "32.0000° N".
    coordinate (value, positive, negative) {
      return `${Math.abs(value).toFixed(4)}° ${value < 0 ? negative : positive}`
    },
    aria (view) {
      return `${view === 'flat' ? 'Map' : 'Globe'} showing where the sample was collected, at ${this.coordinate(this.lat, 'N', 'S')}, ${this.coordinate(this.lon, 'E', 'W')}.`
    },
    // Nothing happens while the globe is still loading.
    zoom (method) {
      const shown = this.$refs.shown
      if (shown && typeof shown[method] === 'function') shown[method]()
    }
  }
}
</script>

<style scoped>
.location-map { max-width: 720px; }
.location-flag { display: block; margin-top: 0.25rem; font-weight: 600; color: #8a5a00; }
</style>
