<template>
  <div class="density-chart">
    <h3 class="subtitle is-5">{{ chart.title }}</h3>
    <p class="stat-note">{{ chart.note }}</p>
    <div class="line-chart">
      <p class="line-y-title">Density</p>
      <div class="line-plot" role="img" :aria-label="chart.aria"
           @pointermove="move" @pointerdown="move" @pointerleave="hovered = null">
        <div v-for="tick in chart.y_ticks" :key="tick.percent" class="line-gridline" :style="{ bottom: tick.percent + '%' }">
          <span class="line-tick-label">{{ tick.label }}</span>
        </div>
        <span v-for="tick in verticalTicks" :key="'v' + tick.label" class="line-vline" :style="{ left: tick.percent + '%' }"></span>
        <svg class="line-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <template v-for="line in drawn" :key="line.label">
            <path :d="line.area" :style="{ fill: shade(line) }" class="line-area" :class="{ 'is-dim': dimmed(line) }" />
            <path :d="line.curve" :style="{ stroke: shade(line) }" class="line-stroke" :class="{ 'is-dim': dimmed(line) }" fill="none" vector-effect="non-scaling-stroke" />
          </template>
          <!-- Wide invisible strokes on top: hovering a line (not the shaded area) picks it out. -->
          <path v-for="line in chart.lines" :key="'hit-' + line.label" :d="line.curve" class="line-hit" fill="none"
                vector-effect="non-scaling-stroke" @pointerenter="hoveredLine = line.label" @pointerleave="hoveredLine = null" />
        </svg>
        <span v-for="mark in chart.marks" :key="mark.symbol + mark.left" class="chart-mark" :tabindex="mark.text ? 0 : null"
              :class="{ 'is-left': mark.left > 55 }" :style="{ left: mark.left + '%', bottom: mark.bottom + '%' }"
              @pointermove.stop @pointerdown.stop @pointerenter="hovered = null">{{ mark.symbol }}<span v-if="mark.text" class="chart-mark-tip" role="tooltip">{{ mark.text }}</span></span>
        <template v-if="hovered !== null">
          <span class="hover-guide" :style="{ left: hovered.centre + '%' }"></span>
          <span v-for="(line, n) in chart.lines" :key="line.label" class="hover-dot"
                :style="{ left: hovered.centre + '%', bottom: hovered.values[n].height + '%', background: shade(line) }"></span>
          <div class="hover-tip" :class="{ 'is-left': hovered.centre > 55 }" :style="{ left: hovered.centre + '%' }" aria-hidden="true">
            <p class="hover-range">{{ hovered.label }}</p>
            <p v-for="(line, n) in chart.lines" :key="line.label" class="hover-row" :class="{ 'is-dim': dimmed(line) }">
              <span class="density-swatch" :style="{ background: shade(line) }"></span>
              <span class="hover-name">{{ line.label }}</span>
              <span class="hover-figures hover-density">Density {{ hovered.values[n].density }}</span>
            </p>
          </div>
        </template>
      </div>
      <div class="line-axis" aria-hidden="true">
        <span v-for="tick in chart.x_ticks" :key="tick.label" class="line-x-label" :style="{ left: tick.percent + '%' }">{{ tick.label }}</span>
      </div>
      <p class="line-x-title">{{ chart.x_title }}</p>
    </div>
    <p v-if="chart.footnote" class="stat-note chart-footnote">{{ chart.footnote }}</p>
    <p v-if="!interactive" class="stat-note density-legend">
      <span v-for="line in chart.lines" :key="line.label">
        <span class="density-swatch" :style="{ background: line.colour }" aria-hidden="true"></span>{{ line.label }}, median {{ line.median }}{{ chart.unit }}
      </span>
    </p>
    <div v-else class="stat-note density-legend is-stacked" role="group" aria-label="Highlight lines. Click to select several; double-click to clear.">
      <button v-for="line in chart.lines" :key="line.label" type="button" class="density-legend-item"
              :class="{ 'is-dim': dimmed(line) }" :aria-pressed="String(selected.includes(line.label))"
              @click="selected = toggleKey(selected, line.label)" @dblclick.prevent="selected = []">
        <span class="density-swatch" :style="{ background: shade(line) }" aria-hidden="true"></span>{{ line.label }}, median {{ line.median }}{{ chart.unit }}
      </button>
      <button type="button" class="density-reset" @click="selected = [...defaultSelected]">Reset</button>
    </div>
    <p v-for="label in chart.missing" :key="label" class="stat-note">{{ label }}</p>
  </div>
