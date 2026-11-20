<template>
  <equal-earth-map ref="map" :label="label" @view-change="view = $event" @map-click="close_lists">
    <template #default="{ scale }">
      <g v-for="marker in markers" :key="marker.key" :transform="`translate(${marker.x} ${marker.y}) scale(${scale})`"
         class="runs-marker" :class="{ 'is-pinned': marker.key === pinned_key }" role="button" tabindex="0" :aria-label="marker_label(marker)"
         @pointerenter="preview(marker, $event)" @pointerleave="linger_preview" @click.stop="pin(marker)"
         @keydown.enter.prevent="pin(marker)" @keydown.space.prevent="pin(marker)">
        <circle :r="radius_of(marker)" :fill="MARKER_COLOUR" class="runs-marker-disc" />
        <text class="runs-marker-count">{{ marker.runs.toLocaleString('en-US') }}</text>
      </g>
    </template>
    <template #over>
      <div v-for="list in lists" :key="list.marker.key" class="runs-flat-popup" :class="{ 'is-below': list.below }" :style="list.style"
           @pointerenter="hold_preview(list)" @pointerleave="release_preview(list)">
        <button v-if="list.pinned" type="button" class="runs-flat-popup-close" aria-label="Close this list" @click="close_lists">×</button>
        <div class="runs-popup-head">
          <p class="runs-popup-title">{{ list.title }}</p>
          <p v-if="list.one_study" class="runs-popup-study">{{ list.studies[0].title }}</p>
        </div>
        <div class="runs-popup-scroll">
          <template v-for="study in list.studies" :key="study.title">
            <!-- With several studies each title stays at the top of the list while its own runs scroll under it. -->
            <p v-if="!list.one_study" class="runs-popup-study is-sticky">{{ study.title }}</p>
            <ul class="runs-popup-runs">
              <li v-for="accession in study.runs" :key="accession"><router-link :to="{ name: 'Run', params: { accession } }">{{ accession }}</router-link></li>
            </ul>
          </template>
        </div>
        <div class="runs-popup-foot">
          <p v-if="list.more > 0" class="runs-popup-note">and {{ plural(list.more, 'more run') }}, all listed in the table below.</p>
          <button v-if="list.marker.places.length > 1" type="button" class="runs-popup-zoom" @click="separate(list.marker)">Zoom in to separate these places</button>
          <p v-if="!list.pinned" class="runs-popup-note">Click the marker to keep this list open.</p>
        </div>
      </div>
    </template>
  </equal-earth-map>
</template>

<script>
// The flat view of the project page's map (see ProjectRunsMap): the equal-area world map with one numbered
// marker per place the project's runs were collected at. As on the globe, places close together on screen
// share one marker, numbered with their runs in total, and separate on zooming in; hovering a marker lists
// its runs, and clicking keeps the list open.
import EqualEarthMap from '@/components/EqualEarthMap.vue'
import '@/components/runsPopup.css'
import { MAP_WIDTH, MAP_HEIGHT, mapPoint } from '@/components/equalEarth'
import { SAMPLE_MARKER_COLOUR } from '@/components/mapStyles'
import { placesToGeoJson, runsAt, mergePlaces, plural } from '@/utils/runPlaces'

// The opening view holds every place with this much room round them, and is never closer than this zoom.
const FIT_MAX_SCALE = 6
const FIT_PADDING_PX = 70
// Places within this many pixels of each other share a marker. They are gathered afresh each time the
// zoom doubles, not at every step of a zoom, so the markers hold still while the map moves.
const MERGE_RADIUS_PX = 36
// From this zoom on, near the closest the map goes, only places at the very same spot share a marker,
// so places a few kilometres apart can still be told apart.
const MERGE_UNTIL_SCALE = 32
// More runs than this in one list are counted, not listed.
const RUNS_LISTED = 30
const POPUP_GAP_PX = 6
// How long a previewed list stays after the pointer leaves its marker, so the pointer can cross the gap onto
// the list; while the pointer is on the list it stays open.
const PREVIEW_LINGER_MS = 350
// A marker grows a little with its runs: 10 px for under ten, up to 20 px for a thousand.
const MARKER_RADII = [[1000, 20], [100, 16], [10, 13], [0, 10]]
// A list opens below a marker in the top part of the map, and leans inwards near the left and right edges.
const BELOW_ABOVE_PERCENT = 45
const EDGE_PERCENT = 25

