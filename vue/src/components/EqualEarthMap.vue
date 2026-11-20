<template>
  <div ref="box" class="flat-map">
    <svg ref="svg" :viewBox="`0 0 ${W} ${H}`" role="img" :aria-label="label" @click="$emit('map-click')">
      <g :transform="map_transform">
        <path :d="sphere_path" class="flat-sea" />
        <path :d="graticule_path" class="flat-graticule" />
        <path :d="land_path" class="flat-land" />
        <path :d="border_path" class="flat-border" />
        <path :d="coast_path" class="flat-coast" />
        <path :d="sphere_path" class="flat-outline" />
        <text v-for="name in world_labels" :key="name.name" :x="name.x" :y="name.y" class="flat-world-label"
              :class="name.ocean ? 'is-ocean' : 'is-continent'" :style="{ fontSize: (LABEL_SIZE + 1) * scale + 'px' }">{{ name.text }}</text>
        <text v-for="name in visible_labels" :key="name.name" :x="name.x" :y="name.y" class="flat-country"
              :style="{ fontSize: LABEL_SIZE * scale + 'px', strokeWidth: 3 * scale + 'px' }">{{ name.name }}</text>
        <!-- What the page marks on the map. `scale` is the map units to one pixel of screen, so a marker
             drawn `scale` times its size keeps that size on screen at every zoom and width. -->
        <slot :scale="scale" />
      </g>
    </svg>
    <div class="flat-zoom" role="group" aria-label="Zoom the map">
      <button type="button" class="flat-zoom-button" aria-label="Zoom in" title="Zoom in" :disabled="zoom.k >= ZOOM_MAX" @click="zoom_by(ZOOM_STEP)">+</button>
      <button type="button" class="flat-zoom-button" aria-label="Zoom out" title="Zoom out" :disabled="zoom.k <= 1" @click="zoom_by(1 / ZOOM_STEP)">−</button>
    </div>
    <!-- Page elements laid over the map, such as a marker's list. -->
    <slot name="over" />
  </div>
</template>

<script>
// A flat, equal-area world map (see equalEarth.js) that zooms and pans, with finer coastlines and country
// names as it zooms in. It has country outlines only; the street and satellite pictures exist only as
// Mercator tiles, and are on the globe views. Pages put their own markers on it through the default slot.
import { markRaw } from 'vue'
import * as d3 from 'd3'
import { mesh } from 'topojson-client'
import countries110m from 'world-atlas/countries-110m.json'
import { MAP_WIDTH as W, MAP_HEIGHT as H, PROJECTION, mapPoint } from '@/components/equalEarth'
import { DETAIL_LEVELS, COUNTRY_LABEL_ZOOM, landOf, worldLabels, countryLabelsOf, visibleCountryLabels } from '@/components/statistics/worldGeometry'

const VIEW = [[0, 0], [W, H]]
const PATH = d3.geoPath(PROJECTION)
const SPHERE_PATH = PATH({ type: 'Sphere' })
const GRATICULE_PATH = PATH(d3.geoGraticule10())

const ZOOM_MAX = 40
const ZOOM_MS = 300
// One press of + doubles the scale, and one press of − halves it, as on the globe.
const ZOOM_STEP = 2
const LABEL_SIZE = 10
const LABEL_CHAR_WIDTH = 0.6
// How far one unit of wheel movement zooms, by the unit the browser reports: pixels, lines or pages.
const WHEEL_ZOOM_PER_PIXEL = 0.002
const WHEEL_ZOOM_PER_LINE = 0.05
const WHEEL_ZOOM_PER_PAGE = 1
// A trackpad pinch arrives as Ctrl + scroll in steps of a few pixels, far smaller than a wheel notch,
// so those small steps are boosted to keep pinching responsive.
const PINCH_MAX_PIXELS = 20
const PINCH_BOOST = 10

function wheelZoom (event) {
  const perUnit = event.deltaMode === 1 ? WHEEL_ZOOM_PER_LINE : event.deltaMode ? WHEEL_ZOOM_PER_PAGE : WHEEL_ZOOM_PER_PIXEL
  const isPinch = event.deltaMode === 0 && Math.abs(event.deltaY) < PINCH_MAX_PIXELS
  return -event.deltaY * perUnit * (isPinch ? PINCH_BOOST : 1)
}

