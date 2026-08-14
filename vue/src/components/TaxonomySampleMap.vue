<template>
  <div>
    <div v-if="loading" class="has-text-grey">Loading sample distribution…</div>

    <div v-else-if="error" class="has-text-danger">
      Could not load sample distribution: {{ error }}
    </div>

    <div v-else-if="cells.length === 0" class="has-text-grey">
      No samples with coordinates for this taxon.
    </div>

    <div v-else class="sample-map">
      <div v-show="tip.visible" class="map-tip"
           :style="{ left: tip.x + 'px', top: tip.y + 'px' }">
        <div class="map-tip-head">
          <b>{{ tip.total.toLocaleString("en-US") }}</b> samples
          <span class="map-tip-coords">{{ tip.lat }}, {{ tip.lon }}</span>
        </div>
        <div v-for="row in tip.categories" :key="row.key" class="map-tip-row">
          <span class="map-tip-dot" :style="{ backgroundColor: COLOURS[row.key] }"></span>
          <span class="map-tip-label">{{ LABELS[row.key] || row.key }}</span>
          <span class="map-tip-count">{{ row.n.toLocaleString("en-US") }}</span>
        </div>
        <div v-if="tip.studies.length" class="map-tip-studies">
          <div v-for="study in tip.studies" :key="study.title" class="map-tip-study">
            {{ study.title }}
            <span class="map-tip-count">{{ study.count.toLocaleString("en-US") }}</span>
          </div>
        </div>
        <div class="map-tip-hint">Click to filter the runs below</div>
      </div>

      <p>
        {{ total.toLocaleString("en-US") }} samples with coordinates, at
        {{ cells.length.toLocaleString("en-US") }} locations. Circle area is
        proportional to the number of samples.
      </p>

      <!-- World -->
      <svg :viewBox="`0 0 ${W} ${worldH}`" preserveAspectRatio="xMidYMid meet"
           class="panel world"></svg>

      <div class="legend">
        <span v-for="key in legendKeys" :key="key" class="legend-item">
          <span class="legend-dot" :style="{ backgroundColor: COLOURS[key] }"></span>
          {{ LABELS[key] }}
        </span>
      </div>

      <!-- Poles -->
      <div class="poles">
        <svg :viewBox="`0 0 ${poleSize} ${poleSize}`" preserveAspectRatio="xMidYMid meet"
             class="panel north"></svg>
        <svg :viewBox="`0 0 ${poleSize} ${poleSize}`" preserveAspectRatio="xMidYMid meet"
             class="panel south"></svg>
      </div>

    </div>
  </div>
</template>

<script>
import * as d3 from 'd3'
import { feature, mesh } from 'topojson-client'
import countries110m from 'world-atlas/countries-110m.json'
import { fetchTaxonomyMap } from '@/api'

// Ordered so the legend never reshuffles between taxa.
const COLOURS = {
  human: '#f2a03d',
  animal: '#ef6c2a',
  ocean: '#5b8fd4',
  other: '#e0417c',
  host_associated: '#9a6fb5',
  ecological: '#84a86f',
  unclassified: '#b0b0b0'
}
const LABELS = {
  human: 'Human samples',
  animal: 'Animal samples',
  ocean: 'Ocean water samples',
  other: 'Other environmental samples',
  host_associated: 'Host-associated samples',
  ecological: 'Ecological samples',
  unclassified: 'Unclassified'
}

// Muted physical-map palette: pale blue sea, warm tan land, soft borders.
const OCEAN = '#bcd9ea'
const LAND = '#e9e2ce'
const LAND_EDGE = '#a89f88'
const BORDER = '#c8bfa6'
const GRATICULE = '#ffffff'
const SPHERE_EDGE = '#8fa3ae'

// Radius in pixels of the largest circle. One value for every panel: all three
// render at 1 SVG unit = 1px, so this means the same physical size in each.
const DOT_SCALE = 14

