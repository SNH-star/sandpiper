<template>
  <section :id="compact ? null : 'sample-map'" :class="compact ? 'map-compact' : 'section container stat-figure'">
    <h3 v-if="!compact" class="subtitle is-3 stat-title"><a class="section-anchor" href="#sample-map">#</a> Where samples were collected</h3>
    <p v-if="!compact" class="stat-note">
      Runs with coordinates, grouped into {{ data.cell }}° squares. Choose a sample type below: each circle sits on one
      square and its area shows how many runs of that type the square holds, on one scale for both types so the two maps can be compared. The bars on the right count those runs
      by latitude. Hover or tap a circle for its counts.
    </p>
    <b-field grouped role="group" aria-label="Type of sample shown on the map" class="map-switch">
      <b-radio-button v-model="view" name="map-view" native-value="host_associated" type="is-primary" class="map-view-host_associated">Host-associated</b-radio-button>
      <b-radio-button v-model="view" name="map-view" native-value="ecological" type="is-primary" class="map-view-ecological">Ecological</b-radio-button>
    </b-field>
    <p class="map-key stat-note">
      <span><span class="swatch" :class="'swatch-' + view" aria-hidden="true"></span>{{ view_label }} runs</span>
      <span>Zoom: scroll over the map, pinch or use the + / − buttons; drag to pan. Zoom in for finer coastlines, a 5° grid and country names.</span>
      <span v-if="!compact">Full-size circle: {{ max_runs.toLocaleString('en-US') }} runs, the busiest square counting both types</span>
    </p>
    <div class="map-box">
      <div class="map-wrap" @pointerleave="clear($event)">
        <div class="map-zoom" role="group" aria-label="Map zoom">
          <button type="button" class="map-zoom-button" aria-label="Zoom in" :disabled="zoom.k >= ZOOM_MAX" @click="zoom_by(ZOOM_STEP)">+</button>
          <button type="button" class="map-zoom-button" aria-label="Zoom out" :disabled="zoom.k <= 1" @click="zoom_by(1 / ZOOM_STEP)">−</button>
          <button type="button" class="map-zoom-button map-zoom-reset" aria-label="Reset zoom" :disabled="zoom.k === 1" @click="zoom_reset">Reset</button>
        </div>
        <svg ref="svg" :viewBox="`0 0 ${compact ? W : W + STRIP + PAD_RIGHT} ${compact ? H : H + LABEL_ROW}`" role="img" :aria-label="aria">
          <defs>
            <clipPath :id="clip_map"><rect :width="W" :height="H" /></clipPath>
            <clipPath :id="clip_strip"><rect :x="W" :width="STRIP + PAD_RIGHT" :height="H" /></clipPath>
          </defs>
          <g :clip-path="`url(#${clip_map})`">
            <g :transform="map_transform">
              <rect :width="W" :height="H" class="map-sea" />
              <path :d="land_path" class="map-land" />
              <path :d="border_path" class="map-border" />
              <path :d="coast_path" class="map-coast" />
              <path v-if="zoom.k >= LABEL_ZOOM" :d="graticule_path" class="map-graticule" />
              <line :x1="0" :x2="W" :y1="equator" :y2="equator" class="map-equator" />
              <circle v-for="cell in bubbles" :key="cell.key" :cx="cell.x" :cy="cell.y" :r="cell.r"
                      class="map-bubble" :class="['bubble-' + view, { 'is-selected': selected && selected.key === cell.key, 'is-chosen': chosen.includes(cell.key) }]"
                      @pointerenter="pick($event, cell)" @click="activate(cell)"><title>{{ cell.title }}</title></circle>
              <text v-for="label in visible_labels" :key="label.name" :x="label.x" :y="label.y" class="map-country" :style="{ fontSize: (LABEL_SIZE / zoom.k) + 'px', strokeWidth: (3 / zoom.k) + 'px' }">{{ label.name }}</text>
            </g>
          </g>
          <g v-if="!compact" class="map-guides" aria-hidden="true">
            <g v-for="guide in guides" :key="guide.label">
              <line :x1="guide.x" :x2="guide.x" y1="0" :y2="H" class="map-guide" />
              <text :x="guide.x" :y="H + 13" class="map-guide-label">{{ guide.label }}</text>
            </g>
            <text :x="W + STRIP_GAP" :y="H + LABEL_ROW - 3" class="map-guide-title">Runs per latitude band</text>
          </g>
          <!-- The bars follow the map's vertical zoom and pan so each stays level with its band of latitude. -->
          <g v-if="!compact" :clip-path="`url(#${clip_strip})`">
            <g class="map-bands" :transform="strip_transform">
              <line :x1="W" :x2="W + STRIP" :y1="equator" :y2="equator" class="map-equator" />
              <rect v-for="band in bands" :key="band.lat" :x="W + STRIP_GAP" :y="band.y" :width="band.width" :height="band.h"
                    class="band" :class="'band-' + view"><title>{{ band.title }}</title></rect>
            </g>
          </g>
        </svg>
      </div>
      <p v-if="!compact || selected" class="stat-note map-hover" aria-live="polite">{{ selected ? selected.title : summary }}</p>
    </div>
  </section>