export default {
  name: 'EqualEarthMap',
  props: {
    label: { type: String, default: 'World map' }
  },
  // 'view-change' carries { k, x, y, unit }: the zoom and pan, and the map units to one pixel at no zoom.
  emits: ['map-click', 'view-change'],
  data () {
    return {
      W, H, LABEL_SIZE, ZOOM_MAX, ZOOM_STEP,
      zoom: { k: 1, x: 0, y: 0 },
      // Map units to one pixel of screen before any zoom: 1 when the map is shown at its own width.
      unit: 1,
      topology: markRaw(countries110m)
    }
  },
  computed: {
    sphere_path () { return SPHERE_PATH },
    graticule_path () { return GRATICULE_PATH },
    map_transform () { return `translate(${this.zoom.x} ${this.zoom.y}) scale(${this.zoom.k})` },
    scale () { return this.unit / this.zoom.k },
    view () { return { ...this.zoom, unit: this.unit } },
    land_path () { return PATH(landOf(this.topology)) },
    border_path () { return PATH(mesh(this.topology, this.topology.objects.countries, (a, b) => a !== b)) },
    coast_path () { return PATH(mesh(this.topology, this.topology.objects.land)) },
    country_labels () { return countryLabelsOf(this.topology, PROJECTION) },
    // Continents and oceans are named while the whole world is in view, countries once it is zoomed in.
    world_labels () { return this.zoom.k < COUNTRY_LABEL_ZOOM ? worldLabels(PROJECTION) : [] },
    visible_labels () {
      if (this.zoom.k < COUNTRY_LABEL_ZOOM) return []
      return visibleCountryLabels(this.country_labels, this.zoom, W, H, LABEL_SIZE * this.unit, LABEL_CHAR_WIDTH)
    }
  },
  watch: {
    'zoom.k' () { this.ensure_detail() },
    view (view) { this.$emit('view-change', view) }
  },
  created () {
    this.detail_cache = {}
    this.detail_loading = new Set()
  },
  mounted () {
    this.zoom_behaviour = d3.zoom()
      .scaleExtent([1, ZOOM_MAX])
      .translateExtent(VIEW)
      .extent(VIEW)
      // Scrolling zooms the map only while Ctrl (or ⌘) is held, so a plain scroll keeps moving the page.
      // One-finger swipes keep scrolling the page until the map is zoomed in, so touch users are never stuck on it.
      .filter(event => {
        if (event.type === 'wheel') return event.ctrlKey || event.metaKey
        if (event.type.startsWith('touch')) return event.touches.length > 1 || this.zoom.k > 1
        return !event.button
      })
      .wheelDelta(wheelZoom)
      .on('zoom', event => { this.zoom = { k: event.transform.k, x: event.transform.x, y: event.transform.y } })
    d3.select(this.$refs.svg).call(this.zoom_behaviour)
    this.measure()
    if (typeof ResizeObserver !== 'undefined') {
      this.resize_observer = new ResizeObserver(() => this.measure())
      this.resize_observer.observe(this.$refs.box)
    }
  },
  beforeUnmount () {
    if (this.resize_observer) this.resize_observer.disconnect()
    if (this.$refs.svg) d3.select(this.$refs.svg).on('.zoom', null)
  },
  methods: {
    measure () {
      const width = this.$refs.box ? this.$refs.box.clientWidth : 0
      if (width > 0) this.unit = W / width
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
    zoom_to (transform, animate = true) {
      if (!this.zoom_behaviour) return
      const svg = d3.select(this.$refs.svg)
      const target = animate ? svg.transition().duration(ZOOM_MS) : svg
      target.call(this.zoom_behaviour.transform, transform)
    },
    // Zooms about the middle of the view, stopping at the whole world and at the closest zoom.
    zoom_by (factor) {
      if (!this.zoom_behaviour) return
      d3.select(this.$refs.svg).transition().duration(ZOOM_MS).call(this.zoom_behaviour.scaleBy, factor)
    },
    // A point of the map (in map units) in the middle of the view, as near as the edge of the world allows.
    centre_on (x, y, k, animate) {
      if (!this.zoom_behaviour) return
      const scale = Math.min(ZOOM_MAX, Math.max(1, k))
      const centred = d3.zoomIdentity.translate(W / 2, H / 2).scale(scale).translate(-x, -y)
      this.zoom_to(this.zoom_behaviour.constrain()(centred, VIEW, VIEW), animate)
    },
    zoom_to_place (lon, lat, k, animate = true) {
      const [x, y] = mapPoint(lon, lat)
      this.centre_on(x, y, k, animate)
    },
    // The closest view, up to `maxScale`, that holds every one of `places` ([[lon, lat], ...]) with
    // `padding` pixels to spare on each side.
    fit_places (places, { maxScale = ZOOM_MAX, padding = 0, animate = true } = {}) {
      if (!places.length) return
      const points = places.map(([lon, lat]) => mapPoint(lon, lat))
      const [x0, x1] = d3.extent(points, point => point[0])
      const [y0, y1] = d3.extent(points, point => point[1])
      const room = 2 * padding * this.unit
      // A single point has no width to fit, so it takes the closest zoom allowed.
      const wide = x1 > x0 ? Math.max(W - room, 1) / (x1 - x0) : maxScale
      const tall = y1 > y0 ? Math.max(H - room, 1) / (y1 - y0) : maxScale
      this.centre_on((x0 + x1) / 2, (y0 + y1) / 2, Math.min(maxScale, wide, tall), animate)
    },
    zoom_world (animate = true) {
      this.zoom_to(d3.zoomIdentity, animate)
    }
  }
}
</script>

<style scoped>
.flat-map { position: relative; background: var(--color-white); }
.flat-map svg { display: block; width: 100%; height: auto; cursor: grab; }
.flat-map svg:active { cursor: grabbing; }
/* The sea and land take the colours of the globe view's street map. */
.flat-sea { fill: #6fb1e4; }
.flat-graticule { vector-effect: non-scaling-stroke; fill: none; stroke: var(--color-white); stroke-width: 0.6; opacity: 0.35; pointer-events: none; }
.flat-land { fill: #f8f4f0; }
.flat-border { vector-effect: non-scaling-stroke; fill: none; stroke: hsl(30, 8%, 62%); stroke-width: 0.7; pointer-events: none; }
.flat-coast { vector-effect: non-scaling-stroke; fill: none; stroke: hsl(208, 35%, 34%); stroke-width: 0.9; pointer-events: none; }
.flat-outline { vector-effect: non-scaling-stroke; fill: none; stroke: hsl(208, 35%, 34%); stroke-width: 1; pointer-events: none; }
.flat-country { text-anchor: middle; dominant-baseline: middle; fill: #1b2a3a; paint-order: stroke; stroke: #f8f4f0; stroke-linejoin: round; pointer-events: none; user-select: none; }
.flat-world-label { text-anchor: middle; dominant-baseline: middle; pointer-events: none; user-select: none; }
.flat-world-label.is-continent { fill: #1b2a3a; font-weight: 600; opacity: 0.75; }
.flat-world-label.is-ocean { fill: hsl(210, 60%, 22%); font-style: italic; opacity: 0.8; }
/* In the top right corner, which the world's outline leaves empty, where the globe has its own pair. */
.flat-zoom { position: absolute; top: 10px; right: 10px; display: flex; flex-direction: column; border-radius: 4px; box-shadow: 0 0 0 2px var(--black-10); }
.flat-zoom-button { width: 29px; height: 29px; padding: 0; font: inherit; font-size: 1.2rem; line-height: 1; color: #333; background: var(--color-white); border: 0; cursor: pointer; }
.flat-zoom-button:first-child { border-radius: 4px 4px 0 0; }
.flat-zoom-button:last-child { border-top: 1px solid #ddd; border-radius: 0 0 4px 4px; }
.flat-zoom-button:hover:not(:disabled) { background: #f2f2f2; }
.flat-zoom-button:disabled { color: #bbb; cursor: default; }
.flat-zoom-button:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 1px; }
@media (max-width: 600px) {
  .flat-zoom-button { width: 2.75rem; height: 2.75rem; }
}
</style>
