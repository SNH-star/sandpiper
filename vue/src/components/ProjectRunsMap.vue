<template>
  <figure class="runs-map">
    <div class="runs-map-wrap">
      <div ref="container" class="runs-map-canvas" role="application" :aria-label="aria"></div>
      <div class="runs-map-modes" role="group" aria-label="Map options">
        <button type="button" class="runs-map-mode" :class="{ 'is-active': base === 'map' }" :aria-pressed="String(base === 'map')" @click="base = 'map'">Map</button>
        <button type="button" class="runs-map-mode" :class="{ 'is-active': base === 'satellite' }" :aria-pressed="String(base === 'satellite')" @click="base = 'satellite'">Satellite</button>
        <button type="button" class="runs-map-mode runs-map-mode-gap" @click="fit_runs(true)">All runs</button>
        <button type="button" class="runs-map-mode" @click="zoom_world">World</button>
      </div>
    </div>
  </figure>
</template>

<script>
// The project page's map: the run page's base map, with one numbered marker per place the project's runs were
// collected at. Places close together on screen share one marker, numbered with their runs in total, and
// separate on zooming in. Hovering a marker lists its runs; clicking keeps the list open.
import { markRaw } from 'vue'
import { Map as MapLibreMap, NavigationControl, Popup, ScaleControl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { BASE_STYLES, SAMPLE_MARKER_COLOUR, decorateBase, maritimeBorders } from '@/components/mapStyles'
import { placesToGeoJson, runsAt, boundsOf } from '@/utils/runPlaces'

const WORLD_VIEW = { center: [0, 20], zoom: 0.6 }
// A project with a single place opens as the run page does; one with several is fitted, but never closer than this.
const ONE_PLACE_ZOOM = 2
const FIT_MAX_ZOOM = 6
const FIT_PADDING_PX = 70
// The view of all runs is then pulled back by one press of the − button, to show more of the surroundings.
const FIT_STEPS_OUT = 1
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

const plural = (count, noun) => `${count.toLocaleString('en-US')} ${noun}${count === 1 ? '' : 's'}`

function element (tag, className, text) {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

export default {
  name: 'ProjectRunsMap',
  props: {
    // [{ lat_lon: [lat, lon], samples: { study title: [run accession, ...] } }, ...]
    lat_lons: { type: Array, default: () => [] }
  },
  data () {
    return { base: 'map' }
  },
  computed: {
    places () { return placesToGeoJson(this.lat_lons) },
    aria () {
      const runs = this.places.features.reduce((total, feature) => total + feature.properties.runs, 0)
      return `Map of where this project's runs were collected: ${plural(runs, 'run')} at ${plural(this.places.features.length, 'place')}. The runs are also listed in the table below.`
    }
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
      this.fit_runs(false)
    }
  },
  mounted () {
    const map = markRaw(new MapLibreMap({
      container: this.$refs.container,
      style: BASE_STYLES.map,
      ...WORLD_VIEW,
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
    // A change of base map drops every layer, so the markers are put back each time a style loads.
    map.on('style.load', () => {
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
    this.fit_runs(false)
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
    fit_runs (animate) {
      const bounds = boundsOf(this.lat_lons)
      if (!this.map || !bounds) return
      const [[west, south], [east, north]] = bounds
      const onePlace = west === east && south === north
      const fitted = onePlace
        ? { center: [west, south], zoom: ONE_PLACE_ZOOM }
        : this.map.cameraForBounds(bounds, { padding: FIT_PADDING_PX, maxZoom: FIT_MAX_ZOOM })
      // No view holds the runs when the map has no size yet; it is then left as it is.
      if (!fitted) return
      this.map.easeTo({ center: fitted.center, zoom: Math.max(0, fitted.zoom - FIT_STEPS_OUT), animate })
    },
    zoom_world () {
      if (this.map) this.map.easeTo(WORLD_VIEW)
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
.runs-map { margin: 0 0 1rem; }
.runs-map-wrap { position: relative; }
.runs-map-canvas { width: 100%; height: 520px; border: 1px solid var(--color-rule, hsl(0, 0%, 88%)); border-radius: 2px; }
.runs-map-modes { position: absolute; top: 10px; left: 10px; display: flex; gap: 2px; }
.runs-map-mode {
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
.runs-map-mode-gap { margin-left: 0.5rem; }
.runs-map-mode:hover { border-color: #00796b; }
.runs-map-mode.is-active { color: #fff; background: #00796b; border-color: #00796b; }
.runs-map-mode:focus-visible { outline: 2px solid #3273dc; outline-offset: 2px; }
@media (max-width: 600px) {
  .runs-map-canvas { height: 300px; }
  .runs-map-mode { min-height: 2.75rem; }
}
</style>

<!-- The lists are built outside Vue's templates, so their styles cannot be scoped. -->
<style>
.runs-popup .maplibregl-popup-content { padding: 0.7rem 0.9rem; font-size: 0.85rem; line-height: 1.4; }
.runs-popup-scroll { max-height: 180px; margin-top: 0.3rem; overflow-y: auto; }
.runs-popup-title { margin: 0 1rem 0.3rem 0; font-weight: 600; }
.runs-popup-study { margin: 0 0 0.1rem; color: hsl(0, 0%, 35%); }
.runs-popup-study.is-sticky { position: sticky; top: 0; padding: 0.3rem 0 0.1rem; background: #fff; }
.runs-popup-runs { margin: 0; padding-left: 1.1rem; list-style: disc; }
.runs-popup-note { margin: 0.4rem 0 0; font-size: 0.8rem; color: hsl(0, 0%, 40%); }
.runs-popup-zoom { margin-top: 0.5rem; padding: 0.25rem 0.6rem; font: inherit; font-size: 0.8rem; color: #363636; background: #fff; border: 1px solid #c8c8c8; border-radius: 2px; cursor: pointer; }
.runs-popup-zoom:hover { border-color: #00796b; }
</style>