</template>

<script>
import { markRaw } from 'vue'
import * as d3 from 'd3'
import { feature, mesh } from 'topojson-client'
import countries110m from 'world-atlas/countries-110m.json'

// Coastlines and borders get finer as the map zooms in. The coarse set ships
// with the page; the finer ones load the first time they are needed.
const DETAIL_LEVELS = [
  { name: '10m', minZoom: 8, load: () => import('world-atlas/countries-10m.json') },
  { name: '50m', minZoom: 2.5, load: () => import('world-atlas/countries-50m.json') }
]
// From this zoom on, show a 5° grid and the names of countries big enough to hold them.
const LABEL_ZOOM = 3
const LABEL_SIZE = 11
const LABEL_CHAR_WIDTH = 0.6

const W = 960
const ZOOM_MAX = 16
const ZOOM_STEP = 1.6
const ZOOM_MS = 200
let nextMapId = 0
// Room to the right of the map for the latitude bars, and the gap before them.
const STRIP = 120
const STRIP_GAP = 14
// Room under the map for the bar scale's labels.
const LABEL_ROW = 34
// Extra width past the bars so the scale's caption is not cut off.
const PAD_RIGHT = 40
const R_MAX = 24
const R_MIN = 2.5
const VIEWS = {
  host_associated: { label: 'Host-associated' },
  ecological: { label: 'Ecological' }
}

// The largest 1, 2 or 5 times a power of ten that is at most value.
function roundDown (value) {
  const power = 10 ** Math.floor(Math.log10(value))
  return power * [5, 2, 1].find(step => step * power <= value)
}

const signed = value => (value < 0 ? '−' : '') + Math.abs(value)

