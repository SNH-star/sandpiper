<template>
  <section :id="compact ? null : 'sample-map'" :class="compact ? 'map-compact hex-map' : 'section container stat-figure hex-map'">
    <chart-download v-if="!compact" target="#sample-map" name="sample-locations" />
    <h3 v-if="!compact" class="subtitle is-3 stat-title"><a class="section-anchor" href="#sample-map">#</a> Where samples were collected</h3>
    <!-- Shown only with the hexagon data, because it quotes the hexagon size. -->
    <p v-if="has_hexes && !compact" class="stat-note">
      This map shows where the runs that have coordinates were collected. The map is divided into hexagons
      {{ data.width }}° across (about {{ hex_km }} km at the equator), and each hexagon is shaded by how many runs were
      collected inside it: the darker the hexagon, the more runs. Areas without a hexagon have no runs. Use the buttons
      below to switch between host-associated and ecological samples; both use the same colour scale, so the two maps
      can be compared. The bars on the right show how many runs fall in each {{ data.cell }}° band of latitude. Hover
      over a hexagon to see its run count, or click it to keep it selected.
    </p>
    <p v-if="!has_hexes" class="stat-note map-missing" role="alert">The map's hexagon counts were not returned by the server, so the density map cannot be drawn.</p>
    <template v-else>
      <b-field grouped role="group" aria-label="Type of sample shown on the map" class="map-switch">
        <b-radio-button v-model="view" :name="view_name" native-value="host_associated" type="is-primary" class="map-view-host_associated">Host-associated</b-radio-button>
        <b-radio-button v-model="view" :name="view_name" native-value="ecological" type="is-primary" class="map-view-ecological">Ecological</b-radio-button>
      </b-field>
      <p class="map-key stat-note">
        <span>
          <span class="ramp-swatch" :style="{ background: ramp_css }" aria-hidden="true"></span>
          {{ view_label }} runs per hexagon
        </span>
        <span class="export-skip">Zoom: hold Ctrl (⌘ on a Mac) and scroll over the map, or pinch; drag to pan. Zoom in for finer coastlines and country names. Reset returns to the whole world.</span>
      </p>
      <div class="map-box">
        <div class="map-wrap" @pointerleave="clear($event)">
          <div class="map-zoom">
            <button type="button" class="map-zoom-reset" aria-label="Reset zoom" :disabled="zoom.k === 1" @click="zoom_reset">Reset</button>
            <!-- The zoom level, shown only while the map is being zoomed and for a moment after. -->
            <span v-if="zoom_level_shown" class="map-zoom-level" aria-hidden="true">{{ Math.round(zoom.k * 100) }}%</span>
          </div>
          <svg ref="svg" :viewBox="`0 0 ${compact ? W : W + STRIP + PAD_RIGHT} ${H + LEGEND_ROW}`" role="img" :aria-label="aria">
            <defs>
              <clipPath :id="clip_map"><rect :width="W" :height="H" /></clipPath>
              <clipPath :id="clip_strip"><rect :x="W" :width="STRIP + PAD_RIGHT" :height="H" /></clipPath>
              <linearGradient :id="ramp_id" x1="0" y1="0" x2="1" y2="0">
                <stop v-for="stop in ramp_stops" :key="stop.offset" :offset="stop.offset" :stop-color="stop.colour" />
              </linearGradient>
            </defs>
            <g :clip-path="`url(#${clip_map})`">
              <g :transform="map_transform">
                <rect :width="W" :height="H" class="map-sea" />
                <path :d="land_path" class="map-land" />
                <!-- The band of latitude the selected hexagon lies in, across the map. -->
                <rect v-if="selected_band" :x="0" :width="W" :y="selected_band.y" :height="selected_band.h" class="map-band-shade" />
                <path v-for="hex in view_hexes" :key="hex.key" :d="hex_path" :transform="`translate(${hex.x} ${hex.y})`"
                      class="map-hex" :fill="hex.fill" :stroke="hex.fill"
                      @pointerenter="pick($event, hex)" @click="activate(hex)"><title>{{ hex.title }}</title></path>
                <path :d="border_path" class="map-border" />
                <path :d="coast_path" class="map-coast" />
                <line :x1="0" :x2="W" :y1="equator" :y2="equator" class="map-equator" />
                <!-- Picked for the search: a thick, white-edged dark border that shows on any shade. -->
                <g v-for="hex in chosen_hexes" :key="'chosen-' + hex.key" :transform="`translate(${hex.x} ${hex.y})`" class="map-chosen">
                  <path :d="hex_path" class="map-hex-outline is-chosen-halo" />
                  <path :d="hex_path" class="map-hex-outline is-chosen" />
                </g>
                <path v-if="selected" :d="hex_path" :transform="`translate(${selected.x} ${selected.y})`" class="map-hex-outline" :class="{ 'is-locked': locked }" />
                <text v-for="label in world_labels" :key="label.name" :x="label.x" :y="label.y" class="map-world-label" :class="label.ocean ? 'is-ocean' : 'is-continent'" :style="{ fontSize: (LABEL_SIZE + 2) / zoom.k + 'px' }">{{ label.text }}</text>
                <text v-for="label in visible_labels" :key="label.name" :x="label.x" :y="label.y" class="map-country" :style="{ fontSize: (LABEL_SIZE / zoom.k) + 'px', strokeWidth: (3 / zoom.k) + 'px' }">{{ label.name }}</text>
              </g>
            </g>
            <rect :width="W" :height="H" class="map-frame" />
            <g v-if="!compact" class="map-guides" aria-hidden="true">
              <g v-for="guide in guides" :key="guide.label">
                <line :x1="guide.x" :x2="guide.x" y1="0" :y2="H" class="map-guide" />
                <text :x="guide.x" :y="H + 13" class="map-guide-label">{{ guide.label }}</text>
              </g>
              <text :x="W + STRIP_GAP" :y="H + 31" class="map-guide-title">Runs per latitude band</text>
            </g>
            <!-- The bars follow the map's vertical zoom and pan so each stays level with its band of latitude. -->
            <g v-if="!compact" :clip-path="`url(#${clip_strip})`">
              <g class="map-bands" :transform="strip_transform">
                <line :x1="W" :x2="W + STRIP" :y1="equator" :y2="equator" class="map-equator" />
                <rect v-for="band in bands" :key="band.lat" :x="W + STRIP_GAP" :y="band.y" :width="band.width" :height="band.h"
                      class="band" :class="['band-' + view, { 'is-selected': selected_band && selected_band.lat === band.lat }]"><title>{{ band.title }}</title></rect>
              </g>
            </g>
            <!-- Colour scale, under the map. It stays fixed while the map zooms; the marker shows the hexagon under the pointer. -->
            <g class="map-legend" aria-hidden="true">
              <rect x="0" :y="legend_top" :width="W" :height="LEGEND_BAR" :fill="`url(#${ramp_id})`" class="legend-bar" />
              <g v-for="tick in legend_ticks" :key="tick.label">
                <line :x1="tick.x" :x2="tick.x" :y1="legend_top + LEGEND_BAR" :y2="legend_top + LEGEND_BAR + 4" class="legend-tick" />
                <text :x="tick.x" :y="legend_top + LEGEND_BAR + 15" class="legend-tick-label" :text-anchor="tick.anchor">{{ tick.label }}</text>
              </g>
              <text :x="W / 2" :y="legend_top + LEGEND_BAR + 32" class="legend-title">{{ view_label }} runs per hexagon</text>
              <g v-if="marker" class="legend-marker">
                <line :x1="marker.x" :x2="marker.x" :y1="legend_top" :y2="legend_top + LEGEND_BAR" class="legend-marker-line" />
                <polygon :points="marker.arrow" class="legend-marker-arrow" />
                <text :x="marker.label_x" :y="legend_top - 4" class="legend-marker-label" :text-anchor="marker.anchor">{{ marker.label }}</text>
              </g>
            </g>
          </svg>
        </div>
        <p class="stat-note map-hover" aria-live="polite">{{ hover_text }}</p>
      </div>
    </template>
  </section>
