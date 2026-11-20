<template>
  <div ref="root" class="chart-download" @keydown.esc="closeMenu">
    <div class="download-split">
      <button type="button" class="download-main" :disabled="busy" @click="download">
        {{ busy ? 'Preparing...' : `Download ${label(format)}` }}
      </button>
      <button
        type="button"
        class="download-arrow"
        aria-haspopup="menu"
        :aria-expanded="String(open)"
        aria-label="Choose the download format"
        :disabled="busy"
        @click="open = !open"
        @keydown.down.prevent="openMenu">
        <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M4 6.5l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </button>
    </div>
    <ul v-if="open" class="download-menu" role="menu" @keydown.down.prevent="move(1)" @keydown.up.prevent="move(-1)">
      <li v-for="(item, key) in choices" :key="key" role="none">
        <button type="button" class="download-choice" role="menuitemradio" :aria-checked="String(format === key)" @click="choose(key)">
          <span class="download-check" aria-hidden="true">{{ format === key ? '✓' : '' }}</span>
          <span class="download-choice-text">
            <strong>Download {{ label(key) }}</strong>
            <span>{{ item }}</span>
          </span>
        </button>
      </li>
    </ul>
    <p v-if="error" class="download-error" role="alert">{{ error }}</p>
  </div>
</template>

<script>
import { exportFigure, FORMATS } from '@/components/statistics/chartExport'
import { downloadCsv } from '@/components/statistics/tableExport'

const CHOICES = {
  svg: 'One scalable file, for documents and slides',
  png: 'A picture, for anywhere that takes images'
}
// Offered only by a figure that has a table.
const TABLE_CHOICE = { csv: 'The figure’s numbers as a table, for spreadsheets and your own analysis' }
const CSV_LABEL = 'CSV'

// A GitHub style split button: the left part downloads the figure it belongs to in the chosen format
// (SVG to begin with), the arrow chooses the format. The file is the figure as it is on screen.
export default {
  name: 'ChartDownload',
  props: {
    // Selector of the figure to save, e.g. '#release-year'.
    target: { type: String, required: true },
    // Used in the file name.
    name: { type: String, required: true },
    // Gives the figure's data as { columns, rows } as it is on screen now. A figure with one can also be saved as a CSV.
    table: { type: Function, default: null }
  },
  data () {
    return { format: 'svg', open: false, busy: false, error: '' }
  },
  computed: {
    choices () {
      return this.table ? { ...CHOICES, ...TABLE_CHOICE } : CHOICES
    }
  },
  mounted () {
    document.addEventListener('pointerdown', this.closeOnOutside)
  },
  beforeUnmount () {
    document.removeEventListener('pointerdown', this.closeOnOutside)
  },
  methods: {
    closeOnOutside (event) {
      if (this.open && !this.$refs.root.contains(event.target)) this.open = false
    },
    closeMenu () {
      this.open = false
      this.$refs.root.querySelector('.download-arrow').focus()
    },
    openMenu () {
      this.open = true
      this.$nextTick(() => this.$refs.root.querySelector('.download-choice').focus())
    },
    // Moves focus to the next or previous choice, wrapping round.
    move (step) {
      const choices = [...this.$refs.root.querySelectorAll('.download-choice')]
      const next = (choices.indexOf(document.activeElement) + step + choices.length) % choices.length
      choices[next].focus()
    },
    choose (key) {
      this.format = key
      this.open = false
      this.$refs.root.querySelector('.download-main').focus()
    },
    label (key) {
      return key === 'csv' ? CSV_LABEL : FORMATS[key].label
    },
    downloadTable () {
      try {
        downloadCsv(this.table(), this.name)
      } catch (error) {
        console.error('Table download failed', error)
        this.error = `The ${CSV_LABEL} could not be made. Please try again.`
      }
    },
    async download () {
      this.error = ''
      if (this.format === 'csv') {
        this.downloadTable()
        return
      }
      const figure = document.querySelector(this.target)
      if (!figure) {
        this.error = 'This figure could not be found on the page.'
        return
      }
      this.busy = true
      try {
        await exportFigure(figure, { format: this.format, name: this.name })
      } catch (error) {
        console.error('Figure download failed', error)
        this.error = `The ${this.label(this.format)} could not be made. Please try again.`
      } finally {
        this.busy = false
      }
    }
  }
}
</script>

<style scoped>
.chart-download { position: relative; float: right; margin: var(--space-2) 0 var(--space-2) var(--space-4); z-index: 3; }
/* On a phone the button gets its own row above the heading, so it does not squeeze the heading into broken words. */
@media (max-width: 640px) {
  .chart-download { float: none; display: flex; justify-content: flex-end; margin: 0 0 var(--space-2); }
}
.download-split { display: inline-flex; border-radius: var(--radius-bar); box-shadow: 0 1px 0 var(--black-10); }
.download-main, .download-arrow {
  font: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  line-height: 1.2;
  color: var(--color-white);
  background: var(--color-accent);
  border: 1px solid var(--black-20);
  cursor: pointer;
  touch-action: manipulation;
}
.download-main { padding: 0.35rem 0.8rem; border-radius: var(--radius-bar) 0 0 var(--radius-bar); }
/* The divider between the two parts, as on GitHub's merge button. */
.download-arrow { display: inline-flex; align-items: center; padding: 0 0.4rem; border-left-color: var(--white-40); border-radius: 0 var(--radius-bar) var(--radius-bar) 0; }
.download-main:hover:not(:disabled), .download-arrow:hover:not(:disabled), .download-arrow[aria-expanded="true"] { filter: brightness(0.92); }
.download-main:focus-visible, .download-arrow:focus-visible { outline: 2px solid var(--color-ink); outline-offset: 2px; }
.download-main:disabled, .download-arrow:disabled { opacity: 0.7; cursor: progress; }
.download-menu {
  position: absolute;
  top: calc(100% + var(--space-1));
  right: 0;
  width: 17rem;
  margin: 0;
  padding: var(--space-1) 0;
  list-style: none;
  background: var(--color-surface);
  border: 1px solid var(--color-rule);
  border-radius: var(--radius-bar);
  box-shadow: 0 8px 24px var(--black-18);
}
.download-choice { display: flex; align-items: flex-start; gap: var(--space-2); width: 100%; padding: var(--space-2) var(--space-3); font: inherit; text-align: left; color: var(--color-ink); background: none; border: 0; cursor: pointer; }
.download-choice:hover, .download-choice:focus-visible { background: var(--color-track); outline: none; }
.download-check { width: 1rem; flex: none; font-weight: 700; }
.download-choice-text { display: flex; flex-direction: column; font-size: 0.8rem; line-height: 1.35; color: var(--color-ink-muted); }
.download-choice-text strong { font-size: 0.85rem; color: var(--color-ink); }
.download-error { position: absolute; top: calc(100% + var(--space-1)); right: 0; width: 14rem; margin: 0; font-size: 0.8rem; color: var(--color-ink); }
</style>
