<template>
  <div class="indicpiper-group">
    <ul class="ig-rows">
      <li v-for="row in rows" :key="row.habitat" class="ig-row">
        <span class="ig-name ig-has-tip" tabindex="0">{{ row.label }}<span class="ig-runs">{{ row.runs.toLocaleString('en-US') }} runs</span>
          <span class="ig-tip" role="tooltip">{{ row.nameTip }}</span>
        </span>
        <span class="ig-has-tip">
          <span class="ig-track" role="img" tabindex="0" :aria-label="row.aria">
            <span class="ig-bar" :style="{ width: row.widthPercent + '%' }"></span>
          </span>
          <span class="ig-tip" role="tooltip">{{ row.barTip }}</span>
        </span>
        <span class="ig-values ig-has-tip" tabindex="0"><b>{{ row.abundanceLabel }}</b><span class="ig-genera">{{ row.generaLabel }}</span>
          <span class="ig-tip is-end" role="tooltip">{{ row.valuesTip }}</span>
        </span>
      </li>
    </ul>
    <div class="ig-axis" aria-hidden="true"><span v-for="tick in ticks" :key="tick.value" :style="{ left: tick.position + '%' }">{{ tick.value }}</span></div>
    <p class="stat-note ig-axis-title">Average indicator abundance (% of the sample)</p>
    <p v-if="unrecorded.length" class="stat-note">
      {{ unrecordedText }} {{ unrecorded.length === 1 ? 'is one of' : 'are among' }} IndicPiper’s {{ habitatCount }} habitats, but no runs are labelled with
      {{ unrecorded.length === 1 ? 'it' : 'them' }}, so there is no average to show.
    </p>
  </div>
</template>

<script>
import SUMMARIES from '@/constants/groupSummaries.json'

const TICK_COUNT = 4

function sentence (habitat) {
  return habitat.charAt(0).toUpperCase() + habitat.slice(1)
}

// A round number at or above `value`, so the longest bar leaves room for its label.
function niceCeiling (value) {
  if (!(value > 0)) return 1
  const magnitude = 10 ** Math.floor(Math.log10(value))
  return Math.ceil(value / magnitude) * magnitude
}

export default {
  name: 'IndicPiperGroupChart',
  computed: {
    habitats () {
      return SUMMARIES.indicpiper_by_habitat || {}
    },
    withRuns () {
      return Object.entries(this.habitats)
        .filter(([, group]) => group.runs > 0)
        .map(([habitat, group]) => ({ habitat, ...group, percent: group.mean_abundance * 100 }))
        .sort((a, b) => b.percent - a.percent || a.habitat.localeCompare(b.habitat))
    },
    unrecorded () {
      return Object.entries(this.habitats).filter(([, group]) => !group.runs).map(([habitat]) => habitat).sort()
    },
    habitatCount () {
      return Object.keys(this.habitats).length
    },
    unrecordedText () {
      return sentence(this.unrecorded.join(', '))
    },
    axisMax () {
      return niceCeiling(Math.max(0, ...this.withRuns.map(row => row.percent)))
    },
    ticks () {
      return Array.from({ length: TICK_COUNT + 1 }, (_, i) => {
        const value = (this.axisMax * i) / TICK_COUNT
        return { value: Number(value.toPrecision(3)), position: (i / TICK_COUNT) * 100 }
      })
    },
    rows () {
      return this.withRuns.map(row => {
        const abundanceLabel = `${row.percent.toFixed(2)}%`
        const generaLabel = `${row.mean_genera.toFixed(1)} genera`
        const matched = Math.round((row.matched_runs / row.runs) * 100)
        return {
          habitat: row.habitat,
          label: sentence(row.habitat),
          runs: row.runs,
          widthPercent: (row.percent / this.axisMax) * 100,
          abundanceLabel,
          generaLabel,
          nameTip: `${row.runs.toLocaleString('en-US')} runs are recorded as ${row.habitat}. ${matched}% of them have at least one ${row.habitat} indicator genus.`,
          barTip: `Average indicator abundance: the summed abundance of ${row.habitat} indicator genera as a percentage of the sample, averaged over all ${row.runs.toLocaleString('en-US')} runs.`,
          valuesTip: `${abundanceLabel} is the average indicator abundance (the bar). ${generaLabel} is the average number of ${row.habitat} indicator genera found per run.`,
          aria: `${row.habitat}: average indicator abundance ${abundanceLabel} and ${generaLabel} per run, over ${row.runs} runs.`
        }
      })
    }
  }
}
</script>

<style scoped>
.stat-note { font-size: 0.9rem; line-height: 1.5; color: var(--color-ink-muted); }
.indicpiper-group { min-width: 0; }
/* The same row grid, bar height and row rhythm as "Most widely detected taxa". */
.ig-rows { margin: var(--space-2) 0 0; padding: 0; list-style: none; }
.ig-row { position: relative; display: grid; grid-template-columns: 13rem minmax(0, 1fr) 10.5rem; align-items: center; gap: var(--space-3); border-bottom: 1px solid var(--color-rule); }
.ig-row:last-child { border-bottom: 0; }
.ig-name { display: flex; flex-direction: column; justify-content: center; min-height: 44px; font-weight: 600; color: var(--color-ink); }
.ig-runs { font-size: 0.75rem; font-weight: 400; color: var(--color-ink-muted); }
.ig-track { display: block; height: 0.75rem; overflow: hidden; border-radius: var(--radius-bar); }
.ig-bar { display: block; height: 100%; min-width: 1px; background: var(--color-accent); }
.ig-values { display: flex; flex-direction: column; align-items: flex-end; font-variant-numeric: tabular-nums; line-height: 1.25; color: var(--color-ink); }
.ig-genera { font-size: 0.75rem; color: var(--color-ink-muted); }
/* Each of the three parts of a row explains itself on hover or keyboard focus. */
.ig-has-tip { position: relative; }
.ig-tip { display: none; position: absolute; z-index: 5; left: 0; bottom: calc(100% - var(--space-1)); width: max-content; max-width: 18rem; padding: var(--space-2) var(--space-3); font-size: 0.8rem; font-weight: 400; line-height: 1.4; color: var(--color-ink); background: var(--color-surface); border: 1px solid var(--color-rule); border-radius: var(--radius-bar); pointer-events: none; }
.ig-tip.is-end { left: auto; right: 0; }
.ig-track:focus-visible, .ig-name:focus-visible, .ig-values:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.ig-has-tip:hover > .ig-tip, .ig-has-tip:focus-within > .ig-tip { display: block; }
.ig-axis { position: relative; height: 1.2rem; margin: var(--space-1) calc(10.5rem + var(--space-3)) 0 calc(13rem + var(--space-3)); font-size: 0.8rem; color: var(--color-ink-muted); }
.ig-axis span { position: absolute; transform: translateX(-50%); white-space: nowrap; }
.ig-axis-title { max-width: none; margin: 0 calc(10.5rem + var(--space-3)) 0 calc(13rem + var(--space-3)); text-align: center; }
@media (max-width: 640px) {
  .ig-row { grid-template-columns: minmax(0, 1fr); gap: 0; padding-bottom: var(--space-2); }
  .ig-values { align-items: flex-start; margin-top: var(--space-1); }
  .ig-tip, .ig-tip.is-end { left: 0; right: auto; }
  .ig-axis { margin: var(--space-1) 0 0; }
  .ig-axis-title { margin: 0; }
}
</style>