export default {
  name: 'ProjectRunsFlatMap',
  components: { EqualEarthMap },
  props: {
    // [{ lat_lon: [lat, lon], samples: { study title: [run accession, ...] } }, ...]
    lat_lons: { type: Array, default: () => [] },
    label: { type: String, default: 'Map of where this project\'s runs were collected' }
  },
  data () {
    return {
      MARKER_COLOUR: SAMPLE_MARKER_COLOUR,
      // The map's zoom and pan, and its map units to one pixel (see EqualEarthMap).
      view: { k: 1, x: 0, y: 0, unit: 1 },
      hover_key: null,
      pinned_key: null
    }
  },
  computed: {
    points () {
      return placesToGeoJson(this.lat_lons).features.map(feature => {
        const [x, y] = mapPoint(...feature.geometry.coordinates)
        return { place: feature.properties.place, runs: feature.properties.runs, x, y }
      })
    },
    merge_scale () { return 2 ** Math.floor(Math.log2(Math.max(1, this.view.k))) },
    markers () {
      const radius = this.merge_scale >= MERGE_UNTIL_SCALE ? 0 : (MERGE_RADIUS_PX * this.view.unit) / this.merge_scale
      return mergePlaces(this.points, radius)
    },
    // The pinned list, and the previewed one beside it when the pointer is on another marker.
    lists () {
      const keys = [this.pinned_key, this.hover_key === this.pinned_key ? null : this.hover_key]
      return keys.flatMap((key, index) => {
        const marker = key === null ? null : this.markers.find(candidate => candidate.key === key)
        const list = marker && this.list_of(marker, index === 0)
        return list ? [list] : []
      })
    }
  },
  watch: {
    lat_lons () {
      this.close_lists()
      this.$nextTick(() => this.fit_runs(false))
    },
    // Zooming regroups the places; a list whose marker no longer exists is closed.
    markers (markers) {
      const has = key => markers.some(marker => marker.key === key)
      if (this.pinned_key !== null && !has(this.pinned_key)) this.pinned_key = null
      if (this.hover_key !== null && !has(this.hover_key)) this.hover_key = null
    }
  },
  mounted () {
    this.fit_runs(false)
  },
  beforeUnmount () {
    clearTimeout(this.linger_timer)
  },
  methods: {
    plural,
    radius_of (marker) {
      return MARKER_RADII.find(([runs]) => marker.runs >= runs)[1]
    },
    marker_label (marker) {
      const where = marker.places.length > 1 ? `at ${plural(marker.places.length, 'place')}` : 'collected here'
      return `${plural(marker.runs, 'run')} ${where}. Press Enter to list them.`
    },
    // What a marker's list shows and where it sits over the map; null while the marker is out of view.
    list_of (marker, pinned) {
      const left = ((this.view.x + this.view.k * marker.x) / MAP_WIDTH) * 100
      const top = ((this.view.y + this.view.k * marker.y) / MAP_HEIGHT) * 100
      if (left < 0 || left > 100 || top < 0 || top > 100) return null
      const summary = runsAt(this.lat_lons, marker.places)
      let room = RUNS_LISTED
      const studies = summary.studies.flatMap(study => {
        if (room <= 0) return []
        const runs = study.runs.slice(0, room)
        room -= study.runs.length
        return [{ title: study.title, runs }]
      })
      const shift = left < EDGE_PERCENT ? '-12%' : left > 100 - EDGE_PERCENT ? '-88%' : '-50%'
      return {
        marker,
        pinned,
        studies,
        one_study: summary.studies.length === 1,
        more: Math.max(0, summary.total - RUNS_LISTED),
        title: marker.places.length > 1 ? `${plural(summary.total, 'run')} at ${plural(summary.places, 'place')}` : `${plural(summary.total, 'run')} collected here`,
        below: top < BELOW_ABOVE_PERCENT,
        style: { left: `${left}%`, top: `${top}%`, '--shift': shift, '--gap': `${this.radius_of(marker) + POPUP_GAP_PX}px` }
      }
    },
    // A mouse previews on hover; touch and keyboard pin with a tap or Enter.
    preview (marker, event) {
      if (event.pointerType !== 'mouse') return
      clearTimeout(this.linger_timer)
      this.hover_key = marker.key
    },
    // Closes the previewed list shortly, unless the pointer reaches the list or its marker first.
    linger_preview () {
      clearTimeout(this.linger_timer)
      this.linger_timer = setTimeout(() => { this.hover_key = null }, PREVIEW_LINGER_MS)
    },
    hold_preview (list) {
      if (!list.pinned) clearTimeout(this.linger_timer)
    },
    release_preview (list) {
      if (!list.pinned) this.linger_preview()
    },
    // A click on a marker keeps its list open; a click on it again, or anywhere else on the map, closes it.
    pin (marker) {
      this.pinned_key = this.pinned_key === marker.key ? null : marker.key
    },
    close_lists () {
      clearTimeout(this.linger_timer)
      this.hover_key = null
      this.pinned_key = null
    },
    lon_lats (places) {
      return places.map(index => this.lat_lons[index]).filter(Boolean).map(place => [place.lat_lon[1], place.lat_lon[0]])
    },
    separate (marker) {
      const places = this.lon_lats(marker.places)
      this.close_lists()
      if (this.$refs.map) this.$refs.map.fit_places(places, { padding: FIT_PADDING_PX })
    },
    // Every place in view. A project with a single place opens on the whole world, as the run page does.
    fit_runs (animate = true) {
      const map = this.$refs.map
      if (!map) return
      this.close_lists()
      if (this.points.length < 2) {
        map.zoom_world(animate)
        return
      }
      map.fit_places(this.lon_lats(this.points.map(point => point.place)), { maxScale: FIT_MAX_SCALE, padding: FIT_PADDING_PX, animate })
    },
    zoom_world () {
      this.close_lists()
      if (this.$refs.map) this.$refs.map.zoom_world()
    }
  }
}
</script>

