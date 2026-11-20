<template>
  <section v-if="series.length" :id="spec.id" class="section container stat-figure">
    <chart-download :target="'#' + spec.id" :name="spec.id" :table="table" />
    <h3 class="subtitle is-3 stat-title"><a class="section-anchor" :href="'#' + spec.id">#</a> {{ spec.title }}</h3>
    <p class="stat-note is-wide">
      {{ spec.intro }} Counting only species that had a genome available the year before (by the
      NCBI date of the species’ earliest genome in GTDB). Dashed lines are linear trends weighted by the number of
      runs{{ spec.fitNote }}. Years with fewer than {{ MIN_YEAR_RUNS }} runs are left out, and the earliest years rest on few runs, so
      they vary more.
    </p>
    <b-switch v-model="extrapolate" :name="'extrapolate-' + spec.id" class="trend-switch">Extrapolate with simple linear model</b-switch>
    <template v-if="extrapolate">
      <p class="stat-note is-wide trend-extrapolation">
        Each dashed line continues in a straight line until it reaches 100%, then stops, as if the trend stayed linear, which it
        will not. The year each selected line is predicted to reach 100% is shown on the chart and in the legend; click a
        line, or its legend entry, to add or remove it.
      </p>
      <p class="stat-note is-wide trend-extrapolation">
        This linear model is only roughly indicative, as it implicitly makes many assumptions about the future.
      </p>
    </template>
    <div class="trend-chart">
      <p class="trend-y-title"><span class="trend-y-long">Mean known species fraction (%)</span><span class="trend-y-short">Known species (%)</span></p>
      <div class="trend-plot" role="img" :aria-label="aria" @pointermove="move" @pointerdown="move" @pointerleave="hovered = null">
        <div v-for="tick in Y_TICKS" :key="tick" class="trend-gridline" :style="{ bottom: tick + '%' }">
          <span class="trend-tick-label">{{ tick }}</span>
        </div>
        <!-- The current year, so an extended dashed line reads as past or still to come. -->
        <span class="trend-now" :style="{ left: place(CURRENT_YEAR) + '%' }" aria-hidden="true">
          <span class="trend-now-label">{{ CURRENT_YEAR }}</span>
        </span>
        <svg class="trend-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <template v-for="line in drawn" :key="line.key">
            <polyline :points="line.points" :style="{ stroke: shade(line) }" class="trend-stroke" :class="{ 'is-dim': dimmed(line) }" fill="none" vector-effect="non-scaling-stroke" />
            <line v-if="showFit(line)" :x1="line.fit[0]" :y1="line.fit[1]" :x2="line.fit[2]" :y2="line.fit[3]" :style="{ stroke: shade(line) }" class="trend-fit" :class="{ 'is-dim': dimmed(line) }" vector-effect="non-scaling-stroke" />
          </template>
          <!-- Wide invisible strokes on top: hovering a line picks it out, clicking it selects it like its legend entry. -->
          <polyline v-for="line in lines" :key="'hit-' + line.key" :points="line.points" class="trend-hit" fill="none"
                    vector-effect="non-scaling-stroke" @pointerenter="hoveredLine = line.key" @pointerleave="hoveredLine = null"
                    @click="selected = toggleKey(selected, line.key)" />
        </svg>
        <template v-for="line in drawn" :key="'dots-' + line.key">
          <span v-for="point in line.dots" :key="point.year" class="trend-dot" :class="{ 'is-dim': dimmed(line) }" :style="{ left: point.x + '%', bottom: point.y + '%', background: shade(line) }"></span>
        </template>
        <!-- Where a clicked line's extended dashed line reaches 100%, and in which year. -->
        <template v-for="line in drawn" :key="'predicted-' + line.key">
          <span v-if="extrapolate && selected.includes(line.key) && showFit(line) && line.full !== null" class="trend-predicted"
                :class="{ 'is-right-edge': place(line.full) > RIGHT_EDGE_PERCENT, 'is-dim': dimmed(line) }"
                :style="{ left: place(line.full) + '%', color: shade(line) }">year: {{ predictedYear(line) }}</span>
        </template>
        <template v-if="hovered !== null">
          <span class="trend-guide" :style="{ left: place(hovered) + '%' }"></span>
          <div class="trend-tip" :class="{ 'is-left': place(hovered) > 55 }" :style="{ left: place(hovered) + '%' }" aria-hidden="true">
            <p class="trend-tip-year">{{ hovered }}</p>
            <p v-for="line in lines" :key="line.key" class="trend-tip-row" :class="{ 'is-dim': dimmed(line) }">
              <span class="trend-swatch" :style="{ background: shade(line) }"></span>
              <span class="trend-tip-name">{{ line.label }}</span>
              <span class="trend-tip-figures">{{ readout(line, hovered) }}</span>
            </p>
          </div>
        </template>
      </div>
      <div class="trend-axis" aria-hidden="true">
        <span v-for="year in x_ticks" :key="year" class="trend-x-label" :style="{ left: place(year) + '%' }">{{ year }}</span>
      </div>
      <p class="trend-x-title">Year released</p>
    </div>
    <p v-for="label in missing" :key="label" class="stat-note">{{ label }} has too few runs per year to plot.</p>
    <div class="stat-note trend-key" role="group" aria-label="Highlight lines. Click to select several; double-click to clear.">
      <button v-for="line in lines" :key="line.key" type="button" class="trend-key-item" :class="{ 'is-dim': dimmed(line) }"
              :aria-pressed="String(selected.includes(line.key))"
              @click="selected = toggleKey(selected, line.key)" @dblclick.prevent="selected = []">
        <span class="trend-swatch" :style="{ background: shade(line) }" aria-hidden="true"></span>{{ line.label }} ({{ line.total_runs.toLocaleString('en-US') }} runs)<template v-if="extrapolate && selected.includes(line.key)">, predicted 100% year: {{ line.full === null ? 'none (trend not rising)' : predictedYear(line) }}</template>
      </button>
      <button type="button" class="trend-reset" @click="selected = []">Reset</button>
    </div>
  </section>