</template>

<script>
import ChartDownload from '@/components/statistics/ChartDownload.vue'
import { markRaw } from 'vue'
import * as d3 from 'd3'
import { mesh } from 'topojson-client'
import { DETAIL_LEVELS, COUNTRY_LABEL_ZOOM, landOf, worldLabels, countryLabelsOf, visibleCountryLabels } from '@/components/statistics/worldGeometry'
import countries110m from 'world-atlas/countries-110m.json'

const LABEL_SIZE = 11
const LABEL_CHAR_WIDTH = 0.6

const W = 960
const ZOOM_MAX = 16
const ZOOM_MS = 200
// How long the zoom level stays beside the Reset button after the last zoom step.
const ZOOM_LEVEL_SHOWN_MS = 1000
// How far one unit of wheel movement zooms, by the unit the browser reports: pixels, lines or pages.
// A mouse wheel notch is about 100 pixels, which makes one notch zoom by about 15%.
const WHEEL_ZOOM_PER_PIXEL = 0.002
const WHEEL_ZOOM_PER_LINE = 0.05
const WHEEL_ZOOM_PER_PAGE = 1
// A trackpad pinch arrives as Ctrl + scroll in steps of a few pixels, far smaller than a wheel notch,
// so those small steps are boosted to keep pinching responsive.
const PINCH_MAX_PIXELS = 20
const PINCH_BOOST = 10
let nextMapId = 0
// Room to the right of the map for the latitude bars, and the gap before them.
const STRIP = 120
const STRIP_GAP = 14
// Extra width past the bars so the scale's caption is not cut off.
const PAD_RIGHT = 40
// Room under the map for the colour scale: a gap for its marker, the bar, then its tick labels and title.
const LEGEND_GAP = 18
const LEGEND_BAR = 12
const LEGEND_ROW = 68
const MARKER_SIZE = 5
const KM_PER_DEGREE = 111
// Within this distance of the scale's right-hand end, the marker's count is written to its left.
const MARKER_FLIP_ROOM = 90
// Pale to dark, passing through each sample type's site colour (--color-sample-host and
// --color-sample-ecological). They are listed here because the colour scale is computed, not styled.
const VIEWS = {
  host_associated: { label: 'Host-associated', ramp: ['#cdaee6', '#b48fd0', '#9a6fb5', '#5f3a80', '#2c1440'] },
  ecological: { label: 'Ecological', ramp: ['#b3d39a', '#9dbf86', '#84a86f', '#4b6f39', '#1f3814'] }
}

