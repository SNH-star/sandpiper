<template>
  <div ref="container" class="runs-globe-canvas" role="application" :aria-label="label"></div>
</template>

<script>
// The globe view of the project page's map (see ProjectRunsMap): the run page's globe, with one numbered marker
// per place the project's runs were collected at. Places close together on screen share one marker, numbered with their runs in total, and
// separate on zooming in. Hovering a marker lists its runs; clicking keeps the list open.
import { markRaw } from 'vue'
import { Map as MapLibreMap, NavigationControl, Popup, ScaleControl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import '@/components/runsPopup.css'
import { BASE_STYLES, SAMPLE_MARKER_COLOUR, decorateBase, maritimeBorders } from '@/components/mapStyles'
import { placesToGeoJson, runsAt, boundsOf, plural } from '@/utils/runPlaces'

// Far enough out for the whole globe to fit in the frame; the map zooms out no further than this.
const WORLD_ZOOM = 0.6
const GLOBE = { type: 'globe' }
// A project with a single place opens as the run page does; one with several is fitted, but never closer than this.
const ONE_PLACE_ZOOM = 2
const FIT_MAX_ZOOM = 6
const FIT_PADDING_PX = 70
// The view of all runs is then pulled back by this many presses of the − button, to show more of the surroundings.
const FIT_STEPS_OUT = 2
// The globe never opens further out than this, where it fills the frame: any further and it is a small ball.
// Runs on its far side are then out of sight until it is turned, or until 'All runs' pulls back to hold them.
const OPENING_MIN_ZOOM = 2
// Places within this many pixels of each other share a marker, until this zoom.
const MERGE_RADIUS_PX = 36
const MERGE_UNTIL_ZOOM = 14
// More runs than this in one list are counted, not listed.
const RUNS_LISTED = 30
const POPUP_OFFSET_PX = 14
// How long a previewed list stays after the pointer leaves its marker, so the pointer can cross the gap onto
// the list; while the pointer is on the list it stays open.
const PREVIEW_LINGER_MS = 350
const SOURCE = 'project-runs'
const MARKER_LAYER = 'project-runs-marker'
// A marker grows a little with its runs: 10 px for under ten, up to 20 px for a thousand.
const MARKER_RADIUS = ['step', ['get', 'runs'], 10, 10, 13, 100, 16, 1000, 20]
const LAYERS = [
  { id: MARKER_LAYER, type: 'circle', source: SOURCE, paint: { 'circle-radius': MARKER_RADIUS, 'circle-color': SAMPLE_MARKER_COLOUR, 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 2 } },
  {
    id: 'project-runs-count',
    type: 'symbol',
    source: SOURCE,
    layout: { 'text-field': ['to-string', ['get', 'runs']], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-allow-overlap': true, 'text-ignore-placement': true },
    paint: { 'text-color': '#ffffff' }
  }
]

function element (tag, className, text) {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

export default {
  name: 'ProjectRunsGlobe',
  props: {
    // [{ lat_lon: [lat, lon], samples: { study title: [run accession, ...] } }, ...]
    lat_lons: { type: Array, default: () => [] },
    // Which base map to show: 'map' (streets) or 'satellite'.
    base: { type: String, default: 'map', validator: value => value in BASE_STYLES },
    label: { type: String, default: 'Globe of where this project\'s runs were collected' }
  },
  computed: {
    places () { return placesToGeoJson(this.lat_lons) }
  },
  watch: {
    base () {
      this.close_popups()
      if (this.map) this.map.setStyle(BASE_STYLES[this.base])
    },
    lat_lons () {
      this.close_popups()
      const source = this.map && this.map.getSource(SOURCE)
      if (source) source.setData(this.places)
      this.fit_runs(false, OPENING_MIN_ZOOM)
    }
  },
  mounted () {
    const map = markRaw(new MapLibreMap({
      container: this.$refs.container,
      style: BASE_STYLES[this.base],
      center: this.world_centre(),
      zoom: WORLD_ZOOM,
      minZoom: WORLD_ZOOM,
      maxPitch: 0,
      dragRotate: false,
      cooperativeGestures: true,
      attributionControl: { compact: true }
    }))
    this.map = map
    // The markers the previewed and the pinned list belong to. A list is gathered in the background, so each
    // is checked against these when it arrives and dropped if the reader has moved on.
    this.hover_key = null
    this.pinned_key = null
    map.touchZoomRotate.disableRotation()
    // A change of base map drops every layer and the projection, so both are put back each time a style loads.
    map.on('style.load', () => {
      map.setProjection(GLOBE)
      decorateBase(map, this.base)
      maritimeBorders(map, this.base === 'satellite')
      this.add_markers()
    })
    map.addControl(new NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(new ScaleControl({ unit: 'metric' }), 'bottom-left')
    map.on('mousemove', MARKER_LAYER, event => this.preview(event))
    map.on('mouseleave', MARKER_LAYER, () => {
      map.getCanvas().style.cursor = ''
      this.linger_preview()
    })
    map.on('click', event => this.pin(event))
    this.fit_runs(false, OPENING_MIN_ZOOM)
  },
  beforeUnmount () {
    this.close_popups()
    if (this.map) this.map.remove()
    this.map = null
  },
  methods: {
    add_markers () {
      if (!this.map.getSource(SOURCE)) {
        this.map.addSource(SOURCE, {
          type: 'geojson',
          data: this.places,
          cluster: true,
          clusterRadius: MERGE_RADIUS_PX,
          clusterMaxZoom: MERGE_UNTIL_ZOOM,
          // A shared marker carries its places' runs in total, under the name a single place uses.
          clusterProperties: { runs: ['+', ['get', 'runs']] }
        })
      }
      LAYERS.forEach(layer => { if (!this.map.getLayer(layer.id)) this.map.addLayer(layer) })
    },
    // Every run in view, though never further out than `minZoom`.
    fit_runs (animate = true, minZoom = WORLD_ZOOM) {
      const bounds = boundsOf(this.lat_lons)
      if (!this.map || !bounds) return
      const [[west, south], [east, north]] = bounds
      const onePlace = west === east && south === north
      const fitted = onePlace
        ? { center: [west, south], zoom: ONE_PLACE_ZOOM + FIT_STEPS_OUT }
        : this.map.cameraForBounds(bounds, { padding: FIT_PADDING_PX, maxZoom: FIT_MAX_ZOOM })
      // No view holds the runs when the map has no size yet; it is then left as it is.
      if (!fitted) return
      this.map.easeTo({ center: fitted.center, zoom: Math.max(minZoom, fitted.zoom - FIT_STEPS_OUT), animate })
    },
    // The whole globe, turned to the side the runs are on.
    world_centre () {
      const bounds = boundsOf(this.lat_lons)
      return bounds ? [(bounds[0][0] + bounds[1][0]) / 2, 20] : [0, 20]
    },
    zoom_world () {
      if (this.map) this.map.easeTo({ center: this.world_centre(), zoom: WORLD_ZOOM })
    },
    // The indexes (into `lat_lons`) of the places a marker stands for: one, or every place sharing it.
    async places_of (feature) {
      if (!feature.properties.cluster) return [feature.properties.place]
      const leaves = await this.map.getSource(SOURCE).getClusterLeaves(feature.properties.cluster_id, feature.properties.point_count, 0)
      return leaves.map(leaf => leaf.properties.place)
    },
    // Where to anchor a marker's list: on the copy of the world the pointer is over.
    anchor_of (feature, pointer) {
      const [lon, lat] = feature.geometry.coordinates
      return [lon + 360 * Math.round((pointer.lng - lon) / 360), lat]
    },
    key_of (feature) {
      return feature.properties.cluster ? `shared-${feature.properties.cluster_id}` : `place-${feature.properties.place}`
    },
    // Opens a marker's list; null if it could not be gathered or the map has gone meanwhile.
    async open_list (feature, pointer, pinned) {
      let summary
      try {
        summary = runsAt(this.lat_lons, await this.places_of(feature))
      } catch (error) {
        console.error('Could not list the runs of a map marker', error)
        return null
      }
      if (!this.map) return null
      const popup = new Popup({
        closeButton: pinned,
        closeOnClick: false,
        offset: POPUP_OFFSET_PX,
        maxWidth: '320px',
        className: pinned ? 'runs-popup' : 'runs-popup is-preview'
      })
      return popup.setLngLat(this.anchor_of(feature, pointer)).setDOMContent(this.list_content(summary, feature, pinned)).addTo(this.map)
    },
    async preview (event) {
      this.map.getCanvas().style.cursor = 'pointer'
      const feature = event.features[0]
      const key = this.key_of(feature)
      if (key === this.pinned_key) return
      clearTimeout(this.linger_timer)
      if (key === this.hover_key) return
      this.end_preview()
      this.hover_key = key
      const popup = await this.open_list(feature, event.lngLat, false)
      if (!popup) return
      // The pointer may have left, or a click may have pinned this marker, while its list was gathered.
      if (this.hover_key !== key || this.pinned_key === key) {
        popup.remove()
        return
      }
      this.hover_popup = popup
      // The list stays open while the pointer is on it, so a run in it can be clicked.
      popup.getElement().addEventListener('pointerenter', () => clearTimeout(this.linger_timer))
      popup.getElement().addEventListener('pointerleave', () => this.linger_preview())
    },
    // Closes the previewed list shortly, unless the pointer reaches the list or its marker first.
    linger_preview () {
      clearTimeout(this.linger_timer)
      this.linger_timer = setTimeout(() => this.end_preview(), PREVIEW_LINGER_MS)
    },
    end_preview () {
      clearTimeout(this.linger_timer)
      this.hover_key = null
      if (this.hover_popup) this.hover_popup.remove()
      this.hover_popup = null
    },
    // A click on a marker keeps its list open; a click anywhere else on the map closes it.
    async pin (event) {
      const [feature] = this.map.queryRenderedFeatures(event.point, { layers: [MARKER_LAYER] })
      this.close_popups()
      if (!feature) return
      const key = this.key_of(feature)
      this.pinned_key = key
      const popup = await this.open_list(feature, event.lngLat, true)
      // Another click may have come while the list was gathered: then this list is no longer wanted.
      if (this.pinned_key !== key) {
        if (popup) popup.remove()
        return
      }
      if (!popup) {
        this.pinned_key = null
        return
      }
      this.pinned_popup = popup
      popup.on('close', () => { if (this.pinned_popup === popup) { this.pinned_popup = null; this.pinned_key = null } })
    },
    close_popups () {
      this.end_preview()
      if (this.pinned_popup) this.pinned_popup.remove()
      this.pinned_popup = null
      this.pinned_key = null
    },
    // The list as page elements, never as HTML text: study titles come from the sequence archive as written.
    // The heading (the count, and the study when there is only one) and the notes stay put; only the runs scroll.
    list_content (summary, feature, pinned) {
      const box = element('div', 'runs-popup-body')
      const shared = Boolean(feature.properties.cluster)
      const oneStudy = summary.studies.length === 1
      const head = element('div', 'runs-popup-head')
      head.append(element('p', 'runs-popup-title',
        shared ? `${plural(summary.total, 'run')} at ${plural(summary.places, 'place')}` : `${plural(summary.total, 'run')} collected here`))
      if (oneStudy) head.append(element('p', 'runs-popup-study', summary.studies[0].title))
      const scroll = element('div', 'runs-popup-scroll')
      let room = RUNS_LISTED
      summary.studies.forEach(study => {
        if (room <= 0) return
        // With several studies each title stays at the top of the list while its own runs scroll under it.
        if (!oneStudy) scroll.append(element('p', 'runs-popup-study is-sticky', study.title))
        const list = element('ul', 'runs-popup-runs')
        study.runs.slice(0, room).forEach(accession => list.append(this.run_item(accession)))
        room -= study.runs.length
        scroll.append(list)
      })
      const foot = element('div', 'runs-popup-foot')
      if (summary.total > RUNS_LISTED) {
        foot.append(element('p', 'runs-popup-note', `and ${plural(summary.total - RUNS_LISTED, 'more run')}, all listed in the table below.`))
      }
      if (shared) foot.append(this.zoom_button(feature))
      if (!pinned) foot.append(element('p', 'runs-popup-note', 'Click the marker to keep this list open.'))
      box.append(head, scroll, foot)
      return box
    },
    run_item (accession) {
      const item = element('li')
      const link = element('a', '', accession)
      const route = { name: 'Run', params: { accession } }
      link.href = this.$router.resolve(route).href
      // A plain click moves within the site; with a modifier key the browser opens the link its own way.
      link.addEventListener('click', event => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
        event.preventDefault()
        this.$router.push(route)
      })
      item.append(link)
      return item
    },
    zoom_button (feature) {
      const button = element('button', 'runs-popup-zoom', 'Zoom in to separate these places')
      button.type = 'button'
      button.addEventListener('click', async () => {
        try {
          const zoom = await this.map.getSource(SOURCE).getClusterExpansionZoom(feature.properties.cluster_id)
          this.close_popups()
          this.map.easeTo({ center: feature.geometry.coordinates, zoom })
        } catch (error) {
          console.error('Could not zoom in on a map marker', error)
        }
      })
      return button
    }
  }
}
</script>

<style scoped>
/* Twice as wide as tall, the shape of the flat view it is exchanged with. */
.runs-globe-canvas { width: 100%; height: auto; aspect-ratio: 2 / 1; min-height: 300px; }
</style>

<!-- The lists are built outside Vue's templates, so their styles cannot be scoped. -->
<style>
.runs-popup .maplibregl-popup-content { padding: 0.7rem 0.9rem; font-size: 0.85rem; line-height: 1.4; }
</style>
