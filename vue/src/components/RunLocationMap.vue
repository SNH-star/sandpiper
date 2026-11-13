<template>
  <figure class="location-map">
    <div class="location-wrap">
      <div ref="container" class="location-canvas" role="application" :aria-label="aria"></div>
      <div class="location-modes" role="group" aria-label="Map options">
        <button type="button" class="location-mode" :class="{ 'is-active': base === 'map' }" :aria-pressed="String(base === 'map')" @click="base = 'map'">Map</button>
        <button type="button" class="location-mode" :class="{ 'is-active': base === 'satellite' }" :aria-pressed="String(base === 'satellite')" @click="base = 'satellite'">Satellite</button>
        <button type="button" class="location-mode location-mode-gap" @click="zoom_to_sample">Sample</button>
        <button type="button" class="location-mode" @click="zoom_world">World</button>
      </div>
    </div>
    <figcaption class="location-caption">
      <span>Latitude {{ coordinate(lat) }}, longitude {{ coordinate(lon) }}<template v-if="country"> ({{ country }})</template>.</span>
    </figcaption>
  </figure>
</template>

<script>
// Where a run's sample was collected, on a flat map: OpenFreeMap streets or Sentinel-2 satellite (both free, no key).
import { markRaw } from 'vue'
import { Map as MapLibreMap, NavigationControl, ScaleControl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import countries110m from 'world-atlas/countries-110m.json'
import { BASE_STYLES, SAMPLE_MARKER_COLOUR as MARKER_COLOUR, decorateBase, maritimeBorders } from '@/components/mapStyles'
import { countryAt } from '@/components/statistics/worldGeometry'

const SAMPLE_ZOOM = 6
// The map opens four presses of the − button further out than the Sample close-up, so the surrounding
// countries show where in the world the sample is.
const START_ZOOM_STEPS_OUT = 4
const START_ZOOM = SAMPLE_ZOOM - START_ZOOM_STEPS_OUT
const WORLD_ZOOM = 0.6
// The sample's marker is drawn by the map itself, as a dot with a white rim inside a soft halo. The map
// repeats the world sideways, and a layer is drawn on every copy, where a pin element sits on only one.
const MARKER_SOURCE = 'sample-location'
const MARKER_LAYERS = [
  { id: 'sample-location-halo', type: 'circle', source: MARKER_SOURCE, paint: { 'circle-radius': 16, 'circle-color': MARKER_COLOUR, 'circle-opacity': 0.25 } },
  { id: 'sample-location-dot', type: 'circle', source: MARKER_SOURCE, paint: { 'circle-radius': 7, 'circle-color': MARKER_COLOUR, 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 2.5 } }
]

export default {
  name: 'RunLocationMap',
  props: {
    lat: { type: Number, required: true },
    lon: { type: Number, required: true }
  },
  data () {
    return { base: 'map' }
  },
  computed: {
    // The country the sample lies in, from the coarse world outline (nothing when it is at sea).
    country () { return countryAt(countries110m, this.lon, this.lat) },
    aria () {
      return `Map showing where the sample was collected, at latitude ${this.coordinate(this.lat)}, longitude ${this.coordinate(this.lon)}.`
    }
  },
  watch: {
    base () { if (this.map) this.map.setStyle(BASE_STYLES[this.base]) },
    lat () { this.move_marker(); this.zoom_to_start() },
    lon () { this.move_marker(); this.zoom_to_start() }
  },
  mounted () {
    const map = markRaw(new MapLibreMap({
      container: this.$refs.container,
      style: BASE_STYLES.map,
      center: [this.lon, this.lat],
      zoom: START_ZOOM,
      maxPitch: 0,
      dragRotate: false,
      cooperativeGestures: true,
      attributionControl: { compact: true }
    }))
    this.map = map
    map.touchZoomRotate.disableRotation()
    // A change of base map drops every layer, so the marker is put back each time a style loads.
    map.on('style.load', () => {
      decorateBase(map, this.base)
      maritimeBorders(map, this.base === 'satellite')
      this.add_marker()
    })
    map.addControl(new NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(new ScaleControl({ unit: 'metric' }), 'bottom-left')
  },
  beforeUnmount () {
    if (this.map) this.map.remove()
    this.map = null
  },
  methods: {
    coordinate (value) {
      return `${value.toFixed(4)}°`
    },
    marker_point () {
      return { type: 'Feature', geometry: { type: 'Point', coordinates: [this.lon, this.lat] }, properties: {} }
    },
    add_marker () {
      if (!this.map.getSource(MARKER_SOURCE)) this.map.addSource(MARKER_SOURCE, { type: 'geojson', data: this.marker_point() })
      MARKER_LAYERS.forEach(layer => { if (!this.map.getLayer(layer.id)) this.map.addLayer(layer) })
    },
    move_marker () {
      const source = this.map && this.map.getSource(MARKER_SOURCE)
      if (source) source.setData(this.marker_point())
    },
    // The opening view, also used when the page moves on to another run.
    zoom_to_start () {
      if (this.map) this.map.easeTo({ center: [this.lon, this.lat], zoom: START_ZOOM })
    },
    zoom_to_sample () {
      if (this.map) this.map.easeTo({ center: [this.lon, this.lat], zoom: SAMPLE_ZOOM })
    },
    zoom_world () {
      if (this.map) this.map.easeTo({ center: [this.lon, 20], zoom: WORLD_ZOOM })
    }
  }
}
</script>

<style scoped>
.location-map { margin: 0 0 1rem; max-width: 720px; }
.location-wrap { position: relative; }
.location-canvas { width: 100%; height: 360px; border: 1px solid var(--color-rule, hsl(0, 0%, 88%)); border-radius: 2px; }
.location-modes { position: absolute; top: 10px; left: 10px; display: flex; gap: 2px; }
.location-mode {
  min-height: 2rem;
  padding: 0 0.7rem;
  font: inherit;
  font-size: 0.85rem;
  color: #363636;
  background: #fff;
  border: 1px solid #c8c8c8;
  border-radius: 2px;
  cursor: pointer;
}
.location-mode-gap { margin-left: 0.5rem; }
.location-mode:hover { border-color: #00796b; }
.location-mode.is-active { color: #fff; background: #00796b; border-color: #00796b; }
.location-mode:focus-visible { outline: 2px solid #3273dc; outline-offset: 2px; }
.location-caption { margin-top: 0.4rem; font-size: 0.9rem; color: hsl(0, 0%, 40%); }
@media (max-width: 600px) {
  .location-canvas { height: 300px; }
  .location-mode { min-height: 2.75rem; }
}
</style>
