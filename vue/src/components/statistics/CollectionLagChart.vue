<template>
  <div v-if="summary" id="collection-to-release-chart" class="lag-figure">
    <p class="stat-note">
      Time from sample collection to public release of its sequencing data, for runs whose collection date is
      recorded to the day. A date range that starts on a specific day is placed at its midpoint. Each curve is a
      density with area 1; runs are weighted equally, so large projects can produce sharp peaks.
    </p>
    <p v-if="chart" class="stat-note lag-shown">
      Showing {{ count(plottedRuns) }} of {{ count(summary.database_runs) }} host-associated and ecological runs ({{ percent(plottedRuns) }}%).
    </p>
    <density-chart v-if="chart" :chart="chart" interactive bare vertical-lines @update:selected="setHighlighted" />
    <p v-if="chart && beyondAxis > 0" class="stat-note lag-footnote">
      {{ count(beyondAxis) }} further runs were released more than {{ summary.months / MONTHS_PER_YEAR }} years after collection and are not drawn.
    </p>
    <p v-if="chart && negativeLags > 0" class="stat-note lag-footnote">
      {{ count(negativeLags) }} further runs have a collection date after their release date and are not drawn.
    </p>
    <p v-if="!chart" class="stat-note">No runs have a collection date recorded to the day.</p>
    <div class="stat-note lag-left-out">
      <p class="lag-left-out-title">Runs not drawn, because their collection date is less precise:</p>
      <ul class="lag-left-out-list">
        <li v-for="item in leftOut" :key="item.key">
          <span class="lag-left-out-label">{{ item.label }}:</span>
          {{ count(item.runs) }} runs ({{ percent(item.runs) }}%)<template v-if="item.parts">, of which {{ item.parts }}</template>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import DensityChart from '@/components/statistics/DensityChart.vue'
import { buildDensityChart } from '@/components/statistics/density'
import SUMMARIES from '@/constants/groupSummaries.json'

const MONTHS_PER_YEAR = 12
const TICK_EVERY_YEARS = 3
const MEDIAN_DECIMALS = 1

// Only runs whose collection date is recorded to the day are drawn: a month or a year gives no real lag,
// only one measured from an assumed midpoint.
const DRAWN_PRECISION = 'day'

// The runs left out of the chart, in the order they are listed under it. Only the first two are split by
// call in the summary.
const LEFT_OUT = [
  { key: 'month', label: 'Month only', byCall: true },
  { key: 'year', label: 'Year only', byCall: true },
  { key: 'none', label: 'No usable date', byCall: false }
]

// The two curves: the call each is made under in the summary, its label and its colour
// (the purple and green of the host and ecological circles on the maps).
const SERIES = [
  { call: 'host', label: 'Host-associated', colour: 'var(--color-sample-host)' },
  { call: 'ecological', label: 'Ecological', colour: 'var(--color-sample-ecological)' }
]

// 38 months as "3 y 2 mo"; under a year as "5 mo".
function monthsLabel (months) {
  const years = Math.floor(months / MONTHS_PER_YEAR)
  const rest = months % MONTHS_PER_YEAR
  return years === 0 ? `${rest} mo` : `${years} y ${rest} mo`
}

// The median, in years to one decimal, of a list of per-month run counts, placed within its month.
function medianOf (counts, runs) {
  let before = 0
  for (let month = 0; month < counts.length; month++) {
    if (before + counts[month] >= runs / 2) {
      return +((month + (runs / 2 - before) / counts[month]) / MONTHS_PER_YEAR).toFixed(MEDIAN_DECIMALS)
    }
    before += counts[month]
  }
  return +(counts.length / MONTHS_PER_YEAR).toFixed(MEDIAN_DECIMALS)
}

