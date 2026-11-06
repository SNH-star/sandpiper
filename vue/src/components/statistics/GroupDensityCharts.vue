<template>
  <div :id="figure.id" class="group-figure">
    <h4 class="stat-panel-title"><a class="section-anchor" :href="'#' + figure.id">#</a> {{ figure.title }}</h4>
    <p class="stat-note">
      {{ figure.note }} Each group is the runs whose organism is “&lt;name&gt; metagenome”{{ figure.gutNote }}. This uses the
      newest version ({{ version.label }}, GTDB {{ version.gtdb }}). Curves show density, so the area under each is 1.
    </p>
    <density-chart :chart="chart" interactive />
  </div>
</template>

<script>
import DensityChart from '@/components/statistics/DensityChart.vue'
import { buildDensityChart } from '@/components/statistics/density'
import SUMMARIES from '@/constants/versionSummaries.json'

// What each measure plots; `prefix` picks its histograms out of the version summary.
const MEASURES = {
  known: {
    prefix: '',
    idSuffix: '',
    title: 'Known species fraction',
    note: 'The share of a run’s community that belongs to species already named in GTDB.',
    x_title: 'Known species fraction (%)',
    describe: 'Known species fraction'
  },
  spf: {
    prefix: 'spf_',
    idSuffix: '-spf',
    title: 'Prokaryotic fraction',
    note: 'The share of a run’s reads that SingleM estimates are bacterial or archaeal (SPF).',
    x_title: 'Prokaryotic fraction (%)',
    describe: 'Prokaryotic fraction (SPF)'
  }
}

const FIGURES = {
  host: {
    id: 'host-groups',
    title: 'Eukaryotic host-associated samples',
    note: 'Known species fraction in host-associated runs, by host.',
    key: 'host_groups',
    gutNote: ' (for bovine, human, mouse and pig also “<name> gut metagenome”)',
    groups: [
      { name: 'plant', label: 'Plant', colour: 'var(--color-pastel-purple)' },
      { name: 'bovine', label: 'Bovine', colour: 'var(--color-pastel-orange)' },
      { name: 'pig', label: 'Pig', colour: 'var(--color-pastel-red)' },
      { name: 'human', label: 'Human', colour: 'var(--color-pastel-blue)' },
      { name: 'mouse', label: 'Mouse', colour: 'var(--color-pastel-green)' }
    ]
  },
  ecological: {
    id: 'ecological-groups',
    title: 'Ecological samples',
    note: 'Known species fraction in ecological runs, by environment.',
    key: 'ecological_groups',
    gutNote: '',
    groups: [
      { name: 'soil', label: 'Soil', colour: 'var(--color-pastel-green)' },
      { name: 'sediment', label: 'Sediment', colour: 'var(--color-pastel-red)' },
      { name: 'marine', label: 'Marine', colour: 'var(--color-pastel-blue)' },
      { name: 'freshwater', label: 'Freshwater', colour: 'var(--color-pastel-orange)' },
      { name: 'aquatic', label: 'Aquatic', colour: 'var(--color-pastel-purple)' }
    ]
  }
}

export default {
  name: 'GroupDensityCharts',
  components: { DensityChart },
  props: {
    kind: { type: String, required: true, validator: value => value in FIGURES },
    measure: { type: String, default: 'known', validator: value => value in MEASURES }
  },
  computed: {
    spec () {
      return MEASURES[this.measure]
    },
    figure () {
      const base = FIGURES[this.kind]
      return {
        ...base,
        id: base.id + this.spec.idSuffix,
        key: this.spec.prefix + base.key,
        note: base.note.replace('Known species fraction', this.spec.describe)
      }
    },
    version () {
      return SUMMARIES.versions[0]
    },
    chart () {
      const histograms = this.version[this.figure.key] || {}
      // Legend order: the group with the most runs first, then downwards.
      const present = this.figure.groups.filter(group => histograms[group.name])
        .sort((a, b) => histograms[b.name].runs - histograms[a.name].runs)
      return buildDensityChart({
        key: this.figure.key,
        title: this.spec.title,
        note: this.spec.note,
        x_title: this.spec.x_title,
        unit: '%',
        point_label: value => `${value}%`,
        x_step: 1,
        x_ticks: [0, 25, 50, 75, 100].map(value => ({ value, label: String(value) })),
        series: present.map(group => ({
          colour: group.colour,
          label: `${group.label} (${histograms[group.name].runs.toLocaleString('en-US')} runs)`,
          histogram: histograms[group.name]
        })),
        missing: this.figure.groups.filter(group => !histograms[group.name]).map(group => `${group.label} has no runs in this version.`)
      })
    }
  }
}
</script>

<style scoped>
.stat-note { max-width: 62ch; font-size: 0.9rem; line-height: 1.5; color: var(--color-ink-muted); }
.group-figure { min-width: 0; }
.section-anchor:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
</style>