// The largest 1, 2 or 5 times a power of ten that is at most value.
function roundDown (value) {
  const power = 10 ** Math.floor(Math.log10(value))
  return power * [5, 2, 1].find(step => step * power <= value)
}

const signed = value => (value < 0 ? '−' : '') + Math.abs(value)
const count_text = value => value.toLocaleString('en-US')
// "51.9° N" or "12° W": one decimal at most, and no sign.
const degrees = (value, positive, negative) => `${+Math.abs(value).toFixed(1)}° ${value < 0 ? negative : positive}`

export default {
  name: 'SampleHexMapChart',
  components: { ChartDownload },
  props: {
    // The statistics response's map: 5° `cells` for the latitude bars and `hexes` (`width` degrees across) for the map.
    data: { type: Object, required: true },
    // Search-page version: no heading, explanation or latitude bars, and with `selectable` a click picks
    // the hexagon for the search (emitted as 'toggle') instead of locking onto it. `chosen` lists the keys
    // ("lat:lon") of the hexagons picked under the sample type on show, which are outlined.
    compact: { type: Boolean, default: false },
    selectable: { type: Boolean, default: false },
    chosen: { type: Array, default: () => [] }
  },
  emits: ['toggle', 'view-change'],
  data () {
    nextMapId += 1
    return {
      view: 'host_associated', hovered: null, locked: null, zoom_level_shown: false, W, STRIP, STRIP_GAP, PAD_RIGHT, LEGEND_BAR, LEGEND_ROW,
      zoom: { k: 1, x: 0, y: 0 }, LABEL_SIZE,
      topology: markRaw(countries110m),
      clip_map: `hex-map-clip-${nextMapId}`, clip_strip: `hex-strip-clip-${nextMapId}`, ramp_id: `hex-ramp-${nextMapId}`,
      view_name: `hex-map-view-${nextMapId}`
    }
  },
  computed: {
    // The hexagon whose details are shown: the locked one if there is one, otherwise the one under the pointer.
    selected () { return this.locked || this.hovered },
    hover_text () {
      if (this.locked) return `Locked: ${this.locked.title} Click it again to release it, or click another hexagon.`
      if (!this.hovered) return this.summary
      const isPicked = this.selectable && this.chosen.includes(this.hovered.key)
      return isPicked ? `${this.hovered.title} Picked for the search: click it again to drop it.` : this.hovered.title
    },
    has_hexes () { return Array.isArray(this.data.hexes) && this.data.width > 0 },
    projection () {
      return d3.geoEquirectangular().fitExtent([[0, 0], [W, W / 2]], { type: 'Sphere' })
    },
    H () { return W / 2 },
    map_transform () { return `translate(${this.zoom.x} ${this.zoom.y}) scale(${this.zoom.k})` },
    strip_transform () { return `translate(0 ${this.zoom.y}) scale(1 ${this.zoom.k})` },
    equator () { return this.projection([0, 0])[1] },
    view_label () { return VIEWS[this.view].label },
    ramp () { return VIEWS[this.view].ramp },
    // The hexagon's width in kilometres at the equator, to the nearest ten.
    hex_km () { return Math.round(this.data.width * KM_PER_DEGREE / 10) * 10 },
    // A pointy-topped hexagon `data.width` degrees across, around the origin, in map units.
    hex_path () {
      const half = (this.data.width * W) / 360 / 2
      const radius = (2 * half) / Math.sqrt(3)
      return `M0,${-radius}L${half},${-radius / 2}L${half},${radius / 2}L0,${radius}L${-half},${radius / 2}L${-half},${-radius / 2}Z`
    },
    // One scale for both views, set by the busiest hexagon of either type, so the two maps can be compared.
    busiest () {
      return this.data.hexes.reduce((most, hex) => Math.max(most, hex.host_associated, hex.ecological), 1)
    },
    // Top of the colour scale: the first power of ten at or above the busiest hexagon (at least 10),
    // so the scale's labels run 1, 10, 100 and so on right to its end.
    max_runs () { return 10 ** Math.max(1, Math.ceil(Math.log10(this.busiest))) },
    colour () {
      return d3.scaleSequentialLog([1, this.max_runs], d3.piecewise(d3.interpolateRgb, this.ramp)).clamp(true)
    },
    ramp_stops () {
      return this.ramp.map((colour, index) => ({ colour, offset: index / (this.ramp.length - 1) }))
    },
    ramp_css () { return `linear-gradient(to right, ${this.ramp.join(', ')})` },
    // Hexagons holding at least one run of the chosen type, placed and coloured.
    view_hexes () {
      return this.data.hexes.filter(hex => hex[this.view] > 0).map(hex => {
        // Placed by hand, not with the projection, which would wrap a centre just past 180° to the far edge.
        const x = ((hex.lon + 180) * W) / 360
        const y = ((90 - hex.lat) * W) / 360
        const count = hex[this.view]
        return { key: `${hex.lat}:${hex.lon}`, lat: hex.lat, x, y, count, fill: this.colour(count), title: this.describe(hex, count) }
      })
    },
    // The picked hexagons that hold runs of the type on show.
    chosen_hexes () {
      return this.chosen.length ? this.view_hexes.filter(hex => this.chosen.includes(hex.key)) : []
    },
    total () { return this.view_hexes.reduce((sum, hex) => sum + hex.count, 0) },
    legend_top () { return this.H + LEGEND_GAP },
    // Every power of ten along the scale, left to right; the scale ends on one (see `max_runs`).
    legend_ticks () {
      const ticks = []
      for (let runs = 1; runs <= this.max_runs; runs *= 10) {
        const anchor = runs === 1 ? 'start' : runs === this.max_runs ? 'end' : 'middle'
        ticks.push({ x: this.legend_x(runs), label: count_text(runs), anchor })
      }
      return ticks
    },
    // Where the hexagon under the pointer sits on the colour scale: an arrow above the bar with its count beside it.
    marker () {
      if (!this.selected) return null
      const x = this.legend_x(this.selected.count)
      const tip = this.legend_top - 2
      const back = tip - MARKER_SIZE - 2
      // The count sits to the right of the arrow, or to its left near the right-hand end of the scale.
      const flip = x > W - MARKER_FLIP_ROOM
      return {
        x,
        arrow: `${x},${tip} ${x - MARKER_SIZE},${back} ${x + MARKER_SIZE},${back}`,
        label: `${count_text(this.selected.count)} ${this.selected.count === 1 ? 'run' : 'runs'}`,
        label_x: flip ? x - MARKER_SIZE - 3 : x + MARKER_SIZE + 3,
        anchor: flip ? 'end' : 'start'
      }
    },
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
      return `${count_text(this.total)} ${this.view_label.toLowerCase()} runs with coordinates, in ${count_text(this.view_hexes.length)} hexagons. Hover over a hexagon for its count, or click or tap one to ${this.selectable ? 'add it to the search' : 'lock onto it'}.`
    },
    aria () {
      return `${count_text(this.total)} ${this.view_label.toLowerCase()} runs with coordinates, drawn as ${count_text(this.view_hexes.length)} hexagons shaded by run count.`
    },
    land_path () {
      return d3.geoPath(this.projection)(landOf(this.topology))
    },
    border_path () {
      const borders = mesh(this.topology, this.topology.objects.countries, (a, b) => a !== b)
      return d3.geoPath(this.projection)(borders)
    },
    coast_path () {
      return d3.geoPath(this.projection)(mesh(this.topology, this.topology.objects.land))
    },
    // Each country's name on its largest piece, with that piece's width in map units.
    country_labels () {
      return countryLabelsOf(this.topology, this.projection)
    },
    // Continents and oceans, named while the whole world is in view.
    world_labels () {
      return this.zoom.k < COUNTRY_LABEL_ZOOM ? worldLabels(this.projection) : []
    },
    // Names that fit inside their country and sit in the current view.
    visible_labels () {
      if (this.zoom.k < COUNTRY_LABEL_ZOOM) return []
      return visibleCountryLabels(this.country_labels, this.zoom, W, this.H, LABEL_SIZE, LABEL_CHAR_WIDTH)
    },
    // The band of latitude the selected hexagon's centre lies in, as the bars below the map divide the globe.
    selected_band () {
      if (!this.selected) return null
      const size = this.data.cell
      const lat = Math.floor(this.selected.lat / size) * size
      const top = this.projection([0, lat + size])[1]
      const bottom = this.projection([0, lat])[1]
      return { lat, y: top, h: bottom - top }
    },
    // Runs of the chosen type in each band of latitude.
    bands () {
      const size = this.data.cell
      const byLat = new Map()
      this.data.cells.forEach(cell => {
        if (cell[this.view] > 0) byLat.set(cell.lat, (byLat.get(cell.lat) || 0) + cell[this.view])
      })
      const scale = (STRIP - STRIP_GAP - 4) / this.max_band_runs
      return [...byLat].map(([lat, runs]) => {
        const top = this.projection([0, lat + size])[1]
        const bottom = this.projection([0, lat])[1]
        return {
          lat,
          y: top + 0.5,
          h: Math.max(1, bottom - top - 1),
          width: runs * scale,
          title: `Latitude ${signed(lat)}° to ${signed(lat + size)}°: ${count_text(runs)} ${this.view_label.toLowerCase()} runs`
        }
      })
    }
  },
  created () {
    this.detail_cache = {}
    this.detail_loading = new Set()
  },
  mounted () {
    if (!this.has_hexes) return
    this.zoom_behaviour = d3.zoom()
      .scaleExtent([1, ZOOM_MAX])
      .translateExtent([[0, 0], [W, this.H]])
      .extent([[0, 0], [W, this.H]])
      // Scrolling zooms the map only while Ctrl (or ⌘) is held, so a plain scroll keeps moving the page.
      // A trackpad pinch arrives as a Ctrl + scroll, so it zooms too. One-finger swipes keep scrolling
      // the page until the map is zoomed in, so touch users are never stuck on it.
      .filter(event => {
        if (event.type === 'wheel') return event.ctrlKey || event.metaKey
        if (event.type.startsWith('touch')) return event.touches.length > 1 || this.zoom.k > 1
        return !event.button
      })
      // d3 multiplies every Ctrl + scroll by ten, which made one wheel notch jump a long way.
      .wheelDelta(event => {
        const perUnit = event.deltaMode === 1 ? WHEEL_ZOOM_PER_LINE : event.deltaMode ? WHEEL_ZOOM_PER_PAGE : WHEEL_ZOOM_PER_PIXEL
        const isPinch = event.deltaMode === 0 && Math.abs(event.deltaY) < PINCH_MAX_PIXELS
        return -event.deltaY * perUnit * (isPinch ? PINCH_BOOST : 1)
      })
      .on('zoom', event => { this.zoom = { k: event.transform.k, x: event.transform.x, y: event.transform.y } })
    d3.select(this.$refs.svg).call(this.zoom_behaviour)
  },
  beforeUnmount () {
    if (this.$refs.svg) d3.select(this.$refs.svg).on('.zoom', null)
    clearTimeout(this.zoom_level_timer)
  },
  watch: {
    view (view) {
      this.hovered = null
      this.locked = null
      this.$emit('view-change', view)
    },
    'zoom.k' () {
      this.ensure_detail()
      this.show_zoom_level()
    }
  },
  methods: {
    // Position along the colour scale of a run count: 1 at the left, the top of the scale at the right.
    legend_x (runs) {
      return (W * Math.log(runs)) / Math.log(this.max_runs)
    },
    describe (hex, count) {
      const place = `${degrees(hex.lat, 'N', 'S')}, ${degrees(hex.lon, 'E', 'W')}`
      return `${count_text(count)} ${this.view_label.toLowerCase()} ${count === 1 ? 'run' : 'runs'} in the hexagon centred near ${place}.`
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
    // Shows the zoom level, and hides it again once zooming has stopped for ZOOM_LEVEL_SHOWN_MS.
    show_zoom_level () {
      this.zoom_level_shown = true
      clearTimeout(this.zoom_level_timer)
      this.zoom_level_timer = setTimeout(() => { this.zoom_level_shown = false }, ZOOM_LEVEL_SHOWN_MS)
    },
    zoom_reset () {
      d3.select(this.$refs.svg).transition().duration(ZOOM_MS).call(this.zoom_behaviour.transform, d3.zoomIdentity)
    },
    // A mouse previews on hover. While a hexagon is locked the preview is ignored (see `selected`).
    pick (event, hex) {
      if (event.pointerType === 'mouse') this.hovered = hex
    },
    clear (event) {
      if (event.pointerType === 'mouse') this.hovered = null
    },
    // On the search page a click or tap picks the hexagon for the search, or drops it; elsewhere it locks onto it.
    activate (hex) {
      if (this.selectable) this.$emit('toggle', hex.key)
      else this.toggle_lock(hex)
    },
    // Clicking the locked hexagon again releases it.
    toggle_lock (hex) {
      this.locked = this.locked && this.locked.key === hex.key ? null : hex
    }
  }
}
</script>

