<template>
  <div class="indicpiper-chart">
    <p class="section-note">Habitat totals, genus values, and bar lengths show indicator abundance as a percentage of the sample.</p>
    <div v-for="row in habitats" :key="row.k" class="habitat-row">
      <div class="habitat-row-header">
        <button
          type="button"
          class="habitat-toggle"
          :aria-expanded="!!expanded[row.k]"
          :aria-controls="detailId(row.k)"
          :aria-label="`Show genus breakdown for ${row.k}`"
          @click="toggle(row.k)"
        >
          <b-icon icon="information-outline" size="is-small" />
          <span class="habitat-name">{{ row.k }}</span>
        </button>
        <span class="habitat-score">{{ formatPercent(row.score) }}</span>
      </div>

      <div class="habitat-bar" role="img" :aria-label="barAriaLabel(row)">
        <router-link
          v-for="seg in segments(row)"
          :key="seg.genus"
          :to="taxonomyLink(seg.genus)"
          class="habitat-bar-segment"
          tabindex="-1"
          :style="{ width: seg.widthPct + '%', backgroundColor: colorScale(seg.genus) }"
          :title="seg.indValLabel !== null
            ? `${seg.genus}: ${seg.percentLabel} of the sample / IndVal ${seg.indValLabel} -- click to view this genus on the taxonomy page`
            : `${seg.genus}: ${seg.percentLabel} of the sample -- click to view this genus on the taxonomy page`"
        ></router-link>
      </div>

      <div v-if="expanded[row.k]" :id="detailId(row.k)" class="habitat-detail">
        <ul class="detail-grid">
          <li v-for="seg in segments(row)" :key="seg.genus">
            <span class="detail-swatch" :style="{ backgroundColor: colorScale(seg.genus) }"></span>
            <router-link :to="taxonomyLink(seg.genus)" class="detail-genus">{{ seg.genus }}</router-link>
            <span class="detail-fraction">{{ seg.percentLabel }}</span>
            <span v-if="seg.indValLabel !== null" class="detail-indval" :title="`IndicPiper indicator value for this genus's affinity to ${row.k} (0-1, higher is stronger)`">
              / IndVal {{ seg.indValLabel }}
            </span>
          </li>
        </ul>
        <p class="detail-legend">Genus percentages are relative to the whole sample and sum to the habitat total, subject to rounding (2 D.P). IndVal is the reference association statistic (0–1), not a confidence estimate.</p>
      </div>
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3'
import { formatIndicPiperPercent } from '@/utils/indicpiper'

export default {
  name: 'IndicPiperHabitatChart',
  props: {
    habitats: {
      // Each entry: { k: habitat, v: display score, score: raw score,
      // genera: [{ genus, relative_abundance }], ... } -- see api.py's
      // indicpiper_rows().
      type: Array,
      required: true,
    },
  },
  data() {
    return {
      expanded: {},
    }
  },
  computed: {
    // One color per genus, stable across every bar/tooltip on this chart.
    // Evenly divides the full hue circle by the actual genus count, which
    // guarantees a hard minimum hue gap between every pair (360/perRing
    // degrees) -- unlike the previous golden-angle-plus-modular-cycling
    // approach, which had no such guarantee: two genera could coincidentally
    // land at a near-identical hue+saturation+lightness combination once
    // enough genera were in play. Genera beyond 10 split into two
    // interleaved "rings" at different lightness (offset by half a hue
    // step from each other), so each ring keeps a wide hue budget instead
    // of cramming every genus into one ever-finer 360° sweep, while the
    // lightness difference keeps the two rings tell-apart-able even where
    // their hues land close together.
    colorScale() {
      const genusNames = Array.from(new Set(
        this.habitats.flatMap(h => (h.genera || []).map(g => g.genus))
      )).sort()
      const n = genusNames.length
      const baseHue = 174
      const ringCount = n > 10 ? 2 : 1
      const perRing = Math.ceil(n / ringCount)
      const hueStep = 360 / perRing
      const ringLightness = [38, 60]
      const colors = genusNames.map((_, i) => {
        const ring = i % ringCount
        const posInRing = Math.floor(i / ringCount)
        const hue = (baseHue + posInRing * hueStep + ring * (hueStep / 2)) % 360
        return `hsl(${hue}, 58%, ${ringLightness[ring]}%)`
      })
      return d3.scaleOrdinal().domain(genusNames).range(colors)
    },
  },
  methods: {
    toggle(key) {
      this.expanded[key] = !this.expanded[key]
    },
    detailId(key) {
      return `indicpiper-detail-${key.replace(/[^a-z0-9]+/gi, '-')}`
    },
    // Matches the '/taxonomy/:taxonomy' route's expected rank-prefixed name
    // (same 'g__' genus prefix Sunburst3.vue uses when linking a taxon node
    // to its SearchResults page).
    taxonomyLink(genus) {
      return '/taxonomy/g__' + genus
    },
    // Segment width as a percentage of a fixed 0-1 scale (score is a sum of
    // relative_abundance values, which can range from 0 to 1), not relative
    // to this run's own strongest habitat -- a full pill always means a
    // score of 1.0, so bar length is comparable across habitats and across
    // runs, not just within one run.
    segments(row) {
      const genera = row.genera || []
      return genera.map(g => ({
        genus: g.genus,
        widthPct: g.relative_abundance * 100,
        // Use the same sample-wide abundance for labels and segment widths.
        percentLabel: this.formatPercent(g.relative_abundance),
        indValLabel: this.formatIndVal(g.ind_val_mean),
      }))
    },
    formatPercent: formatIndicPiperPercent,
    formatIndVal(value) {
      return typeof value === 'number' && Number.isFinite(value) ? d3.format('.2f')(value) : null
    },
    barAriaLabel(row) {
      const genera = row.genera || []
      if (genera.length === 0) {
        return `${row.k}: indicator abundance ${this.formatPercent(row.score)}`
      }
      const breakdown = genera
        .map(g => {
          const percent = this.formatPercent(g.relative_abundance)
          const indVal = this.formatIndVal(g.ind_val_mean)
          return indVal !== null
            ? `${g.genus} ${percent} of the sample, IndVal ${indVal}`
            : `${g.genus} ${percent} of the sample`
        })
        .join(', ')
      return `${row.k}: indicator abundance ${this.formatPercent(row.score)}, genus breakdown: ${breakdown}`
    },
  },
}
</script>