</template>

<script>
import { toggleKey, isDimmed } from '@/components/statistics/density'

const DIM_COLOUR = 'var(--color-rule)'

export default {
  name: 'DensityChart',
  props: {
    chart: { type: Object, required: true },
    // Makes the legend clickable: select lines to highlight them and grey out the rest.
    interactive: { type: Boolean, default: false },
    // Draws a faint vertical line up from each x-axis tick.
    verticalLines: { type: Boolean, default: false },
    // Labels highlighted to begin with and after Reset; none means nothing is greyed out.
    defaultSelected: { type: Array, default: () => [] }
  },
  data () {
    return { hovered: null, hoveredLine: null, selected: [...this.defaultSelected] }
  },
  computed: {
    // Ticks strictly inside the plot; one at either end would only trace the axis.
    verticalTicks () {
      return this.verticalLines ? this.chart.x_ticks.filter(tick => tick.percent > 0 && tick.percent < 100) : []
    },
    // Greyed-out lines first, so the highlighted ones are drawn over them.
    drawn () {
      return [...this.chart.lines].sort((a, b) => Number(this.legendDimmed(b)) - Number(this.legendDimmed(a)))
    }
  },
  methods: {
    toggleKey,
    legendDimmed (line) {
      return this.interactive && isDimmed(this.selected, line.label)
    },
    // Hovering a line picks it out over the legend's selection; otherwise the legend decides.
    dimmed (line) {
      if (this.hoveredLine !== null) return line.label !== this.hoveredLine
      return this.legendDimmed(line)
    },
    shade (line) {
      return this.dimmed(line) ? DIM_COLOUR : line.colour
    },
    // The point under the pointer, from where it is along the plot.
    move (event) {
      const box = event.currentTarget.getBoundingClientRect()
      if (box.width === 0) return
      const along = Math.min(Math.max((event.clientX - box.left) / box.width, 0), 1)
      this.hovered = this.chart.at(along)
    }
  }
}
</script>

