<template>
  <section id="known-by-year" class="section container stat-figure">
    <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#known-by-year">#</a> Known species fraction by release year</h3>
    <p class="stat-note">
      The mean fraction of the metagenomes released in each year that is assigned to the species level, for
      host-associated and ecological runs, counting only species that had a genome available the year before (by the
      NCBI date of the species’ earliest genome in GTDB). Dashed lines are linear trends weighted by the number of
      runs. Years with fewer than {{ MIN_YEAR_RUNS }} runs are left out, and the earliest years rest on few runs, so
      they vary more.
    </p>
    <div class="trend-chart">
      <p class="trend-y-title"><span class="trend-y-long">Mean known species fraction (%)</span><span class="trend-y-short">Known species (%)</span></p>
      <div class="trend-plot" role="img" :aria-label="aria" @pointermove="move" @pointerdown="move" @pointerleave="hovered = null">
        <div v-for="tick in Y_TICKS" :key="tick" class="trend-gridline" :style="{ bottom: tick + '%' }">
          <span class="trend-tick-label">{{ tick }}</span>
        </div>
        <svg class="trend-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <template v-for="line in drawn" :key="line.key">
            <polyline :points="line.points" :style="{ stroke: shade(line) }" class="trend-stroke" :class="{ 'is-dim': dimmed(line) }" fill="none" vector-effect="non-scaling-stroke" />
            <line :x1="line.fit[0]" :y1="line.fit[1]" :x2="line.fit[2]" :y2="line.fit[3]" :style="{ stroke: shade(line) }" class="trend-fit" :class="{ 'is-dim': dimmed(line) }" vector-effect="non-scaling-stroke" />
          </template>
        </svg>
        <template v-for="line in drawn" :key="'dots-' + line.key">
          <span v-for="point in line.dots" :key="point.year" class="trend-dot" :class="{ 'is-dim': dimmed(line) }" :style="{ left: point.x + '%', bottom: point.y + '%', background: shade(line) }"></span>
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
    <div class="stat-note trend-key" role="group" aria-label="Highlight lines. Click to select several; double-click to clear.">
      <button v-for="line in lines" :key="line.key" type="button" class="trend-key-item" :class="{ 'is-dim': dimmed(line) }"
              :aria-pressed="String(selected.includes(line.key))"
              @click="selected = toggleKey(selected, line.key)" @dblclick.prevent="selected = []">
        <span class="trend-swatch" :style="{ background: shade(line) }" aria-hidden="true"></span>{{ line.label }}
      </button>
      <button type="button" class="trend-reset" @click="selected = []">Reset</button>
    </div>
  </section>
</template>

<script>
import SUMMARIES from '@/constants/groupSummaries.json'
import { toggleKey, isDimmed } from '@/components/statistics/density'

const MIN_YEAR_RUNS = 10
const Y_TICKS = [0, 25, 50, 75, 100]
const SERIES = [
  { key: 'host_associated', label: 'Host-associated', colour: 'var(--color-sample-host)' },
  { key: 'ecological', label: 'Ecological', colour: 'var(--color-sample-ecological)' }
]
const LONG_SPAN = 12
const DIM_COLOUR = 'var(--color-rule)'

export default {
  name: 'YearTrendChart',
  data () {
    return { hovered: null, selected: [], MIN_YEAR_RUNS, Y_TICKS }
  },
  computed: {
    series () {
      const totalRuns = item => item.points.reduce((sum, point) => sum + point.runs, 0)
      // Legend order: the group with the most runs first.
      return SERIES.filter(item => SUMMARIES.yearly_known[item.key])
        .map(item => ({ ...item, ...SUMMARIES.yearly_known[item.key] }))
        .sort((a, b) => totalRuns(b) - totalRuns(a))
    },
    years () {
      return this.series.flatMap(item => item.points.map(point => point.year))
    },
    first () { return Math.min(...this.years) },
    last () { return Math.max(...this.years) },
    x_ticks () {
      const step = this.last - this.first > LONG_SPAN ? 4 : 2
      const ticks = []
      for (let year = Math.ceil(this.first / step) * step; year <= this.last; year += step) ticks.push(year)
      return ticks
    },
    lines () {
      const clamp = value => Math.min(Math.max(value, 0), 100)
      return this.series.map(item => {
        const dots = item.points.map(point => ({ year: point.year, x: this.place(point.year), y: clamp(point.mean) }))
        return {
          ...item,
          dots,
          points: dots.map(dot => `${dot.x},${100 - dot.y}`).join(' '),
          fit: [this.place(item.fit[0].year), 100 - clamp(item.fit[0].value), this.place(item.fit[1].year), 100 - clamp(item.fit[1].value)]
        }
      })
    },
    // Greyed-out lines first, so the highlighted ones are drawn over them.
    drawn () {
      return [...this.lines].sort((a, b) => Number(this.dimmed(b)) - Number(this.dimmed(a)))
    },
    aria () {
      return `Mean known species fraction by release year, ${this.first} to ${this.last}, for ${this.series.map(item => item.label.toLowerCase()).join(' and ')} runs.`
    }
  },
  methods: {
    toggleKey,
    dimmed (line) {
      return isDimmed(this.selected, line.key)
    },
    shade (line) {
      return this.dimmed(line) ? DIM_COLOUR : line.colour
    },
    // Position along the plot, with half a year of room at each end.
    place (year) {
      return (100 * (year - this.first + 0.5)) / (this.last - this.first + 1)
    },
    move (event) {
      const box = event.currentTarget.getBoundingClientRect()
      if (box.width === 0) return
      const along = Math.min(Math.max((event.clientX - box.left) / box.width, 0), 1)
      this.hovered = Math.min(this.last, Math.max(this.first, Math.floor(this.first - 0.5 + along * (this.last - this.first + 1) + 0.5)))
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
.stat-note { max-width: 62ch; font-size: 0.9rem; line-height: 1.5; color: var(--color-ink-muted); }
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
.trend-stroke { stroke-width: 2; stroke-linejoin: round; }
.trend-fit { stroke-width: 2; stroke-dasharray: 6 5; }
.trend-dot { position: absolute; width: 0.55rem; height: 0.55rem; margin: 0 0 -0.275rem -0.275rem; border-radius: 50%; pointer-events: none; }
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
.trend-key { display: flex; flex-wrap: wrap; gap: var(--space-1) var(--space-6); }
.trend-stroke.is-dim, .trend-fit.is-dim { stroke-width: 1.5; }
.trend-dot.is-dim { opacity: 0.6; }
.trend-tip-row.is-dim { opacity: 0.5; }
.trend-key-item, .trend-reset { font: inherit; color: var(--color-ink); background: none; border: 1px solid transparent; border-radius: var(--radius-bar); padding: 0 var(--space-2); cursor: pointer; touch-action: manipulation; user-select: none; }
.trend-key-item[aria-pressed="true"] { border-color: var(--color-ink-muted); font-weight: 600; }
.trend-key-item.is-dim { color: var(--color-ink-muted); }
.trend-key-item:hover, .trend-reset:hover { border-color: var(--color-rule); }
.trend-key-item:focus-visible, .trend-reset:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.trend-reset { color: var(--color-ink-muted); text-decoration: underline; }
.trend-swatch { display: inline-block; width: 0.8rem; height: 0.8rem; margin-right: var(--space-2); border-radius: var(--radius-bar); }
.section-anchor:active { color: var(--color-accent-strong); }
.section-anchor:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
</style>