<style scoped>
.indicpiper-chart {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}

.habitat-row-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.3rem;
}

.habitat-toggle {
  appearance: none;
  border: 0;
  padding: 0.15rem 0.2rem;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.habitat-toggle:focus-visible {
  outline: 2px solid #3273dc;
  outline-offset: 2px;
}

.habitat-name {
  font-weight: 600;
  text-transform: capitalize;
}

.habitat-score {
  font-variant-numeric: tabular-nums;
  color: hsl(0, 0%, 40%);
  white-space: nowrap;
}

.habitat-bar {
  display: flex;
  width: 100%;
  height: 1.1rem;
  background: hsl(0, 0%, 93%);
  border-radius: 3px;
  overflow: hidden;
}

.habitat-bar-segment {
  display: block;
  height: 100%;
  min-width: 1px;
  cursor: pointer;
}

.habitat-bar-segment:hover,
.habitat-bar-segment:focus-visible {
  filter: brightness(1.15);
  outline: 1px solid hsl(0, 0%, 100%);
  outline-offset: -1px;
}

.habitat-detail {
  margin-top: 0.4rem;
  padding: 0.5rem 0.6rem;
  background: hsl(0, 0%, 97%);
  border-radius: 3px;
  font-size: 0.85rem;
}

.detail-grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.4rem 1rem;
}

.detail-grid li {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  min-width: 0;
  font-size: 0.78rem;
  white-space: nowrap;
}

.detail-legend {
  margin: 0.6rem 0 0;
  padding-top: 0.4rem;
  border-top: 1px solid hsl(0, 0%, 88%);
  color: hsl(0, 0%, 55%);
  font-size: 0.75rem;
}

.detail-swatch {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 2px;
  flex-shrink: 0;
}

.detail-genus {
  font-style: italic;
  color: hsl(174, 62%, 28%);
  text-decoration: underline;
  text-decoration-color: transparent;
  transition: text-decoration-color 0.15s;
}

.detail-genus:hover,
.detail-genus:focus-visible {
  text-decoration-color: currentColor;
}

.detail-fraction {
  font-variant-numeric: tabular-nums;
  color: hsl(0, 0%, 40%);
}

.detail-indval {
  font-variant-numeric: tabular-nums;
  color: hsl(0, 0%, 40%);
  font-size: 0.8em;
}

@media (max-width: 600px) {
  .habitat-row-header {
    flex-wrap: wrap;
  }
  /* One clearly bounded block per habitat. */
  .indicpiper-chart {
    gap: 0;
  }
  .habitat-row {
    padding: 0.85rem 0;
    border-bottom: 1px solid hsl(0, 0%, 90%);
  }
  .habitat-row:first-of-type {
    padding-top: 0.25rem;
  }
  .habitat-row:last-child {
    border-bottom: 0;
  }
  /* A 260px minimum column plus nowrap overflowed a 320px screen. */
  .detail-grid {
    grid-template-columns: 1fr;
  }
  .detail-grid li {
    flex-wrap: wrap;
    white-space: normal;
  }
}
</style>
