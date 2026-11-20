<template>
  <equal-earth-map ref="map" :label="label">
    <template #default="{ scale }">
      <g :transform="`translate(${marker[0]} ${marker[1]}) scale(${scale})`" class="sample-marker">
        <circle :r="MARKER_HALO" :fill="MARKER_COLOUR" class="sample-marker-halo" />
        <circle :r="MARKER_DOT" :fill="MARKER_COLOUR" class="sample-marker-dot" />
      </g>
    </template>
  </equal-earth-map>
</template>

<script>
// The flat view of a run's sample location (see RunLocationMap): the equal-area world map with the sample
// marked on it as a dot with a white rim inside a soft halo, as on the globe.
import EqualEarthMap from '@/components/EqualEarthMap.vue'
import { mapPoint } from '@/components/equalEarth'
import { SAMPLE_MARKER_COLOUR } from '@/components/mapStyles'

const SAMPLE_ZOOM = 6
const MARKER_HALO = 14
const MARKER_DOT = 6

export default {
  name: 'RunLocationFlatMap',
  components: { EqualEarthMap },
  props: {
    lat: { type: Number, required: true },
    lon: { type: Number, required: true },
    label: { type: String, default: 'Map showing where the sample was collected' }
  },
  data () {
    return { MARKER_HALO, MARKER_DOT, MARKER_COLOUR: SAMPLE_MARKER_COLOUR }
  },
  computed: {
    marker () { return mapPoint(this.lon, this.lat) }
  },
  watch: {
    // The page has moved on to another run: back to the whole world.
    lat () { this.zoom_world() },
    lon () { this.zoom_world() }
  },
  methods: {
    zoom_to_sample () {
      if (this.$refs.map) this.$refs.map.zoom_to_place(this.lon, this.lat, SAMPLE_ZOOM)
    },
    zoom_world () {
      if (this.$refs.map) this.$refs.map.zoom_world()
    }
  }
}
</script>

<style scoped>
.sample-marker { pointer-events: none; }
.sample-marker-halo { opacity: 0.25; }
.sample-marker-dot { stroke: var(--color-white); stroke-width: 2.5; }
</style>