<style scoped>
.stat-note { max-width: 62ch; font-size: 0.9rem; line-height: 1.5; color: var(--color-ink-muted); }
.stat-note + .stat-note { margin-top: var(--space-2); }
.density-chart { margin-top: var(--space-8); }
.line-chart { position: relative; margin: var(--space-6) 0 var(--space-2) 4.4rem; --plot-height: 14rem; }
@media (max-width: 640px) {
  .line-chart { margin-left: 3.8rem; margin-right: var(--space-2); --plot-height: 11rem; }
  .line-y-title { left: -3.8rem; font-size: 0.75rem; white-space: nowrap; }
  .line-x-title { font-size: 0.8rem; }
  .line-x-label { font-size: 0.7rem; }
}
.line-y-title { position: absolute; top: 0; left: -4.4rem; display: flex; align-items: center; justify-content: center; width: 1.4rem; height: var(--plot-height); font-size: 0.85rem; writing-mode: vertical-rl; transform: rotate(180deg); color: var(--color-ink-muted); }
.line-plot { position: relative; height: var(--plot-height); border-left: 1px solid var(--color-rule); border-bottom: 1px solid var(--color-rule); }
.line-gridline { position: absolute; left: 0; right: 0; border-top: 1px solid var(--color-track); }
.line-tick-label { position: absolute; right: calc(100% + var(--space-2)); top: 0; transform: translateY(-50%); font-size: 0.8rem; font-variant-numeric: tabular-nums; color: var(--color-ink-muted); white-space: nowrap; }
.chart-mark { position: absolute; z-index: 6; transform: translate(-50%, 50%); font-size: 1.25rem; line-height: 1; color: var(--color-ink); cursor: help; }
.chart-mark:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.chart-mark-tip { display: none; position: absolute; bottom: calc(100% + var(--space-2)); left: 50%; transform: translateX(-50%); width: max-content; max-width: 16rem; padding: var(--space-2) var(--space-3); font-size: 0.8rem; line-height: 1.4; text-align: left; color: var(--color-ink); background: var(--color-surface); border: 1px solid var(--color-rule); border-radius: var(--radius-bar); pointer-events: none; }
.chart-mark.is-left .chart-mark-tip { left: auto; right: 0; transform: none; }
.chart-mark:hover .chart-mark-tip, .chart-mark:focus .chart-mark-tip { display: block; }
.chart-footnote { margin-top: var(--space-2); }
.hover-guide { position: absolute; top: 0; bottom: 0; width: 0; border-left: 1px dashed var(--color-ink-muted); pointer-events: none; }
.hover-dot { position: absolute; width: 0.6rem; height: 0.6rem; margin: 0 0 -0.3rem -0.3rem; border: 2px solid var(--color-surface); border-radius: 50%; pointer-events: none; }
.hover-tip { position: absolute; top: var(--space-2); z-index: 5; margin-left: var(--space-3); min-width: 12rem; max-width: 18rem; padding: var(--space-2) var(--space-3); font-size: 0.8rem; line-height: 1.4; color: var(--color-ink); background: var(--color-surface); border: 1px solid var(--color-rule); border-radius: var(--radius-bar); pointer-events: none; }
.hover-tip.is-left { margin-left: 0; transform: translateX(calc(-100% - var(--space-3))); }
.hover-range { font-weight: 600; }
.hover-row { display: grid; grid-template-columns: auto minmax(0, 1fr); column-gap: var(--space-2); align-items: baseline; margin-top: var(--space-1); }
.hover-name { font-weight: 600; }
.hover-density { color: var(--color-ink); font-weight: 600; }
.hover-figures { grid-column: 2; font-variant-numeric: tabular-nums; color: var(--color-ink-muted); }
.line-plot { touch-action: pan-y; }
.line-vline { position: absolute; top: 0; bottom: 0; width: 0; border-left: 1px solid var(--color-track); pointer-events: none; }
.line-svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.line-stroke { stroke-width: 2; stroke-linejoin: round; }
.line-area { stroke: none; fill-opacity: 0.1; pointer-events: none; }
.line-stroke { pointer-events: none; }
.line-hit { stroke: transparent; stroke-width: 12; pointer-events: stroke; }
.line-axis { position: relative; height: 1.4rem; }
.line-x-label { position: absolute; top: var(--space-1); transform: translateX(-50%); font-size: 0.8rem; color: var(--color-ink-muted); white-space: nowrap; }
.line-x-title { margin-top: var(--space-1); font-size: 0.85rem; text-align: center; color: var(--color-ink-muted); }
.density-legend { display: flex; flex-wrap: wrap; gap: var(--space-1) var(--space-6); }
/* The clickable legend: one item per line, so a long label never splits into a second column. */
.density-legend.is-stacked { flex-direction: column; flex-wrap: nowrap; align-items: flex-start; gap: var(--space-1); }
.density-legend.is-stacked .density-legend-item { text-align: left; }
.line-stroke.is-dim { stroke-width: 1.5; }
.line-area.is-dim { fill-opacity: 0.03; }
.hover-row.is-dim { opacity: 0.5; }
.density-legend-item, .density-reset { font: inherit; color: var(--color-ink); background: none; border: 1px solid transparent; border-radius: var(--radius-bar); padding: 0 var(--space-2); cursor: pointer; touch-action: manipulation; user-select: none; }
.density-legend-item[aria-pressed="true"] { border-color: var(--color-ink-muted); font-weight: 600; }
.density-legend-item.is-dim { color: var(--color-ink-muted); }
.density-legend-item:hover, .density-reset:hover { border-color: var(--color-rule); }
.density-legend-item:focus-visible, .density-reset:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.density-reset { color: var(--color-ink-muted); text-decoration: underline; }
.density-swatch { display: inline-block; width: 0.8rem; height: 0.8rem; margin-right: var(--space-2); border-radius: var(--radius-bar); }
</style>