export default {
  name: 'CollectionLagChart',
  components: { DensityChart },
  data () {
    return {
      MONTHS_PER_YEAR,
      // Labels of the legend lines the reader has highlighted; none means every line counts.
      highlighted: []
    }
  },
  computed: {
    summary () {
      return SUMMARIES.collection_to_release || null
    },
    // Per call, the histogram of the runs dated to the day (null when it has no runs).
    histograms () {
      return Object.fromEntries(SERIES.map(item => {
        const counts = this.summary.counts[item.call][DRAWN_PRECISION]
        const runs = counts.reduce((total, n) => total + n, 0)
        if (runs === 0) return [item.call, null]
        return [item.call, {
          start: counts.map((_, month) => month / MONTHS_PER_YEAR),
          percent: counts.map(n => +(100 * n / runs).toFixed(3)),
          median: medianOf(counts, runs),
          runs
        }]
      }))
    },
    // Legend order: the call with the most runs first.
    present () {
      return SERIES.filter(item => this.histograms[item.call])
        .sort((a, b) => this.histograms[b.call].runs - this.histograms[a.call].runs)
    },
    // The curves the figures under the chart describe: the highlighted ones, or all when none is highlighted.
    counted () {
      const chosen = this.present.filter(item => this.highlighted.includes(this.lineLabel(item)))
      return chosen.length ? chosen : this.present
    },
    plottedRuns () {
      return this.counted.reduce((total, item) => total + this.histograms[item.call].runs, 0)
    },
    beyondAxis () {
      return this.sumOver('beyond_axis')
    },
    // Absent from a summary made before negative lags were counted.
    negativeLags () {
      return this.summary.negative ? this.sumOver('negative') : 0
    },
    // The runs the chart leaves out, with the host and ecological share where the summary has it.
    leftOut () {
      return LEFT_OUT.map(item => ({
        key: item.key,
        label: item.label,
        runs: this.summary.available[item.key],
        parts: item.byCall
          ? SERIES.map(series => `${this.count(this.runsOf(series.call, item.key))} ${series.label.toLowerCase()}`).join(' and ')
          : ''
      }))
    },
    chart () {
      if (this.present.length === 0) return null
      const lastYear = this.summary.months / MONTHS_PER_YEAR
      const ticks = []
      for (let years = 0; years <= lastYear; years += TICK_EVERY_YEARS) {
        ticks.push({ value: years, label: String(years) })
      }
      const everyYear = Array.from({ length: lastYear + 1 }, (_, years) => years)
      return buildDensityChart({
        key: 'collection_to_release',
        title: 'Time from collection to release',
        note: '',
        x_title: 'Years from collection to release',
        unit: ' years',
        y_title: 'Density (per year)',
        median_decimals: MEDIAN_DECIMALS,
        point_label: years => monthsLabel(Math.round(years * MONTHS_PER_YEAR)),
        x_step: 1 / MONTHS_PER_YEAR,
        x_ticks: ticks,
        x_grid: everyYear,
        series: this.present.map(item => ({
          colour: item.colour,
          label: this.lineLabel(item),
          histogram: this.histograms[item.call]
        }))
      })
    }
  },
  methods: {
    lineLabel (item) {
      return `${item.label} (${this.count(this.histograms[item.call].runs)} runs)`
    },
    setHighlighted (labels) {
      const same = labels.length === this.highlighted.length && labels.every(label => this.highlighted.includes(label))
      if (!same) this.highlighted = labels
    },
    // A summary count (`beyond_axis` or `negative`) of the drawn precision over the counted curves.
    sumOver (field) {
      return this.counted.reduce((total, item) => total + this.summary[field][item.call][DRAWN_PRECISION], 0)
    },
    // Every run of one call and precision: those on the axis, beyond it, and collected after release.
    runsOf (call, precision) {
      const onAxis = this.summary.counts[call][precision].reduce((total, n) => total + n, 0)
      const negative = this.summary.negative ? this.summary.negative[call][precision] : 0
      return onAxis + this.summary.beyond_axis[call][precision] + negative
    },
    count (n) {
      return n.toLocaleString('en-US')
    },
    percent (n) {
      return (100 * n / this.summary.database_runs).toFixed(1)
    }
  }
}
</script>

<style scoped>
.stat-note { font-size: 0.9rem; line-height: 1.5; color: var(--color-ink-muted); }
.lag-figure { min-width: 0; }
.lag-shown { margin: var(--space-4) 0 var(--space-2); }
.lag-footnote { margin-top: var(--space-2); }
.lag-left-out { margin-top: var(--space-4); }
.lag-left-out-title { margin-bottom: var(--space-1); }
.lag-left-out-list { margin: 0; padding-left: 1.2rem; list-style: disc; }
.lag-left-out-label { font-weight: 600; }
</style>