</template>

<script>
import ChartDownload from '@/components/statistics/ChartDownload.vue'
import SUMMARIES from '@/constants/groupSummaries.json'
import { toggleKey, isDimmed } from '@/components/statistics/density'
import { groupColour } from '@/components/statistics/groupColours'
import { yearTrendTable } from '@/components/statistics/chartTables'

const MIN_YEAR_RUNS = 10
const Y_TICKS = [0, 25, 50, 75, 100]
const DARKEN = colour => `color-mix(in srgb, ${colour} 55%, black)`
// A gut series shares its host's hue, darkened, so the pair reads together.
const withGut = (name, label, colour) => [
  { key: name, label: label + ' (non-gut)', colour },
  { key: name + '_gut', label: label + ' (gut)', colour: DARKEN(colour) }
]

// What each chart plots: where its series sit in the summary, and how they look. `extrapolated` is the
// lines selected for the reader when they switch extrapolation on, so their predicted years show at once.
const SPECS = {
  overall: {
    id: 'known-by-year',
    title: 'Known species fraction by release year',
    intro: 'The mean fraction of the metagenomes released in each year that is assigned to the species level, for host-associated and ecological runs.',
    fitNote: '',
    source: key => SUMMARIES.yearly_known && SUMMARIES.yearly_known[key],
    always_fit: true,
    extrapolated: ['host_associated', 'ecological'],
    series: [
      { key: 'host_associated', label: 'Host-associated', colour: 'var(--color-sample-host)' },
      { key: 'ecological', label: 'Ecological', colour: 'var(--color-sample-ecological)' }
    ],
    noun: 'host-associated and ecological'
  },
  host: {
    id: 'known-by-year-host',
    title: 'Known species fraction by release year: eukaryotic host-associated samples',
    intro: 'The same, for host-associated runs by host. For human and mouse, gut samples (“<name> gut metagenome” and “<name> feces metagenome”) are plotted apart from every other body site (“<name> metagenome”, “<name> oral metagenome” and so on). Bovine and pig have too few runs to split, so each is a single line covering all of its “<name> … metagenome” labels, gut included. Plant is the runs labelled “plant metagenome”. Labels that name a virus, or that do not name a host, are left out.',
    fitNote: ' (drawn for the lines you select)',
    source: key => SUMMARIES.yearly_known_groups && SUMMARIES.yearly_known_groups.host && SUMMARIES.yearly_known_groups.host[key],
    always_fit: false,
    extrapolated: ['human_gut', 'bovine'],
    series: [
      ...withGut('human', 'Human', groupColour('human')), ...withGut('mouse', 'Mouse', groupColour('mouse')),
      { key: 'pig', label: 'Pig', colour: groupColour('pig') }, { key: 'bovine', label: 'Bovine', colour: groupColour('bovine') },
      { key: 'plant', label: 'Plant', colour: groupColour('plant') }
    ],
    noun: 'host-associated'
  },
  ecological: {
    id: 'known-by-year-ecological',
    title: 'Known species fraction by release year: ecological samples',
    intro: 'The same, for ecological runs by environment. Each group is the runs whose organism is “<name> metagenome”.',
    fitNote: ' (drawn for the lines you select)',
    source: key => SUMMARIES.yearly_known_groups && SUMMARIES.yearly_known_groups.ecological && SUMMARIES.yearly_known_groups.ecological[key],
    always_fit: false,
    extrapolated: ['freshwater', 'soil', 'sediment'],
    series: [
      { key: 'soil', label: 'Soil', colour: groupColour('soil') }, { key: 'sediment', label: 'Sediment', colour: groupColour('sediment') },
      { key: 'marine', label: 'Marine', colour: groupColour('marine') }, { key: 'freshwater', label: 'Freshwater', colour: groupColour('freshwater') },
      { key: 'aquatic', label: 'Aquatic', colour: groupColour('aquatic') }
    ],
    noun: 'ecological'
  }
}
const LONG_SPAN = 12
// Past these spans (years) the axis labels every 20 or every 10 years, so extrapolating far does not crowd it.
const TICK_SPANS = [{ over: 60, step: 20 }, { over: 30, step: 10 }]
// A year label this far along the plot is set to end at its point, not centre on it, so it stays inside.
const RIGHT_EDGE_PERCENT = 92
// The fraction a dashed line stops at when extrapolating.
const FULL = 100
const DIM_COLOUR = 'var(--color-rule)'
// Marked on every chart with a vertical line.
const CURRENT_YEAR = new Date().getFullYear()