export default {
  name: 'TaxonomySampleMap',
  props: ['taxon', 'taxonomyType'],
  data () {
    return {
      cells: [],
      total: 0,
      precision: 1,
      tip: { visible: false, x: 0, y: 0, lat: 0, lon: 0, total: 0, categories: [], studies: [] },
      loading: true,
      error: null,
      // All panels use 1 SVG unit = 1 rendered pixel (see the CSS widths), so
      // a circle radius means the same physical size in every panel. Mixing
      // ratios is what made the polar dots look wrong next to the world map.
      W: 960,
      worldH: 500,
      poleSize: 400,
      COLOURS,
      LABELS
    }
  },
  computed: {
    land () {
      return feature(countries110m, countries110m.objects.land)
    },
    countries () {
      // Internal borders only -- mesh with a !== b drops the coastline, which
      // is already drawn by the land layer.
      return mesh(countries110m, countries110m.objects.countries, (a, b) => a !== b)
    },
    categoryTotals () {
      const totals = {}
      for (const cell of this.cells) {
        for (const [key, n] of Object.entries(cell.categories)) {
          totals[key] = (totals[key] || 0) + n
        }
      }
      return totals
    },
    legendKeys () {
      return Object.keys(LABELS).filter(k => this.categoryTotals[k] > 0)
    },
    maxTotal () {
      return this.cells.reduce((m, c) => Math.max(m, c.total), 1)
    }
  },
  watch: {
    taxon: 'load',
    taxonomyType: 'load',
    // Safety net for the draw timing: the <svg> elements only exist once the
    // v-else branch has rendered, so redraw whenever the data lands.
    cells () {
      this.$nextTick(this.draw)
    }
  },
  mounted () {
    this.load()
  },
  methods: {
    async load () {
      if (!this.taxon) return
      this.loading = true
      this.error = null
      try {
        const { data } = await fetchTaxonomyMap(this.taxon, this.taxonomyType)
        this.cells = data.cells || []
        this.total = data.total || 0
        this.precision = data.precision ?? 1
      } catch (e) {
        // Surface it: an empty map and a failed request look identical
        // otherwise, which is exactly how this went unnoticed the first time.
        this.error = e.response ? `${e.response.status} ${e.response.statusText}` : e.message
        this.cells = []
        this.total = 0
      } finally {
        this.loading = false
        // Wait for v-else to render the <svg> elements before drawing.
        this.$nextTick(this.draw)
      }
    },

    dominant (cell) {
      let best = 'unclassified'
      let bestN = -1
      for (const [key, n] of Object.entries(cell.categories)) {
        if (n > bestN) { best = key; bestN = n }
      }
      return best
    },

    // Area-proportional: ten times the samples reads as ten times the blob,
    // not a hundred times.
    radius (count, scale) {
      return Math.max(1.4, Math.sqrt(count / this.maxTotal) * scale)
    },

    draw () {
      // Report rather than fail silently: a thrown error here leaves three
      // empty boxes that look exactly like "no data".
      try {
        this.drawAll()
      } catch (e) {
        this.error = `render failed: ${e && e.message ? e.message : e}`
        console.error('TaxonomySampleMap draw failed', e)
      }
    },

    drawAll () {
      if (!this.cells.length) return
      this.drawPanel('.world',
        d3.geoNaturalEarth1().fitExtent(
          [[8, 8], [this.W - 8, this.worldH - 8]], { type: 'Sphere' }),
        DOT_SCALE, true)
      this.drawPanel('.north',
        d3.geoAzimuthalEqualArea().rotate([0, -90]).clipAngle(60)
          .fitExtent([[6, 6], [this.poleSize - 6, this.poleSize - 6]],
            { type: 'Sphere' }),
        DOT_SCALE, true, lat => lat >= 30)
      this.drawPanel('.south',
        d3.geoAzimuthalEqualArea().rotate([0, 90]).clipAngle(60)
          .fitExtent([[6, 6], [this.poleSize - 6, this.poleSize - 6]],
            { type: 'Sphere' }),
        DOT_SCALE, true, lat => lat <= -30)
    },

    drawPanel (selector, projection, dotScale, showGraticule, latFilter) {
      const svg = d3.select(this.$el).select(selector)
      if (svg.empty()) return
      svg.selectAll('*').remove()

      const path = d3.geoPath(projection)

      // Sea
      svg.append('path')
        .attr('d', path({ type: 'Sphere' }))
        .attr('fill', OCEAN)
        .attr('stroke', SPHERE_EDGE)
        .attr('stroke-width', 0.9)

      if (showGraticule) {
        svg.append('path')
          .attr('d', path(d3.geoGraticule10()))
          .attr('fill', 'none')
          .attr('stroke', GRATICULE)
          .attr('stroke-width', 0.5)
          .attr('opacity', 0.55)
      }

      // Land, then internal borders on top of it
      svg.append('path')
        .attr('d', path(this.land))
        .attr('fill', LAND)
        .attr('stroke', LAND_EDGE)
        .attr('stroke-width', 0.5)

      svg.append('path')
        .attr('d', path(this.countries))
        .attr('fill', 'none')
        .attr('stroke', BORDER)
        .attr('stroke-width', 0.4)
        .attr('opacity', 0.85)

      // Largest first so small points stay clickable on top of big ones.
      const visible = this.cells
        .filter(c => !latFilter || latFilter(c.lat))
        .slice()
        .sort((a, b) => b.total - a.total)

      svg.append('g')
        .selectAll('circle')
        .data(visible)
        .join('circle')
        .attr('transform', d => {
          const p = projection([d.lon, d.lat])
          return p ? `translate(${p[0]},${p[1]})` : null
        })
        .attr('display', d => projection([d.lon, d.lat]) ? null : 'none')
        .attr('r', d => this.radius(d.total, dotScale))
        .attr('fill', d => COLOURS[this.dominant(d)])
        .attr('fill-opacity', 0.75)
        .attr('stroke', d => COLOURS[this.dominant(d)])
        .attr('stroke-width', 0.4)
        .attr('cursor', 'pointer')
        .on('click', (event, d) => this.$emit('cluster-selected', {
          lat: d.lat, lon: d.lon, precision: this.precision, total: d.total
        }))
        .on('mouseenter', (event, d) => this.showTip(event, d))
        .on('mousemove', event => this.moveTip(event))
        .on('mouseleave', () => { this.tip.visible = false })
    },

    showTip (event, cell) {
      this.tip.lat = cell.lat
      this.tip.lon = cell.lon
      this.tip.total = cell.total
      this.tip.categories = Object.entries(cell.categories)
        .sort((a, b) => b[1] - a[1])
        .map(([key, n]) => ({ key, n }))
      this.tip.studies = (cell.studies || []).slice(0, 4)
      this.tip.visible = true
      this.moveTip(event)
    },
    moveTip (event) {
      // Position against the component, not the page, so the tip follows the
      // cursor correctly once the page is scrolled.
      const box = this.$el.getBoundingClientRect()
      const x = event.clientX - box.left
      const y = event.clientY - box.top
      // Flip to the left of the cursor near the right edge so it stays visible.
      this.tip.x = x + 260 > box.width ? x - 250 : x + 14
      this.tip.y = Math.max(0, y - 10)
    }
  }
}
</script>

