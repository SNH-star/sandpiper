<template>
  <div ref="container" class="globe-canvas" role="application" :aria-label="label"></div>
</template>

<script>
// The globe view of a run's sample location (see RunLocationMap): OpenFreeMap streets or Sentinel-2 satellite (both free, no key).
// A globe keeps every country at its true size and shape, where the usual flat (Mercator) map swells the
// land towards the poles. Zoomed right in, MapLibre flattens it again, and there the two look the same.
import { markRaw } from 'vue'
import { Map as MapLibreMap, NavigationControl, ScaleControl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { BASE_STYLES, SAMPLE_MARKER_COLOUR as MARKER_COLOUR, decorateBase, maritimeBorders } from '@/components/mapStyles'

const SAMPLE_ZOOM = 6
// The map opens four presses of the − button further out than the Sample close-up, so the surrounding
// countries show where in the world the sample is.
const START_ZOOM_STEPS_OUT = 4
const START_ZOOM = SAMPLE_ZOOM - START_ZOOM_STEPS_OUT
// Far enough out for the whole globe to fit in the frame; the map zooms out no further than this.
const WORLD_ZOOM = 0.6
const GLOBE = { type: 'globe' }
// The sample's marker is drawn by the map itself, as a dot with a white rim inside a soft halo, so it sits
// on the globe's surface and goes out of sight with it when the globe is turned.
const MARKER_SOURCE = 'sample-location'
const MARKER_LAYERS = [
  { id: 'sample-location-halo', type: 'circle', source: MARKER_SOURCE, paint: { 'circle-radius': 16, 'circle-color': MARKER_COLOUR, 'circle-opacity': 0.25 } },
  { id: 'sample-location-dot', type: 'circle', source: MARKER_SOURCE, paint: { 'circle-radius': 7, 'circle-color': MARKER_COLOUR, 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 2.5 } }
]

export default {
  name: 'RunLocationGlobe',
  props: {
    lat: { type: Number, required: true },
    lon: { type: Number, required: true },
    // Which base map to show: 'map' (streets) or 'satellite'.
    base: { type: String, default: 'map', validator: value => value in BASE_STYLES },
    label: { type: String, default: 'Globe showing where the sample was collected' }
  },
  watch: {
    base () { if (this.map) this.map.setStyle(BASE_STYLES[this.base]) },
    lat () { this.move_marker(); this.zoom_to_start() },
    lon () { this.move_marker(); this.zoom_to_start() }
  },
  mounted () {
    const map = markRaw(new MapLibreMap({
      container: this.$refs.container,
      style: BASE_STYLES[this.base],
      center: [this.lon, this.lat],
      zoom: START_ZOOM,
      minZoom: WORLD_ZOOM,
      maxPitch: 0,
      dragRotate: false,
      cooperativeGestures: true,
      attributionControl: { compact: true }
    }))
    this.map = map
    map.touchZoomRotate.disableRotation()
    // A change of base map drops every layer and the projection, so both are put back each time a style loads.
    map.on('style.load', () => {
      map.setProjection(GLOBE)
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
.globe-canvas { width: 100%; height: 360px; }
@media (max-width: 600px) {
  .globe-canvas { height: 300px; }
}
</style>
