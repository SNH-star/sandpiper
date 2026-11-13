<template>
  <div class="depth-figure">
    <div class="depth-chart">
      <p class="depth-y-title"><span class="depth-y-long">Bases sequenced (square-root scale)</span><span class="depth-y-short">Bases (sqrt scale)</span></p>
      <div class="depth-plot" role="img" :aria-label="aria">
        <div v-for="tick in Y_TICKS" :key="tick.bases" class="depth-gridline" :class="{ 'is-minor': !tick.major }" :style="{ bottom: heightOf(tick.bases) + '%' }">
          <span v-if="tick.major" class="depth-tick-label">{{ tick.label }}</span>
        </div>
        <div v-for="row in rows" :key="row.year" class="depth-col" :class="{ 'is-partial': row.is_partial, 'is-selected': selected && selected.year === row.year }" :title="row.title"
             @pointerenter="pick($event, row)" @pointerleave="clear($event)" @click="selected = row">
          <span class="depth-whisker" :style="{ bottom: row.low + '%', height: row.whisker + '%' }"></span>
          <span class="depth-box" :style="{ bottom: row.q1 + '%', height: row.box + '%' }"></span>
          <span class="depth-median" :style="{ bottom: row.median + '%' }"></span>
        </div>
      </div>
      <div class="depth-axis" aria-hidden="true">
        <span v-for="row in rows" :key="row.year" class="depth-x-label">{{ row.year }}</span>
      </div>
      <div class="depth-medians" aria-hidden="true">
        <span class="depth-medians-title">Median</span>
        <span v-for="row in rows" :key="row.year" class="depth-median-value">{{ row.median_label }}</span>
      </div>
      <p class="depth-x-title">Year released</p>
    </div>
    <p class="stat-note depth-readout" :class="{ 'export-skip': !selected }" aria-live="polite">{{ selected ? selected.title : 'Hover or select a year for its figures.' }}</p>
    <p class="stat-note depth-key">
      <span><span class="depth-swatch" aria-hidden="true"></span>Middle half of runs (25th to 75th percentile), with the median marked</span>
      <span><span class="depth-swatch depth-swatch-line" aria-hidden="true"></span>Whiskers reach the 5th and 95th percentiles</span>
      <span v-if="partialRow">{{ partialRow.year }} is partial: runs released before {{ partialDate }}</span>
    </p>
    <p class="stat-note depth-scale-note">
      The scale is square-root: the gaps between lines shrink going up, so equal heights are not equal amounts.
      Square root keeps zero on the axis and spreads shallow runs out more than a linear axis would.
    </p>
    <table class="is-sr-only">
      <caption>Sequencing depth by release year</caption>
      <tbody>
        <tr v-for="row in rows" :key="row.year">
          <th scope="row">{{ row.year }}</th>
          <td>{{ row.title }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import SUMMARIES from '@/constants/groupSummaries.json'
import { basesLabel } from '@/components/statistics/density'

// The depth axis runs from 0 to this many bases (the highest 95th percentile, 2012's, is 57 Gb).
const CEILING_BASES = 60e9
// Lines on the axis, in bases: main ones labelled in full, fainter dotted ones between them.
// They bunch towards the bottom, which shows the scale is square-root.
const GIGA = 1e9
const Y_TICKS = [
  { bases: 0, major: true }, { bases: 1 * GIGA, major: true }, { bases: 2.5 * GIGA, major: false },
  { bases: 5 * GIGA, major: true }, { bases: 10 * GIGA, major: true }, { bases: 15 * GIGA, major: false },
  { bases: 20 * GIGA, major: true }, { bases: 40 * GIGA, major: true }, { bases: CEILING_BASES, major: true }
].map(tick => ({ ...tick, label: tick.bases === 0 ? '0' : basesLabel(tick.bases) }))
// Height on the plot, as a percentage, of a number of bases on the square-root scale.
const heightOf = bases => (100 * Math.sqrt(Math.min(Math.max(bases, 0), CEILING_BASES))) / Math.sqrt(CEILING_BASES)
const toBases = value => basesLabel(10 ** value)

export default {
  name: 'YearDepthBoxplot',
  props: { partialDate: { type: String, default: '' } },
  data () {
    return { Y_TICKS, selected: null }
  },
  computed: {
    years () {
      return SUMMARIES.yearly_depth || []
    },
    rows () {
      return this.years.map(row => ({
        year: row.year,
        is_partial: row.year === this.partialYear,
        low: this.place(row.p5),
        whisker: this.place(row.p95) - this.place(row.p5),
        q1: this.place(row.q1),
        box: this.place(row.q3) - this.place(row.q1),
        median: this.place(row.median),
        median_label: toBases(row.median),
        title: `${row.year}: median ${toBases(row.median)}, middle half ${toBases(row.q1)} to ${toBases(row.q3)}, `
          + `5th to 95th percentile ${toBases(row.p5)} to ${toBases(row.p95)}, ${row.runs.toLocaleString('en-US')} runs`
      }))
    },
    // The year the data was collected in: runs released after it are not in yet.
    partialYear () {
      const match = /\d{4}/.exec(this.partialDate)
      return match ? Number(match[0]) : null
    },
    partialRow () {
      return this.rows.find(row => row.is_partial) || null
    },
    aria () {
      const first = this.years[0]
      const last = this.years[this.years.length - 1]
      return first ? `Boxplot of sequencing depth for each release year, ${first.year} to ${last.year}.` : 'No sequencing depth data.'
    }
  },
  methods: {
    // A mouse previews on hover; touch and pen select with a tap (see @click).
    pick (event, row) {
      if (event.pointerType === 'mouse') this.selected = row
    },
    clear (event) {
      if (event.pointerType === 'mouse') this.selected = null
    },
    // Height on the plot, as a percentage, of a depth the summary stores as log10 bases.
    place (value) {
      return heightOf(10 ** value)
    },
    heightOf
  }
}
</script>

<style scoped>
.stat-note { font-size: 0.9rem; line-height: 1.5; color: var(--color-ink-muted); }
.depth-chart { position: relative; margin: var(--space-6) 0 var(--space-2) 4.4rem; --plot-height: 16rem; }
@media (max-width: 640px) {
  .depth-chart { margin-left: 3.8rem; margin-right: var(--space-2); --plot-height: 12rem; }
  .depth-chart .depth-y-title { left: -3.8rem; font-size: 0.75rem; white-space: nowrap; }
  .depth-axis .depth-x-label:nth-child(even) { visibility: hidden; }
}
.depth-y-title { position: absolute; top: 0; left: -4.4rem; display: flex; align-items: center; justify-content: center; width: 1.4rem; height: var(--plot-height); font-size: 0.85rem; writing-mode: vertical-rl; transform: rotate(180deg); color: var(--color-ink-muted); }
.depth-plot { position: relative; display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); gap: var(--space-1); height: var(--plot-height); border-left: 1px solid var(--color-rule); border-bottom: 1px solid var(--color-rule); }
.depth-gridline { position: absolute; left: 0; right: 0; border-top: 1px solid var(--color-track); }
.depth-tick-label { position: absolute; right: calc(100% + var(--space-2)); top: 0; transform: translateY(-50%); font-size: 0.8rem; font-variant-numeric: tabular-nums; color: var(--color-ink-muted); white-space: nowrap; }
.depth-col { position: relative; min-width: 0; }
.depth-col:hover { background: var(--color-track); }
.depth-whisker { position: absolute; left: 50%; width: 0; border-left: 2px solid var(--color-accent); transform: translateX(-50%); }
.depth-box { position: absolute; left: 20%; right: 20%; background: var(--color-accent); opacity: 0.35; border: 2px solid var(--color-accent); border-radius: 2px; }
.depth-median { position: absolute; left: 20%; right: 20%; height: 0; border-top: 3px solid var(--color-ink); }
/* The partial year: dashed outline, as the box is not yet its final shape. */
.depth-col.is-partial .depth-box { border-style: dashed; }
.depth-axis { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); gap: var(--space-1); height: 1.4rem; }
.depth-x-label { padding-top: var(--space-1); font-size: 0.72rem; font-variant-numeric: tabular-nums; text-align: center; color: var(--color-ink-muted); white-space: nowrap; }
.depth-x-title { margin-top: var(--space-1); font-size: 0.85rem; text-align: center; color: var(--color-ink-muted); }
.depth-key { column-width: 22rem; column-gap: var(--space-6); max-width: none; }
.depth-key > span { display: block; break-inside: avoid; margin-bottom: var(--space-1); }
.depth-swatch { display: inline-block; width: 0.8rem; height: 0.8rem; margin-right: var(--space-2); border: 2px solid var(--color-accent); background: color-mix(in srgb, var(--color-accent) 35%, transparent); border-radius: 2px; }
.depth-swatch-line { width: 0; height: 0.8rem; border-width: 0 0 0 2px; background: none; border-radius: 0; margin-right: var(--space-3); }
@media (max-width: 768px) {
  .depth-x-label { font-size: 0.65rem; }
}
.depth-y-short { display: none; }
@media (max-width: 640px) {
  .depth-y-long { display: none; }
  .depth-y-short { display: inline; }
}
.depth-gridline.is-minor { border-top-style: dotted; opacity: 0.8; }
.depth-gridline.is-minor .depth-tick-label { font-size: 0.7rem; opacity: 0.85; }
.depth-col { cursor: pointer; touch-action: manipulation; }
.depth-col.is-selected { background: var(--color-track); }
.depth-medians { position: relative; display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); gap: var(--space-1); }
.depth-medians-title { position: absolute; top: 0; right: calc(100% + var(--space-2)); font-size: 0.75rem; color: var(--color-ink-muted); white-space: nowrap; }
.depth-median-value { font-size: 0.7rem; font-variant-numeric: tabular-nums; text-align: center; color: var(--color-ink); white-space: nowrap; overflow: visible; }
@media (max-width: 900px) {
  .depth-medians .depth-median-value:nth-child(odd) { visibility: hidden; }
}
@media (max-width: 640px) {
  .depth-medians .depth-median-value:not(:nth-child(2)):not(:last-child) { visibility: hidden; }
  /* A figure wider than its narrow column grows away from the plot's edge, not past it. */
  .depth-medians .depth-median-value:nth-child(2) { visibility: visible; justify-self: start; width: max-content; }
  .depth-medians .depth-median-value:last-child { visibility: visible; justify-self: end; width: max-content; }
  .depth-medians-title { right: auto; left: -3.8rem; }
}
.depth-readout { box-sizing: border-box; min-height: 3.5rem; margin: var(--space-2) 0 0; padding: var(--space-2) 0; max-width: none; }
.depth-scale-note { margin-top: var(--space-2); }
</style>
