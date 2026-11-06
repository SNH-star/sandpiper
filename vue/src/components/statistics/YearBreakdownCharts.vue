<template>
  <div>
    <div class="stack-chart" role="img" :aria-label="stackLabel">
      <div v-for="row in year_rows" :key="row.year" class="stack-col" :title="row.title">
        <div class="stack-area">
          <span class="stack-bar" :style="{ height: row.height + '%' }">
            <span v-for="part in row.parts" :key="part.key" :class="'type-' + part.key" :style="{ height: part.percent + '%' }"></span>
          </span>
        </div>
        <span class="stack-label">{{ row.year }}</span>
      </div>
      <svg class="stack-line" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <polyline :points="cumulative_points" fill="none" vector-effect="non-scaling-stroke" />
      </svg>
    </div>
    <p class="stat-note key">
      <span v-for="item in TYPES" :key="item.key"><span class="swatch" :class="'type-' + item.key" aria-hidden="true"></span>{{ item.label }}</span>
      <span><span class="swatch line-swatch" aria-hidden="true"></span>Running total, {{ total.toLocaleString('en-US') }} runs</span>
    </p>
  </div>
</template>

<script>
const TYPES = [
  { key: 'host_associated', label: 'Host-associated' },
  { key: 'ecological', label: 'Ecological' },
  { key: 'unclassified', label: 'Unclassified' }
]

export default {
  name: 'YearBreakdownCharts',
  props: { data: { type: Object, required: true } },
  data () { return { TYPES } },
  computed: {
    total () {
      const years = this.data.years
      return years.length ? years[years.length - 1].cumulative : 0
    },
    year_rows () {
      const most = Math.max(...this.data.years.map(row => row.host_associated + row.ecological + row.unclassified), 1)
      return this.data.years.map(row => {
        const runs = row.host_associated + row.ecological + row.unclassified
        return {
          year: row.year,
          height: (100 * runs) / most,
          title: `${row.year}: ${runs.toLocaleString('en-US')} runs`,
          parts: TYPES.map(item => ({ key: item.key, percent: runs ? (100 * row[item.key]) / runs : 0 }))
        }
      })
    },
    cumulative_points () {
      const years = this.data.years
      return years.map((row, i) => `${(100 * (i + 0.5)) / years.length},${100 - (100 * row.cumulative) / this.total}`).join(' ')
    },
    stackLabel () {
      return `Runs per year, ${this.total.toLocaleString('en-US')} in total.`
    }
  }
}
</script>

<style scoped>
.stat-note { max-width: 62ch; font-size: 0.9rem; line-height: 1.5; color: var(--color-ink-muted); }
.stack-chart { position: relative; display: flex; align-items: stretch; gap: 2px; height: 14rem; margin: var(--space-6) 0 var(--space-6); border-bottom: 1px solid var(--color-rule); }
.stack-col { position: relative; display: flex; flex: 1 1 0; min-width: 0; flex-direction: column; }
.stack-area { display: flex; flex: 1; align-items: flex-end; }
.stack-bar { display: flex; width: 100%; flex-direction: column-reverse; overflow: hidden; border-radius: var(--radius-bar) var(--radius-bar) 0 0; }
.stack-bar.full { height: 100%; }
.stack-bar > span { display: block; }
.stack-label { position: absolute; bottom: -1.4rem; left: 50%; font-size: 0.75rem; color: var(--color-ink-muted); transform: translateX(-50%); white-space: nowrap; }
@media (max-width: 640px) { .stack-col:nth-child(even) .stack-label { visibility: hidden; } }
.stack-line { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.stack-line polyline { stroke: var(--color-ink); stroke-width: 2; }
.key { display: flex; flex-wrap: wrap; gap: var(--space-1) var(--space-6); margin-top: var(--space-6); }
.swatch { display: inline-block; width: 0.8rem; height: 0.8rem; margin-right: var(--space-2); border-radius: var(--radius-bar); }
.line-swatch { height: 2px; vertical-align: middle; background: var(--color-ink); }
.type-host_associated { background: var(--color-sample-host); }
.type-ecological { background: var(--color-sample-ecological); }
.type-unclassified { background: var(--color-sample-unclassified); }
</style>