export default {
  name: 'YearTrendChart',
  components: { ChartDownload },
  props: {
    kind: { type: String, default: 'overall', validator: value => value in SPECS }
  },
  data () {
    return { hovered: null, hoveredLine: null, selected: [], extrapolate: false, CURRENT_YEAR, MIN_YEAR_RUNS, Y_TICKS, RIGHT_EDGE_PERCENT }
  },
  watch: {
    // Switching extrapolation on with nothing selected selects the chart's default lines; switching it off
    // clears them again unless the reader has changed the selection.
    extrapolate (on) {
      const defaults = this.spec.extrapolated.filter(key => this.series.some(item => item.key === key))
      const untouched = this.selected.length === defaults.length && defaults.every(key => this.selected.includes(key))
      if (on && this.selected.length === 0) this.selected = defaults
      else if (!on && untouched) this.selected = []
    }
  },
  computed: {
    spec () { return SPECS[this.kind] },
    series () {
      const totalRuns = item => item.points.reduce((sum, point) => sum + point.runs, 0)
      // Legend order: the group with the most runs first.
      return this.spec.series.filter(item => this.spec.source(item.key))
        .map(item => ({ ...item, ...this.spec.source(item.key), total_runs: totalRuns(this.spec.source(item.key)) }))
        .sort((a, b) => totalRuns(b) - totalRuns(a))
    },
    missing () {
      return this.spec.series.filter(item => !this.spec.source(item.key)).map(item => item.label)
    },
    years () {
      return this.series.flatMap(item => item.points.map(point => point.year))
    },
    first () { return Math.min(...this.years) },
    last () { return Math.max(...this.years) },
    // Where each drawn dashed line ends, as a year: the last year it was fitted to, or with extrapolation
    // the year it reaches 100%. A line that reaches 100% within the data stops there either way.
    fitEnds () {
      return Object.fromEntries(this.series.map(item => [item.key, this.fitSpan(item)]))
    },
    // The last year on the axis: the later of the last year of data and the current year, or with extrapolation
    // far enough out to hold every drawn dashed line.
    axisLast () {
      const shown = Math.max(this.last, CURRENT_YEAR)
      if (!this.extrapolate) return shown
      const ends = this.series.filter(item => this.showFit(item) && this.fitEnds[item.key]).map(item => this.fitEnds[item.key].end)
      return Math.max(shown, Math.ceil(Math.max(...ends, shown)))
    },
    x_ticks () {
      const span = this.axisLast - this.first
      const step = span > TICK_SPANS[0].over ? TICK_SPANS[0].step : span > TICK_SPANS[1].over ? TICK_SPANS[1].step : span > LONG_SPAN ? 4 : 2
      const ticks = []
      for (let year = Math.ceil(this.first / step) * step; year <= this.axisLast; year += step) ticks.push(year)
      return ticks
    },
    lines () {
      const clamp = value => Math.min(Math.max(value, 0), 100)
      return this.series.map(item => {
        const dots = item.points.map(point => ({ year: point.year, x: this.place(point.year), y: clamp(point.mean) }))
        const span = this.fitEnds[item.key]
        return {
          ...item,
          dots,
          points: dots.map(dot => `${dot.x},${100 - dot.y}`).join(' '),
          full: span ? span.full : null,
          fit: span && [
            this.place(span.start), 100 - clamp(span.startValue), this.place(span.end), 100 - clamp(span.endValue)]
        }
      })
    },
    // Greyed-out lines first, so the highlighted ones are drawn over them.
    drawn () {
      return [...this.lines].sort((a, b) => Number(this.dimmed(b)) - Number(this.dimmed(a)))
    },
    aria () {
      const names = this.series.map(item => item.label.toLowerCase())
      const list = this.kind === 'overall' ? names.join(' and ') : names.join(', ')
      return `Mean known species fraction by release year, ${this.first} to ${this.last}, for ${this.spec.noun} runs: ${list}.`
    }
  },
  methods: {
    // Every line's mean known species fraction by year (the fitted trend lines are not included).
    table () {
      return yearTrendTable(this.series)
    },
    toggleKey,
    // Selected lines stay bright whatever is hovered, so two of them can be followed to where they cross;
    // hovering another line brightens it as well. With nothing selected, hovering picks out one line.
    dimmed (line) {
      if (line.key === this.hoveredLine) return false
      return this.selected.length > 0 ? isDimmed(this.selected, line.key) : this.hoveredLine !== null
    },
    showFit (line) {
      return Boolean(line.fit !== null && this.fitEnds[line.key]) && (this.spec.always_fit || this.selected.includes(line.key))
    },
    // A series' dashed line as { start, startValue, end, endValue, full } in years and percent (full: the year the
    // line reaches 100%, or null if it never does), from its two fitted points: straight on to 100% when
    // extrapolating, and never past 100%. Null when it never gets below 100%.
    fitSpan (item) {
      const [from, to] = item.fit
      const slope = (to.value - from.value) / (to.year - from.year)
      const valueAt = year => from.value + slope * (year - from.year)
      if (slope > 0 && from.value >= FULL) return null
      const reaches = slope > 0 ? from.year + (FULL - from.value) / slope : Infinity
      const end = this.extrapolate && slope > 0 ? reaches : Math.min(to.year, reaches)
      return { start: from.year, startValue: from.value, end, endValue: valueAt(end), full: Number.isFinite(reaches) ? reaches : null }
    },
    // The whole year a line reaches 100% in (the nearest year to where it crosses).
    predictedYear (line) {
      return Math.round(line.full)
    },
    shade (line) {
      return this.dimmed(line) ? DIM_COLOUR : line.colour
    },
    // Position along the plot, with half a year of room at each end.
    place (year) {
      return (100 * (year - this.first + 0.5)) / (this.axisLast - this.first + 1)
    },
    move (event) {
      const box = event.currentTarget.getBoundingClientRect()
      if (box.width === 0) return
      const along = Math.min(Math.max((event.clientX - box.left) / box.width, 0), 1)
      this.hovered = Math.min(this.last, Math.max(this.first, Math.floor(this.first - 0.5 + along * (this.axisLast - this.first + 1) + 0.5)))
    },
    readout (line, year) {
      const point = line.points_by_year[year]
      return point ? `${point.mean}% of ${point.runs.toLocaleString('en-US')} runs` : 'no data'
    }
  },
  created () {
    // Index each series' points by year once, for the hover readout.
    this.series.forEach(item => { item.points_by_year = Object.fromEntries(item.points.map(point => [point.year, point])) })
  }
}
</script>

