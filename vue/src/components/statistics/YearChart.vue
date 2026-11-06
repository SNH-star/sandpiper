<template>
  <div>
    <div class="year-chart" role="group" :aria-label="chartLabel">
      <div
        v-for="row in rows"
        :key="row.year"
        class="year-col"
        :class="{ 'is-selected': selectedYear === row.year }"
        :title="row.title"
        tabindex="0"
        :aria-pressed="String(selectedYear === row.year)"
        :aria-label="row.title"
        @click="pick(row.year)"
        @keydown.enter.prevent="pick(row.year)"
        @keydown.space.prevent="pick(row.year)">
        <div class="year-area">
          <span class="year-value">{{ row.short }}</span>
          <span class="year-bar" :class="{ 'is-partial': row.is_partial, 'is-split': isSplit }" :style="{ height: row.height + '%' }">
            <template v-if="isSplit">
              <span v-for="part in row.parts" :key="part.key" :class="'type-' + part.key" :style="{ height: part.percent + '%' }"></span>
            </template>
          </span>
        </div>
        <span class="year-label">{{ row.year }}</span>
      </div>
      <svg v-if="isSplit" class="year-line" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <polyline :points="cumulativePoints" fill="none" vector-effect="non-scaling-stroke" />
      </svg>
    </div>
    <p class="stat-note year-readout" aria-live="polite">{{ readout }}</p>
    <div class="stat-note year-key">
      <template v-if="isSplit">
        <span v-for="item in TYPES" :key="item.key"><span class="year-swatch" :class="'type-' + item.key" aria-hidden="true"></span>{{ item.label }}</span>
        <span><span class="year-swatch year-line-swatch" aria-hidden="true"></span>Running total, {{ total.toLocaleString('en-US') }} runs</span>
      </template>
      <span v-else><span class="year-swatch type-all" aria-hidden="true"></span>Runs released</span>
      <span v-if="partialRow"><span class="year-swatch is-partial" aria-hidden="true"></span>{{ partialRow.year }} is partial: runs released before {{ partialDate }}</span>
    </div>
  </div>
</template>

<script>
// The tallest bar leaves this share of the plot free for its value label.
const TALLEST_BAR_PERCENT = 85
const SHORT_NUMBER = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })
const TYPES = [
  { key: 'host_associated', label: 'Host-associated' },
  { key: 'ecological', label: 'Ecological' },
  { key: 'unclassified', label: 'Unclassified' }
]

// Runs per release year, as plain bars or split by Sandpiper's sample call with a
// running-total line. Both modes share one geometry, so switching only adds detail.
export default {
  name: 'YearChart',
  props: {
    years: { type: Array, required: true },
    // Per-year runs by sample call, from the breakdown query; when absent the bars are plain.
    breakdown: { type: Object, default: null },
    partialDate: { type: String, default: '' }
  },
  data () { return { TYPES, selectedYear: null } },
  methods: {
    // Selecting the chosen year again clears it.
    pick (year) {
      this.selectedYear = this.selectedYear === year ? null : year
    }
  },
  computed: {
    isSplit () {
      return this.breakdown !== null && Array.isArray(this.breakdown.years)
    },
    byYear () {
      return new Map((this.isSplit ? this.breakdown.years : []).map(row => [row.year, row]))
    },
    total () {
      return this.years.reduce((sum, row) => sum + row.runs, 0)
    },
    rows () {
      const most = Math.max(...this.years.map(row => row.runs), 1)
      return this.years.map((row, i) => {
        const counts = this.byYear.get(row.year)
        const counted = counts ? TYPES.reduce((sum, item) => sum + counts[item.key], 0) : 0
        return {
          year: row.year,
          runs: row.runs,
          short: SHORT_NUMBER.format(row.runs),
          height: Math.max((TALLEST_BAR_PERCENT * row.runs) / most, 1),
          is_partial: i === this.years.length - 1,
          title: `${row.year}: ${row.runs.toLocaleString('en-US')} runs`,
          parts: TYPES.map(item => ({ key: item.key, percent: counted ? (100 * counts[item.key]) / counted : 0 }))
        }
      })
    },
    // What a click or tap on a bar shows: touch screens have no hover.
    readout () {
      const row = this.rows.find(item => item.year === this.selectedYear)
      if (!row) return 'Tap or click a bar to see its number of runs.'
      const counts = this.byYear.get(row.year)
      if (!counts) return row.title
      const split = TYPES.map(item => `${item.label.toLowerCase()} ${counts[item.key].toLocaleString('en-US')}`).join(', ')
      return `${row.title} (${split})`
    },
    partialRow () {
      return this.rows.length ? this.rows[this.rows.length - 1] : null
    },
    cumulativePoints () {
      let running = 0
      const bars = this.years.length
      return this.years.map((row, i) => {
        running += row.runs
        return `${(100 * (i + 0.5)) / bars},${100 - (100 * running) / this.total}`
      }).join(' ')
    },
    chartLabel () {
      const first = this.years[0]
      const last = this.years[this.years.length - 1]
      const split = this.isSplit ? ', split by sample call, with the running total' : ''
      return `Column chart of runs released each year, from ${first.runs.toLocaleString('en-US')} in ${first.year} to ${last.runs.toLocaleString('en-US')} in ${last.year}${split}`
    }
  }
}
</script>

