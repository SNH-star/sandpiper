<template>
  <div :id="figure.id" class="phylum-figure">
    <h4 class="stat-panel-title"><a class="section-anchor" :href="'#' + figure.id">#</a> {{ figure.title }}</h4>
    <ul class="phylum-rows">
      <li v-for="row in rows" :key="row.name" class="phylum-row">
        <span class="phylum-name">{{ row.label }}<span class="phylum-runs">{{ row.runs.toLocaleString('en-US') }} runs</span></span>
        <span class="phylum-bar" role="img" :aria-label="row.aria">
          <span v-for="segment in row.segments" :key="segment.phylum" class="phylum-segment" :class="{ 'is-dim': dimmed(segment.phylum) }"
                :style="{ width: segment.percent + '%', background: dimmed(segment.phylum) ? DIM_COLOUR : segment.colour }" :title="segment.title">
            <span v-if="segment.percent >= 9" class="phylum-percent">{{ Math.round(segment.percent) }}</span>
          </span>
        </span>
      </li>
    </ul>
    <div class="phylum-axis" aria-hidden="true"><span v-for="tick in TICKS" :key="tick" :style="{ left: tick + '%' }">{{ tick }}</span></div>
    <p class="stat-note phylum-axis-title">Relative abundance (%)</p>
    <div class="stat-note phylum-key" :style="{ '--key-rows': keyRows(2), '--key-rows-narrow': keyRows(2) }" role="group" aria-label="Highlight phyla. Click to select several; double-click to clear.">
      <button v-for="item in key" :key="item.phylum" type="button" class="phylum-key-item" :class="{ 'is-dim': dimmed(item.phylum) }"
              :aria-pressed="String(selected.includes(item.phylum))"
              @click="selected = toggleKey(selected, item.phylum)" @dblclick.prevent="selected = []">
        <span class="phylum-swatch" :style="{ background: dimmed(item.phylum) ? DIM_COLOUR : item.colour }" aria-hidden="true"></span>{{ item.label }}
      </button>
      <button type="button" class="phylum-reset" @click="selected = defaultSelected">Reset</button>
    </div>
  </div>
</template>

<script>
import SUMMARIES from '@/constants/groupSummaries.json'
import { toggleKey, isDimmed } from '@/components/statistics/density'

const FIGURES = {
  host_associated: {
    id: 'host-phyla',
    title: 'Phyla in host-associated samples',
    order: ['human', 'mouse', 'pig', 'bovine', 'plant']
  },
  ecological: {
    id: 'ecological-phyla',
    title: 'Phyla in ecological samples',
    order: ['marine', 'soil', 'sediment', 'freshwater', 'aquatic']
  }
}
// Phyla with their own colour token in app.scss; others take a spare in turn.
const NAMED = [
  'Bacteroidota', 'Bacillota_A', 'Bacillota', 'Pseudomonadota', 'Cyanobacteriota', 'Acidobacteriota',
  'Chloroflexota', 'Verrucomicrobiota', 'Actinomycetota', 'Patescibacteriota'
]
const SPARES = 4
const OTHER = 'Other'
const DIM_COLOUR = 'var(--color-rule)'

export default {
  name: 'PhylumCompositionCharts',
  props: { kind: { type: String, required: true, validator: value => value in FIGURES } },
  data () {
    return { TICKS: [0, 25, 50, 75, 100], DIM_COLOUR, selected: [] }
  },
  created () {
    this.selected = this.defaultSelected
  },
  methods: {
    // Rows needed to lay the key (and its Reset button) out in this many columns, filling down.
    keyRows (columns) { return Math.ceil((this.key.length + 1) / columns) },
    toggleKey,
    dimmed (phylum) { return isDimmed(this.selected, phylum) }
  },
  computed: {
    // The most prominent phylum (highest mean abundance across the groups) is highlighted to begin with.
    defaultSelected () {
      const mean = phylum => this.data.groups.reduce((sum, group) => sum + group.percent[phylum] * group.runs, 0)
      const ranked = this.data.phyla.filter(phylum => phylum !== OTHER).sort((a, b) => mean(b) - mean(a))
      return ranked.length ? [ranked[0]] : []
    },
    figure () {
      return FIGURES[this.kind]
    },
    data () {
      return SUMMARIES.composition[this.kind]
    },
    colours () {
      let spare = 0
      return Object.fromEntries(this.data.phyla.map(phylum => {
        if (phylum === OTHER) return [phylum, 'var(--color-phylum-other)']
        if (NAMED.includes(phylum)) return [phylum, `var(--color-phylum-${phylum.toLowerCase().replace(/_/g, '-')})`]
        spare += 1
        return [phylum, `var(--color-phylum-extra-${((spare - 1) % SPARES) + 1})`]
      }))
    },
    // The figure's groups, most runs first; ties keep the figure's own order.
    groupOrder () {
      const byName = Object.fromEntries(this.data.groups.map(group => [group.name, group]))
      return this.figure.order
        .filter(name => byName[name])
        .sort((a, b) => byName[b].runs - byName[a].runs || this.figure.order.indexOf(a) - this.figure.order.indexOf(b))
    },
    rows () {
      const byName = Object.fromEntries(this.data.groups.map(group => [group.name, group]))
      return this.groupOrder.map(name => {
        const group = byName[name]
        const segments = this.data.phyla.map(phylum => ({
          phylum,
          percent: group.percent[phylum],
          colour: this.colours[phylum],
          title: `${phylum}: ${group.percent[phylum]}%`
        })).filter(segment => segment.percent > 0)
        const top = segments.slice(0, 3).map(segment => `${segment.phylum} ${Math.round(segment.percent)}%`)
        return {
          name,
          label: name.charAt(0).toUpperCase() + name.slice(1),
          runs: group.runs,
          segments,
          aria: `${name}: ${top.join(', ')}.`
        }
      })
    },
    key () {
      return this.data.phyla.map(phylum => ({ phylum, label: phylum, colour: this.colours[phylum] }))
    }
  }
}
</script>