<style scoped>
.stat-note.is-wide { max-width: none; }
.trend-switch { margin-top: var(--space-4); }
.trend-predicted { position: absolute; top: 0; z-index: 4; transform: translate(-50%, -110%); font-size: 0.75rem; font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; pointer-events: none; }
.trend-predicted.is-right-edge { transform: translate(-100%, -110%); }
.trend-predicted.is-dim { opacity: 0.5; }
.trend-extrapolation { margin-top: var(--space-2); }
.stat-note { font-size: 0.9rem; line-height: 1.5; color: var(--color-ink-muted); }
.section.container { padding-top: var(--space-8); padding-bottom: var(--space-4); }
.trend-chart { position: relative; margin: var(--space-6) 0 var(--space-2) 4.4rem; --plot-height: 16rem; }
/* The long y-axis title does not fit the short phone plot, so phones get a shorter one. */
.trend-y-short { display: none; }
@media (max-width: 640px) {
  .trend-chart { margin-left: 3.8rem; margin-right: var(--space-2); --plot-height: 12rem; }
  .trend-y-title { left: -3.8rem; font-size: 0.75rem; white-space: nowrap; }
  .trend-y-long { display: none; }
  .trend-y-short { display: inline; }
  .trend-x-label { font-size: 0.7rem; }
}
.trend-y-title { position: absolute; top: 0; left: -4.4rem; display: flex; align-items: center; justify-content: center; width: 1.4rem; height: var(--plot-height); font-size: 0.85rem; writing-mode: vertical-rl; transform: rotate(180deg); color: var(--color-ink-muted); }
.trend-plot { position: relative; height: var(--plot-height); border-left: 1px solid var(--color-rule); border-bottom: 1px solid var(--color-rule); touch-action: pan-y; }
.trend-gridline { position: absolute; left: 0; right: 0; border-top: 1px solid var(--color-track); }
.trend-tick-label { position: absolute; right: calc(100% + var(--space-2)); top: 0; transform: translateY(-50%); font-size: 0.8rem; font-variant-numeric: tabular-nums; color: var(--color-ink-muted); white-space: nowrap; }
.trend-svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.trend-hit { stroke: transparent; stroke-width: 12; pointer-events: stroke; cursor: pointer; }
.trend-stroke { stroke-width: 2; stroke-linejoin: round; }
.trend-fit { stroke-width: 2; stroke-dasharray: 6 5; }
.trend-dot { position: absolute; width: 0.55rem; height: 0.55rem; margin: 0 0 -0.275rem -0.275rem; border-radius: 50%; pointer-events: none; }
.trend-now { position: absolute; top: 0; bottom: 0; width: 0; border-left: 1px solid var(--color-ink-muted); pointer-events: none; }
.trend-now-label { position: absolute; top: var(--space-1); right: var(--space-1); font-size: 0.7rem; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1; color: var(--color-ink-muted); white-space: nowrap; }
.trend-guide { position: absolute; top: 0; bottom: 0; width: 0; border-left: 1px dashed var(--color-ink-muted); pointer-events: none; }
.trend-tip { position: absolute; top: var(--space-2); z-index: 5; margin-left: var(--space-3); min-width: 12rem; max-width: 18rem; padding: var(--space-2) var(--space-3); font-size: 0.8rem; line-height: 1.4; color: var(--color-ink); background: var(--color-surface); border: 1px solid var(--color-rule); border-radius: var(--radius-bar); pointer-events: none; }
.trend-tip.is-left { margin-left: 0; transform: translateX(calc(-100% - var(--space-3))); }
.trend-tip-year { font-weight: 600; }
.trend-tip-row { display: grid; grid-template-columns: auto minmax(0, 1fr); column-gap: var(--space-2); align-items: baseline; margin-top: var(--space-1); }
.trend-tip-name { font-weight: 600; }
.trend-tip-figures { grid-column: 2; font-variant-numeric: tabular-nums; color: var(--color-ink-muted); }
.trend-axis { position: relative; height: 1.4rem; }
.trend-x-label { position: absolute; top: var(--space-1); transform: translateX(-50%); font-size: 0.8rem; color: var(--color-ink-muted); white-space: nowrap; }
.trend-x-title { margin-top: var(--space-1); font-size: 0.85rem; text-align: center; color: var(--color-ink-muted); }
/* Two columns filled top to bottom, so the order by runs reads down the left column and then the right. */
.trend-key { column-count: 2; column-gap: var(--space-8); }
.trend-key-item, .trend-reset { display: block; width: 100%; margin-bottom: var(--space-1); text-align: left; break-inside: avoid; }
@media (max-width: 640px) { .trend-key { column-count: 1; } }
.trend-stroke.is-dim, .trend-fit.is-dim { stroke-width: 1.5; }
.trend-dot.is-dim { opacity: 0.6; }
.trend-tip-row.is-dim { opacity: 0.5; }
.trend-key-item, .trend-reset { font: inherit; color: var(--color-ink); background: none; border: 1px solid transparent; border-radius: var(--radius-bar); padding: 0 var(--space-2); cursor: pointer; touch-action: manipulation; user-select: none; }
.trend-key-item[aria-pressed="true"] { border-color: var(--color-ink-muted); font-weight: 600; }
.trend-key-item.is-dim { color: var(--color-ink-muted); }
.trend-key-item:hover, .trend-reset:hover { border-color: var(--color-rule); }
.trend-key-item:focus-visible, .trend-reset:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.trend-reset { color: var(--color-ink-muted); text-decoration: underline; }
.section-anchor:active { color: var(--color-accent-strong); }
.section-anchor:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
</style>