export default {
  name: 'SampleMapChart',
  props: {
    data: { type: Object, required: true },
    // Search-page version: no heading, latitude bars or scale, and a click picks
    // the circle's square (emitted as 'toggle') instead of only previewing it.
    compact: { type: Boolean, default: false },
    selectable: { type: Boolean, default: false },
    chosen: { type: Array, default: () => [] }
  },
  emits: ['toggle', 'view-change'],
  data () {
    nextMapId += 1
    return {
      view: 'host_associated', selected: null, W, STRIP, STRIP_GAP, LABEL_ROW, PAD_RIGHT, ZOOM_MAX, ZOOM_STEP,
      zoom: { k: 1, x: 0, y: 0 }, LABEL_ZOOM, LABEL_SIZE,
      topology: markRaw(countries110m), clip_map: `map-clip-${nextMapId}`, clip_strip: `strip-clip-${nextMapId}`
    }
  },
  computed: {
    projection () {
      return d3.geoEquirectangular().fitExtent([[0, 0], [W, W / 2]], { type: 'Sphere' })
    },
    H () { return W / 2 },
    map_transform () { return `translate(${this.zoom.x} ${this.zoom.y}) scale(${this.zoom.k})` },
    strip_transform () { return `translate(0 ${this.zoom.y}) scale(1 ${this.zoom.k})` },
    equator () { return this.projection([0, 0])[1] },
    view_label () { return VIEWS[this.view].label },
    // Squares holding at least one run of the chosen type, with that count.
    view_cells () {
      return this.data.cells
        .map(cell => ({ ...cell, count: cell[this.view] }))
        .filter(cell => cell.count > 0)
    },
    total () { return this.view_cells.reduce((sum, cell) => sum + cell.count, 0) },
    // One scale for both views, set by the busiest square counting every run, so
    // the host-associated and ecological circles of a square add up to its total.
    max_runs () { return Math.max(1, ...this.data.cells.map(cell => cell.runs)) },
    // Reference lines for the latitude bars, at round run counts: the largest
    // 1, 2 or 5 times a power of ten that fits the busiest band, and half of it.
    guides () {
      const room = STRIP - STRIP_GAP - 4
      const top = roundDown(this.max_band_runs)
      return [top / 2, top].map(runs => ({
        x: W + STRIP_GAP + (room * runs) / this.max_band_runs,
        label: runs >= 1000 ? `${runs / 1000}k` : `${runs}`
      }))
    },
    max_band_runs () {
      const byLat = new Map()
      this.data.cells.forEach(cell => byLat.set(cell.lat, (byLat.get(cell.lat) || 0) + cell.runs))
      return Math.max(1, ...byLat.values())
    },
    summary () {
      return `${this.total.toLocaleString('en-US')} ${this.view_label.toLowerCase()} runs with coordinates, in ${this.view_cells.length} squares.`
    },
    aria () {
      return `${this.summary} Drawn as circles sized by run count.`
    },
    land_path () {
      const land = this.topology.objects.land || this.topology.objects.countries
      return d3.geoPath(this.projection)(feature(this.topology, land))
    },
    border_path () {
      const borders = mesh(this.topology, this.topology.objects.countries, (a, b) => a !== b)
      return d3.geoPath(this.projection)(borders)
    },
    coast_path () {
      return d3.geoPath(this.projection)(mesh(this.topology, this.topology.objects.land))
    },
    graticule_path () {
      return d3.geoPath(this.projection)(d3.geoGraticule().step([this.data.cell, this.data.cell])())
    },
    // Each country's name and the box it fills, in map units (before zoom).
    country_labels () {
      const path = d3.geoPath(this.projection)
      return feature(this.topology, this.topology.objects.countries).features
        .filter(country => country.properties && country.properties.name)
        .map(country => {
          const [[x0, y0], [x1, y1]] = path.bounds(country)
          return { name: country.properties.name, x: (x0 + x1) / 2, y: (y0 + y1) / 2, width: x1 - x0 }
        })
        .filter(label => Number.isFinite(label.x) && Number.isFinite(label.y))
    },
    // Names that fit inside their country and sit in the current view.
    visible_labels () {
      if (this.zoom.k < LABEL_ZOOM) return []
      const { k, x, y } = this.zoom
      const onScreen = (value, offset, limit) => value * k + offset >= 0 && value * k + offset <= limit
      return this.country_labels.filter(label =>
        label.width * k >= label.name.length * LABEL_SIZE * LABEL_CHAR_WIDTH &&
        onScreen(label.x, x, W) && onScreen(label.y, y, this.H))
    },
    // Largest first, so the small circles are drawn on top and stay hoverable.
    bubbles () {
      const size = this.data.cell
      return [...this.view_cells].sort((a, b) => b.count - a.count).map(cell => {
        const [x, y] = this.projection([cell.lon + size / 2, cell.lat + size / 2])
        return {
          key: `${cell.lat}:${cell.lon}`,
          x, y,
          r: Math.max(R_MIN, R_MAX * Math.sqrt(cell.count / this.max_runs)),
          title: this.describe(cell)
        }
      })
    },
    // Runs of the chosen type in each band of latitude.
    bands () {
      const size = this.data.cell
      const byLat = new Map()
      this.view_cells.forEach(cell => byLat.set(cell.lat, (byLat.get(cell.lat) || 0) + cell.count))
      const scale = (STRIP - STRIP_GAP - 4) / this.max_band_runs
      return [...byLat].map(([lat, runs]) => {
        const top = this.projection([0, lat + size])[1]
        const bottom = this.projection([0, lat])[1]
        return {
          lat,
          y: top + 0.5,
          h: Math.max(1, bottom - top - 1),
          width: runs * scale,
          title: `Latitude ${signed(lat)}° to ${signed(lat + size)}°: ${runs.toLocaleString('en-US')} ${this.view_label.toLowerCase()} runs`
        }
      })
    }
  },
  created () {
    this.detail_cache = {}
    this.detail_loading = new Set()
  },
  mounted () {
    this.zoom_behaviour = d3.zoom()
      .scaleExtent([1, ZOOM_MAX])
      .translateExtent([[0, 0], [W, this.H]])
      .extent([[0, 0], [W, this.H]])
      // Scrolling over the map zooms it. One-finger swipes keep scrolling the page
      // until the map is zoomed in, so touch users are never stuck on it.
      .filter(event => {
        if (event.type === 'wheel') return true
        if (event.type.startsWith('touch')) return event.touches.length > 1 || this.zoom.k > 1
        return !event.button
      })
      .on('zoom', event => { this.zoom = { k: event.transform.k, x: event.transform.x, y: event.transform.y } })
    d3.select(this.$refs.svg).call(this.zoom_behaviour)
  },
  beforeUnmount () {
    d3.select(this.$refs.svg).on('.zoom', null)
  },
  watch: {
    view () { this.selected = null; this.$emit('view-change', this.view) },
    'zoom.k' () { this.ensure_detail() }
  },
  methods: {
    describe (cell) {
      const size = this.data.cell
      const known = cell.known === null ? 'known species fraction not available' : `mean known species fraction ${cell.known}% (all ${cell.runs.toLocaleString('en-US')} runs in the square)`
      const place = `latitude ${signed(cell.lat)}° to ${signed(cell.lat + size)}°, longitude ${signed(cell.lon)}° to ${signed(cell.lon + size)}°`
      return `${place}: ${cell[this.view].toLocaleString('en-US')} ${this.view_label.toLowerCase()} runs, ${known}`
    },
    // Swap in the finest coastline set the zoom calls for, loading it on first use.
    ensure_detail () {
      const wanted = DETAIL_LEVELS.find(level => this.zoom.k >= level.minZoom)
      if (!wanted) {
        this.topology = markRaw(countries110m)
        return
      }
      if (this.detail_cache[wanted.name]) {
        this.topology = this.detail_cache[wanted.name]
        return
      }
      if (this.detail_loading.has(wanted.name)) return
      this.detail_loading.add(wanted.name)
      wanted.load()
        .then(module => {
          this.detail_cache[wanted.name] = markRaw(module.default || module)
          this.ensure_detail()
        })
        .catch(error => console.error(`Could not load the ${wanted.name} map detail`, error))
        .finally(() => this.detail_loading.delete(wanted.name))
    },
    zoom_by (factor) {
      d3.select(this.$refs.svg).transition().duration(ZOOM_MS).call(this.zoom_behaviour.scaleBy, factor, [W / 2, this.H / 2])
    },
    zoom_reset () {
      d3.select(this.$refs.svg).transition().duration(ZOOM_MS).call(this.zoom_behaviour.transform, d3.zoomIdentity)
    },
    activate (cell) {
      if (this.selectable) this.$emit('toggle', cell.key)
      else this.selected = cell
    },
    // A mouse previews on hover; touch and pen select with a tap (see @click).
    pick (event, cell) {
      if (event.pointerType === 'mouse') this.selected = cell
    },
    clear (event) {
      if (event.pointerType === 'mouse') this.selected = null
    }
  }
}
</script>