<style scoped>
.year-chart {
  --label-height: 1.5rem;
  position: relative;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(0, 1fr);
  gap: var(--space-1);
  height: 16rem;
  margin-top: var(--space-6);
  border-bottom: 1px solid var(--color-rule);
}
.year-col {
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.year-col:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.year-col.is-selected .year-bar { outline: 2px solid var(--color-ink); outline-offset: 1px; }
.year-readout { min-height: 1.5em; margin-top: var(--space-3); color: var(--color-ink); font-variant-numeric: tabular-nums; }
.year-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: stretch;
  min-height: 0;
}
.year-value {
  font-size: 0.72rem;
  font-variant-numeric: tabular-nums;
  text-align: center;
  color: var(--color-ink-muted);
}
.year-bar {
  position: relative;
  display: block;
  margin-top: 2px;
  border-radius: var(--radius-bar) var(--radius-bar) 0 0;
  background: var(--color-accent);
}
.year-bar.is-split {
  display: flex;
  flex-direction: column-reverse;
  overflow: hidden;
  background: none;
}
.year-bar.is-split > span {
  display: block;
}
/* The partial year: the bar's own colours with surface stripes cut through them. */
.year-bar.is-partial::after {
  content: '';
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(135deg, transparent 0 3px, var(--color-surface) 3px 6px);
  outline: 1px solid var(--color-accent);
  outline-offset: -1px;
}
.year-bar.is-split.is-partial::after {
  outline-color: var(--color-ink-muted);
}
.year-label {
  position: relative;
  left: 50%;
  width: max-content;
  height: var(--label-height);
  padding-top: var(--space-1);
  font-size: 0.72rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  transform: translateX(-50%);
  color: var(--color-ink-muted);
}
/* The line spans the bars only, not the row of year labels beneath them. */
.year-line {
  position: absolute;
  top: 0;
  right: 0;
  bottom: var(--label-height);
  left: 0;
  width: 100%;
  height: calc(100% - var(--label-height));
  pointer-events: none;
}
.year-line polyline {
  stroke: var(--color-ink);
  stroke-width: 2;
}

.stat-note {
  max-width: 62ch;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--color-ink-muted);
}
.year-key {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-6);
  max-width: none;
  margin-top: var(--space-4);
}
.year-swatch {
  display: inline-block;
  width: 0.8rem;
  height: 0.8rem;
  margin-right: var(--space-2);
  border-radius: var(--radius-bar);
}
.year-line-swatch {
  height: 2px;
  vertical-align: middle;
  background: var(--color-ink);
}
.year-swatch.is-partial {
  background: repeating-linear-gradient(135deg, var(--color-ink-muted) 0 2px, var(--color-surface) 2px 4px);
  outline: 1px solid var(--color-ink-muted);
  outline-offset: -1px;
}
.type-all { background: var(--color-accent); }
.type-host_associated { background: var(--color-sample-host); }
.type-ecological { background: var(--color-sample-ecological); }
.type-unclassified { background: var(--color-sample-unclassified); }

@media (max-width: 768px) {
  .year-chart {
    height: 13rem;
  }
  .year-col:nth-child(even) .year-label {
    visibility: hidden;
  }
  .year-value {
    display: none;
  }
}
</style>