<style scoped>
.stat-note { font-size: 0.9rem; line-height: 1.5; color: var(--color-ink-muted); }
.phylum-figure { --phylum-outline: color-mix(in srgb, var(--color-ink) 70%, transparent); min-width: 0; }
.phylum-rows { margin: var(--space-6) 0 0; padding: 0; list-style: none; }
.phylum-row { display: grid; grid-template-columns: 7rem minmax(0, 1fr); align-items: center; gap: var(--space-3); padding: var(--space-1) 0; }
.phylum-name { display: flex; flex-direction: column; font-weight: 600; color: var(--color-ink); }
.phylum-runs { font-size: 0.75rem; font-weight: 400; color: var(--color-ink-muted); }
.phylum-bar { display: flex; height: 1.9rem; overflow: hidden; background: var(--color-track); border-radius: var(--radius-bar); }
.phylum-segment {
  display: flex; align-items: center; justify-content: center; min-width: 0; height: 100%;
  /* An inset outline on every phylum: it takes no layout width (so segment sizes stay exact,
     even for slivers) and keeps neighbouring phyla apart where their colours are close. */
  box-shadow: inset 0 0 0 1px var(--phylum-outline);
}
.phylum-segment:hover { outline: 2px solid var(--color-ink); outline-offset: -2px; }
.phylum-percent { font-size: 0.75rem; font-variant-numeric: tabular-nums; color: var(--color-ink); white-space: nowrap; }
.phylum-axis { position: relative; height: 1.2rem; margin: var(--space-1) 0 0 calc(7rem + var(--space-3)); font-size: 0.8rem; color: var(--color-ink-muted); }
.phylum-axis span { position: absolute; transform: translateX(-50%); white-space: nowrap; }
.phylum-axis-title { margin-left: calc(7rem + var(--space-3)); }
/* Two columns read down like a newspaper and share the width of their half, so even the longest name (bold when picked) stays on one line inside it. */
.phylum-key { display: grid; grid-auto-flow: column; grid-template-rows: repeat(var(--key-rows, 4), auto); grid-auto-columns: minmax(0, 1fr); gap: var(--space-1) var(--space-6); margin-top: var(--space-3); }
.phylum-key-item, .phylum-reset { text-align: left; }
@media (max-width: 640px) { .phylum-key { grid-template-rows: repeat(var(--key-rows-narrow, 6), auto); gap: var(--space-1) var(--space-4); } }
.phylum-key-item, .phylum-reset { font: inherit; color: var(--color-ink); background: none; border: 1px solid transparent; border-radius: var(--radius-bar); padding: 0 var(--space-2); cursor: pointer; touch-action: manipulation; user-select: none; }
.phylum-key-item[aria-pressed="true"] { border-color: var(--color-ink-muted); font-weight: 600; }
.phylum-key-item.is-dim { color: var(--color-ink-muted); }
.phylum-key-item:hover, .phylum-reset:hover { border-color: var(--color-rule); }
.phylum-key-item:focus-visible, .phylum-reset:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.phylum-reset { color: var(--color-ink-muted); text-decoration: underline; }
.phylum-segment.is-dim .phylum-percent { color: var(--color-ink-muted); }
.phylum-swatch { box-shadow: inset 0 0 0 1px var(--phylum-outline); }
.section-anchor:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
</style>