<style scoped>
.stat-note { max-width: 62ch; font-size: 0.9rem; line-height: 1.5; color: var(--color-ink-muted); }
.section.container { padding-top: var(--space-8); padding-bottom: var(--space-4); }
.map-box { margin-top: var(--space-4); }
.map-wrap { position: relative; }
.map-wrap svg { display: block; width: 100%; height: auto; cursor: grab; }
.map-wrap svg:active { cursor: grabbing; }
.map-zoom { position: absolute; top: var(--space-2); left: var(--space-2); z-index: 2; display: flex; gap: 2px; }
.map-zoom-button { min-width: 2rem; height: 2rem; padding: 0 var(--space-2); font-size: 1rem; line-height: 1; color: var(--color-ink); background: var(--color-surface); border: 1px solid var(--color-rule); border-radius: var(--radius-bar); cursor: pointer; }
.map-zoom-reset { font-size: 0.8rem; }
.map-zoom-button:hover:not(:disabled), .map-zoom-button:focus-visible { border-color: var(--color-accent); }
.map-zoom-button:disabled { opacity: 0.45; cursor: default; }
.map-sea { fill: var(--color-map-sea); }
.map-land { fill: var(--color-map-land); }
.map-border { vector-effect: non-scaling-stroke; fill: none; stroke: var(--color-map-border); stroke-width: 0.8; }
.map-coast { vector-effect: non-scaling-stroke; fill: none; stroke: var(--color-map-coast); stroke-width: 1; }
.map-guide { stroke: var(--color-ink-muted); stroke-width: 0.8; opacity: 0.35; pointer-events: none; }
.map-guide-title { font-size: 11px; text-anchor: start; fill: var(--color-ink-muted); }
.map-guide-label { font-size: 11px; text-anchor: middle; fill: var(--color-ink-muted); }
.map-graticule { vector-effect: non-scaling-stroke; fill: none; stroke: var(--color-map-coast); stroke-width: 0.5; opacity: 0.35; pointer-events: none; }
.map-country { text-anchor: middle; dominant-baseline: middle; fill: var(--color-ink-muted); paint-order: stroke; stroke: var(--color-map-land); stroke-linejoin: round; pointer-events: none; user-select: none; }
.map-equator { vector-effect: non-scaling-stroke; stroke: var(--color-map-coast); stroke-width: 0.8; stroke-dasharray: 4 5; opacity: 0.55; pointer-events: none; }
.map-bubble { vector-effect: non-scaling-stroke; fill-opacity: 0.9; stroke: var(--color-ink); stroke-width: 0.6; cursor: pointer; touch-action: manipulation; }
.map-bubble.is-chosen { fill-opacity: 1; stroke: var(--color-accent); stroke-width: 3; }
.map-compact { margin-top: var(--space-3); }
.map-bubble:hover, .map-bubble.is-selected { fill-opacity: 1; stroke: var(--color-accent); stroke-width: 2.4; }
.band { vector-effect: non-scaling-stroke; stroke: var(--color-ink); stroke-width: 0.4; }
.band-host_associated, .bubble-host_associated { fill: var(--color-sample-host); }
.band-ecological, .bubble-ecological { fill: var(--color-sample-ecological); }
.map-switch { margin-top: var(--space-4); }
/* The selected button takes the colour its circles have on the map. */
.map-view-host_associated :deep(.button.is-selected),
.map-view-host_associated :deep(.button.is-selected:hover),
.map-view-host_associated :deep(.button.is-selected:focus) { background-color: var(--color-sample-host); border-color: var(--color-sample-host); color: #fff; }
.map-view-ecological :deep(.button.is-selected),
.map-view-ecological :deep(.button.is-selected:hover),
.map-view-ecological :deep(.button.is-selected:focus) { background-color: var(--color-sample-ecological); border-color: var(--color-sample-ecological); color: var(--color-ink); }
.map-key { display: flex; flex-wrap: wrap; gap: var(--space-1) var(--space-6); margin-top: var(--space-2); }
.swatch { display: inline-block; width: 0.8rem; height: 0.8rem; margin-right: var(--space-2); border-radius: 50%; border: 1px solid var(--color-ink); }
.swatch-host_associated { background: var(--color-sample-host); }
.swatch-ecological { background: var(--color-sample-ecological); }
.map-hover { box-sizing: border-box; min-height: 3.5rem; margin: var(--space-2) 0 0; padding: var(--space-2) var(--space-3); overflow-y: auto; max-width: none; }
.section-anchor:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { .map-bubble { transition: none; } }
</style>
