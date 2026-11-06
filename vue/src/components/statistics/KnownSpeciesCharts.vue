<template>
  <section id="known-species" class="section container stat-figure">
    <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#known-species">#</a> Known species fraction</h3>
    <p v-for="note in notes" :key="note" class="stat-note">{{ note }}</p>
    <density-chart :chart="chart" interactive />
  </section>
</template>

<script>
import DensityChart from '@/components/statistics/DensityChart.vue'
import { buildDensityChart } from '@/components/statistics/density'

const SERIES = [
  { key: 'host_associated', label: 'Host-associated', colour: 'var(--color-sample-host)' },
  { key: 'ecological', label: 'Ecological', colour: 'var(--color-sample-ecological)' }
]
const PERCENT_TICKS = [0, 25, 50, 75, 100]

export default {
  name: 'KnownSpeciesCharts',
  components: { DensityChart },
  props: {
    data: { type: Object, required: true },
    gtdbVersion: { type: String, required: true },
    version: { type: String, required: true }
  },
  computed: {
    notes () {
      return [
        `Known species fraction is the share of a run’s community that is assigned to the species level, plotted here using the GTDB ${this.gtdbVersion} profiles. A high value means most of the community is known; a low value means much of it is not yet named.`,
        `This chart only uses metagenomes in the current release (Sandpiper ${this.version}) that have a host-associated or ecological call.`,
        'Density shows where a group’s runs are concentrated: the higher the line, the more of the group’s runs have that known species fraction. The area under each line is 1, so the two groups can be compared.'
      ]
    },
    chart () {
      const { distribution } = this
      return buildDensityChart({
        key: 'known_species',
        title: 'Share of runs at each known species fraction',
        note: '',
        x_title: 'Known species fraction (%)',
        unit: '%',
        point_label: value => `${value}%`,
        x_step: 1,
        x_ticks: PERCENT_TICKS.map(value => ({ value, label: String(value) })),
        series: SERIES.map(item => ({
          colour: item.colour,
          label: item.label,
          histogram: this.histogram(distribution[item.key], distribution.bin_width)
        }))
      })
    },
    distribution () {
      return this.data.distribution
    }
  },
  methods: {
    // The bands as the parallel start / percent lists the density chart takes.
    histogram (bands, width) {
      const percent = bands.map(band => band.percent)
      return { start: bands.map(band => band.start), percent, median: this.median(percent, bands[0].start, width) }
    },
    // The 50% point, straight across the band that holds it.
    median (percent, first, width) {
      let cumulative = 0
      for (let n = 0; n < percent.length; n++) {
        if (percent[n] > 0 && cumulative + percent[n] >= 50) {
          return +(first + width * (n + (50 - cumulative) / percent[n])).toFixed(1)
        }
        cumulative += percent[n]
      }
      return null
    }
  }
}
</script>

<style scoped>
.stat-note {
  max-width: 62ch;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--color-ink-muted);
}
.stat-note + .stat-note {
  margin-top: var(--space-2);
}
.section-anchor:active {
  color: var(--color-accent-strong);
}
.section-anchor:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
.section.container {
  padding-top: var(--space-8);
  padding-bottom: var(--space-4);
}
</style>