<style scoped>
.runs-marker { cursor: pointer; outline: none; }
.runs-marker-disc { stroke: var(--color-white); stroke-width: 2; }
.runs-marker:hover .runs-marker-disc, .runs-marker:focus-visible .runs-marker-disc { stroke-width: 3; }
.runs-marker.is-pinned .runs-marker-disc { stroke: #1b2a3a; stroke-width: 3; }
.runs-marker-count { font-size: 11px; font-weight: 700; fill: var(--color-white); text-anchor: middle; dominant-baseline: central; pointer-events: none; user-select: none; }
.runs-flat-popup {
  position: absolute;
  z-index: 3;
  box-sizing: border-box;
  width: max-content;
  max-width: min(320px, 80%);
  padding: 0.7rem 0.9rem;
  font-size: 0.85rem;
  line-height: 1.4;
  overflow-wrap: anywhere;
  background: var(--color-white);
  border-radius: 3px;
  box-shadow: 0 1px 2px var(--black-10), 0 4px 14px var(--black-20);
  transform: translate(var(--shift), calc(-100% - var(--gap)));
}
.runs-flat-popup.is-below { transform: translate(var(--shift), var(--gap)); }
.runs-flat-popup-close { position: absolute; top: 0.1rem; right: 0.1rem; width: 1.6rem; height: 1.6rem; padding: 0; font: inherit; font-size: 1.1rem; line-height: 1; color: hsl(0, 0%, 35%); background: none; border: 0; border-radius: 2px; cursor: pointer; }
.runs-flat-popup-close:hover { background: #f2f2f2; }
.runs-flat-popup-close:focus-visible { outline: 2px solid var(--color-focus); }
</style>
