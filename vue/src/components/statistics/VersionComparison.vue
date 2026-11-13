<template>
  <section id="compare-versions" class="section container stat-figure">
    <chart-download target="#compare-versions" name="version-comparison" />
    <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#compare-versions">#</a> Comparison between versions</h3>
    <p class="stat-note">
      How the runs in each version’s summary compare, with the month each version was released. Curves show
      density: the higher the curve, the more of a version’s runs have that value. The area under each curve is 1,
      so versions with different numbers of runs can be compared, and the curves are lightly smoothed. Counts are the runs that are not on the blacklist and have metadata, which is close to the website’s own
      count for that version but not always identical.
    </p>
    <div class="version-table-wrap">
      <table class="version-table">
        <thead>
          <tr>
            <th scope="col">Version</th>
            <th scope="col">Released</th>
            <th scope="col">GTDB</th>
            <th scope="col">Runs</th>
            <th scope="col">Host-associated</th>
            <th scope="col">Ecological</th>
            <th scope="col">Unclassified</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="version in versions" :key="version.label">
            <th scope="row"><span class="version-swatch" :class="'version-' + (version.index + 1)" aria-hidden="true"></span>{{ version.label }}</th>
            <td :class="{ 'is-unstated': !version.released }">{{ version.released || '-' }}</td>
            <td>{{ version.gtdb }}</td>
            <td>{{ fmt(version.runs) }}</td>
            <td>{{ fmt(version.host_associated) }}</td>
            <td>{{ fmt(version.ecological) }}</td>
            <td>{{ fmt(version.unclassified) }}</td>
          </tr>
        </tbody>
    </table>
    </div>
    <p v-if="hasUndated" class="stat-note version-footnote"><strong>-</strong> Indicates the release date is not known</p>
    <p class="stat-note version-footnote"><em>Versions before 1.1.9 are not shown.</em></p>

    <div v-for="chart in charts" :key="chart.key" :id="'versions-' + chart.key" class="version-chart">
      <chart-download :target="'#versions-' + chart.key" :name="'versions-' + chart.key" />
      <density-chart :chart="chart" interactive :vertical-lines="chart.key === 'genome_size_mb'" />
    </div>
  </section>
</template>

<script>
import ChartDownload from '@/components/statistics/ChartDownload.vue'
import DensityChart from '@/components/statistics/DensityChart.vue'
import { buildDensityChart } from '@/components/statistics/density'
import { releasedLabel } from '@/components/statistics/releases'
import SUMMARIES from '@/constants/versionSummaries.json'

const STAR_NOTE = 'Introduction of k-mer profiling (weebill) alongside SingleM’s marker genes (Sandpiper v2.2.*), assigning more of each community to known species.'

const MEASURES = [
  {
    key: 'known_species_fraction',
    title: 'Known species fraction',
    note: 'The share of a run’s community that belongs to species already named in the version’s GTDB release. Releases differ between versions, so a shift can come from the database as well as the data.',
    x_title: 'Known species fraction (%)',
    unit: '%',
    point_label: value => `${value}%`,
    x_step: 1,
    x_ticks: () => [0, 25, 50, 75, 100].map(value => ({ value, label: String(value) })),
    // A star where the k-mer profiling (weebill) first shows, with its explanation below the chart.
    marks: [{ x: 97, density: 0.09, symbol: '★', text: STAR_NOTE }],
    footnote: `★ ${STAR_NOTE}`
  },
  {
    key: 'genome_size_mb',
    title: 'Average genome size',
    note: 'Each run has one value: the average genome size of the bacteria and archaea in it. The curves show how each version’s runs are spread across those values. Runs with an average above 8 Mb are counted in the last bin.',
    x_title: 'Average genome size of a run (Mb)',
    unit: ' Mb',
    point_label: value => `${value} Mb`,
    x_step: 0.25,
    x_ticks: () => [0, 2, 4, 6, 8].map(value => ({ value, label: String(value) }))
  }
]

export default {
  name: 'VersionComparison',
  components: { DensityChart, ChartDownload },
  data () {
    // Newest version first, each with the month it was released (null when the changelog has no date for it).
    const versions = SUMMARIES.versions.map((version, index) => ({ ...version, index, released: releasedLabel(version.label) }))
    return { versions }
  },
  computed: {
    hasUndated () {
      return this.versions.some(version => !version.released)
    },
    charts () {
      return MEASURES.map(measure => this.build_chart(measure))
    }
  },
  methods: {
    fmt (value) {
      return value.toLocaleString('en-US')
    },
    build_chart (measure) {
      const drawn = this.versions.filter(version => version[measure.key])
      return buildDensityChart({
        key: measure.key,
        title: measure.title,
        note: measure.note,
        x_title: measure.x_title,
        unit: measure.unit,
        point_label: measure.point_label,
        x_step: measure.x_step,
        x_ticks: measure.x_ticks(),
        marks: measure.marks || [],
        footnote: measure.footnote || '',
        series: drawn.map(version => ({ colour: `var(--color-version-${version.index + 1})`, label: version.label, histogram: version[measure.key] })),
        missing: this.versions.filter(version => !version[measure.key]).map(version => `${version.label} has no data for this measure in its summary.`)
      })
    }
  }
}
</script>

<style scoped>
.stat-note { font-size: 0.9rem; line-height: 1.5; color: var(--color-ink-muted); }
.stat-note + .stat-note { margin-top: var(--space-2); }
.section.container { padding-top: var(--space-8); padding-bottom: var(--space-4); }
.version-swatch { display: inline-block; width: 0.8rem; height: 0.8rem; margin-right: var(--space-2); border-radius: var(--radius-bar); }
.version-footnote { margin-top: var(--space-2); }
.version-chart { display: flow-root; }
.version-table-wrap { max-width: 100%; margin-top: var(--space-6); overflow-x: auto; }
.version-table { width: 100%; min-width: 38rem; border-collapse: collapse; font-variant-numeric: tabular-nums; }
.version-table th, .version-table td { padding: var(--space-2) var(--space-3); text-align: right; white-space: nowrap; border-bottom: 1px solid var(--color-rule); }
.version-table thead th { font-weight: 600; color: var(--color-ink); }
.version-table th:first-child { text-align: left; }
.version-table tbody th { font-weight: 400; }
.version-table td.is-unstated { color: var(--color-ink-muted); }
.version-1 { background: var(--color-version-1); }
.version-2 { background: var(--color-version-2); }
.version-3 { background: var(--color-version-3); }
.version-4 { background: var(--color-version-4); }
.section-anchor:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
</style>