<style scoped>
.stat-note { font-size: 0.9rem; line-height: 1.5; color: var(--color-ink-muted); }
.section.container { padding-top: var(--space-8); padding-bottom: var(--space-4); }
.map-missing { margin-top: var(--space-4); color: var(--color-ink); }
.map-box { margin-top: var(--space-4); }
.map-wrap { position: relative; }
.map-wrap svg { display: block; width: 100%; height: auto; overflow: visible; cursor: grab; }
.map-wrap svg:active { cursor: grabbing; }
.map-zoom { position: absolute; top: var(--space-2); left: var(--space-2); z-index: 2; display: flex; align-items: center; gap: var(--space-2); pointer-events: none; }
.map-zoom-level { font-size: 0.8rem; font-variant-numeric: tabular-nums; line-height: 2rem; color: var(--color-ink-muted); }
.map-zoom-reset { pointer-events: auto; height: 2rem; padding: 0 var(--space-2); font-size: 0.8rem; line-height: 1; color: var(--color-ink); background: var(--color-surface); border: 1px solid var(--color-rule); border-radius: var(--radius-bar); cursor: pointer; }
.map-zoom-reset:hover:not(:disabled), .map-zoom-reset:focus-visible { border-color: var(--color-accent); }
.map-zoom-reset:disabled { opacity: 0.45; cursor: default; }
.map-sea { fill: var(--color-hexmap-sea); }
.map-land { fill: var(--color-hexmap-land); }
.map-frame { fill: none; stroke: var(--color-ink-muted); stroke-width: 0.8; pointer-events: none; }
.map-border { vector-effect: non-scaling-stroke; fill: none; stroke: var(--color-hexmap-border); stroke-width: 0.8; pointer-events: none; }
.map-coast { vector-effect: non-scaling-stroke; fill: none; stroke: var(--color-hexmap-coast); stroke-width: 1.2; pointer-events: none; }
/* Each hexagon is stroked in its own colour so no hairline of map shows between neighbours. */
.map-hex { vector-effect: non-scaling-stroke; stroke-width: 0.5; cursor: pointer; touch-action: manipulation; }
.map-hex-outline { vector-effect: non-scaling-stroke; fill: none; stroke: var(--color-accent); stroke-width: 2.4; stroke-linejoin: round; pointer-events: none; }
/* A locked hexagon gets a heavier, darker ring than one that is only hovered. */
.map-hex-outline.is-locked { stroke: var(--color-ink); stroke-width: 3.2; }
.map-hex-outline.is-chosen-halo { stroke: #fff; stroke-width: 8; }
.map-hex-outline.is-chosen { stroke: var(--color-ink); stroke-width: 5; }
.map-compact { margin-top: var(--space-3); }
.map-guide { stroke: var(--color-ink-muted); stroke-width: 0.8; opacity: 0.35; pointer-events: none; }
.map-guide-title { font-size: 11px; text-anchor: start; fill: var(--color-ink-muted); }
.map-guide-label { font-size: 11px; text-anchor: middle; fill: var(--color-ink-muted); }
.map-country { text-anchor: middle; dominant-baseline: middle; fill: var(--color-ink); paint-order: stroke; stroke: var(--color-hexmap-land); stroke-linejoin: round; pointer-events: none; user-select: none; }
.map-world-label { text-anchor: middle; dominant-baseline: middle; pointer-events: none; user-select: none; }
.map-world-label.is-continent { fill: var(--color-ink); font-weight: 600; opacity: 0.7; paint-order: stroke; stroke: var(--color-hexmap-land); stroke-width: 3px; stroke-linejoin: round; }
.map-world-label.is-ocean { fill: hsl(205, 45%, 32%); font-style: italic; }
.map-equator { vector-effect: non-scaling-stroke; stroke: var(--color-ink-muted); stroke-width: 0.8; stroke-dasharray: 4 5; opacity: 0.55; pointer-events: none; }
.band { vector-effect: non-scaling-stroke; stroke: var(--color-ink); stroke-width: 0.4; }
.band.is-selected { stroke-width: 1.6; stroke: var(--color-accent); }
.map-band-shade { fill: var(--color-accent); opacity: 0.1; pointer-events: none; }
.band-host_associated { fill: var(--color-sample-host); }
.band-ecological { fill: var(--color-sample-ecological); }
.legend-bar { stroke: var(--color-ink-muted); stroke-width: 0.6; }
.legend-tick { stroke: var(--color-ink-muted); stroke-width: 0.8; }
.legend-tick-label { font-size: 11px; fill: var(--color-ink-muted); }
.legend-title { font-size: 11px; text-anchor: middle; fill: var(--color-ink-muted); }
.legend-marker-line { stroke: var(--color-ink); stroke-width: 1.6; }
.legend-marker-arrow { fill: var(--color-ink); }
.legend-marker-label { font-size: 11px; font-weight: 600; fill: var(--color-ink); paint-order: stroke; stroke: var(--color-surface); stroke-width: 3px; stroke-linejoin: round; }
.map-switch { margin-top: var(--space-4); }
/* The selected button takes the colour its hexagons and bars have on the map. */
.map-view-host_associated :deep(.button.is-selected),
.map-view-host_associated :deep(.button.is-selected:hover),
.map-view-host_associated :deep(.button.is-selected:focus) { background-color: var(--color-sample-host); border-color: var(--color-sample-host); color: #fff; }
.map-view-ecological :deep(.button.is-selected),
.map-view-ecological :deep(.button.is-selected:hover),
.map-view-ecological :deep(.button.is-selected:focus) { background-color: var(--color-sample-ecological); border-color: var(--color-sample-ecological); color: var(--color-ink); }
.map-key { display: flex; flex-direction: column; gap: var(--space-1); margin-top: var(--space-2); }
.ramp-swatch { display: inline-block; width: 3.5rem; height: 0.7rem; margin-right: var(--space-2); vertical-align: baseline; border: 1px solid var(--color-ink-muted); border-radius: 2px; }
.map-hover { box-sizing: border-box; min-height: 3.5rem; margin: var(--space-2) 0 0; padding: var(--space-2) var(--space-3); overflow-y: auto; max-width: none; }
.section-anchor:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
</style>
