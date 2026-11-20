<template>
  <div :id="figure.id" class="group-figure">
    <h4 class="stat-panel-title"><a class="section-anchor" :href="'#' + figure.id">#</a> {{ figure.title }}</h4>
    <p v-if="!bare" class="stat-note">
      {{ figure.note }} Each group is the runs whose organism is “&lt;name&gt; metagenome”{{ figure.gutNote }}. This uses the
      newest version ({{ version.label }}, GTDB {{ version.gtdb }}). Curves show density, so the area under each is 1.
    </p>
    <density-chart :chart="chart" interactive :bare="bare" :vertical-lines="measure === 'genome'" />
  </div>
</template>

<script>
import DensityChart from '@/components/statistics/DensityChart.vue'
import { buildDensityChart } from '@/components/statistics/density'
import SUMMARIES from '@/constants/versionSummaries.json'
import { MEASURES, FIGURES } from '@/components/statistics/groupDensitySpec'

export default {
  name: 'GroupDensityCharts',
  components: { DensityChart },
  props: {
    // Leaves out the explanation, for a page that gives it once above both charts.
    bare: { type: Boolean, default: false },
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
        unit: this.spec.unit,
        point_label: value => `${value}${this.spec.unit}`,
        x_step: this.spec.x_step,
        x_ticks: this.spec.x_ticks.map(value => ({ value, label: String(value) })),
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
.stat-note { font-size: 0.9rem; line-height: 1.5; color: var(--color-ink-muted); }
.group-figure { min-width: 0; }
.section-anchor:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
</style>