<style scoped>
.sample-map {
  /* Anchor for the absolutely positioned tooltip. */
  position: relative;
}
.map-tip {
  position: absolute;
  z-index: 20;
  pointer-events: none;
  min-width: 210px;
  max-width: 320px;
  padding: 0.6rem 0.7rem;
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid #dcd7c9;
  border-radius: 6px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.16);
  font-size: 0.8rem;
  line-height: 1.35;
}
.map-tip-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.75rem;
  padding-bottom: 0.35rem;
  margin-bottom: 0.35rem;
  border-bottom: 1px solid #eee7d8;
}
.map-tip-coords {
  color: #8a8a8a;
  font-size: 0.72rem;
  white-space: nowrap;
}
.map-tip-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.map-tip-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex: 0 0 auto;
}
.map-tip-label {
  flex: 1 1 auto;
}
.map-tip-count {
  color: #666;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.map-tip-studies {
  margin-top: 0.4rem;
  padding-top: 0.35rem;
  border-top: 1px solid #eee7d8;
  color: #555;
}
.map-tip-study {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  /* Study titles run long; keep the tooltip a sane width. */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.map-tip-hint {
  margin-top: 0.45rem;
  color: #3273dc;
  font-size: 0.72rem;
}
.panel {
  width: 100%;
  height: auto;
  display: block;
  overflow: visible;
}
.world { aspect-ratio: 960 / 500; }
.poles .panel { aspect-ratio: 1 / 1; }
.world {
  max-width: 960px;
  margin: 0 auto;
}
.poles {
  /* Grid, not flex: flex items size to content, which let the two polar
     panels come out different widths. Fixed equal columns keeps them
     identical, which matters because dot radii are shared between panels. */
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(0, 400px));
  justify-content: center;
  gap: 2rem;
  margin-top: 0.5rem;
}
.poles .panel {
  /* Must equal poleSize so 1 SVG unit renders as 1px, matching the world
     panel -- otherwise identical radii come out different sizes. */
  width: 100%;
  max-width: 400px;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 1.25rem;
  margin: 0.5rem 0;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
</style>
