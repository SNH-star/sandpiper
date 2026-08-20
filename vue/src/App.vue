<template>
  <div id="app">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@mdi/font@5.8.55/css/materialdesignicons.min.css">
    <b-navbar :centered="true" type="is-light">
        <template #start>
            <b-navbar-item tag="router-link" :to="{ path: '/' }">Home</b-navbar-item>
            <b-navbar-item tag="router-link" :to="{ path: '/Search' }">Search</b-navbar-item>

            <b-navbar-item tag="router-link" :to="{ path: '/Run/SRR9841429' }">Example 1</b-navbar-item>
            <b-navbar-item tag="router-link" :to="{ path: '/Run/ERR1914274' }">Example 2</b-navbar-item>

            <b-navbar-item tag="router-link" :to="{ path: '/About' }">About</b-navbar-item>
        </template>
    </b-navbar>

    <template v-if="$route.name === 'Run'">
      <!-- Pull tab — always visible on Run pages -->
      <button type="button" class="sticky-pull-tab" :class="{ 'is-drawer-open': sticky_visible }" :aria-expanded="sticky_visible" aria-controls="run-search-panel" aria-label="Continue searching runs" @click="sticky_visible = !sticky_visible">
        <span class="sticky-pull-label">Continue searching</span>
      </button>

      <!-- Sticky bar -->
      <div id="run-search-panel" class="sticky-search-bar" :class="{ 'is-visible': sticky_visible }" :aria-hidden="!sticky_visible" :inert="!sticky_visible">
        <div class="sticky-inner">
          <div class="sticky-bar-row">
            <b-button v-if="run_history.length > 0" type="is-primary" @click="go_back">← Previous</b-button>
            <img src="./assets/sandpiper_logo.png" class="sticky-logo sticky-logo-left" alt="Sandpiper" />
            <div class="sticky-input-col">
              <b-field class="sticky-field-grow">
                <b-input v-model="sticky_input" aria-label="Filter runs" placeholder="e.g. country: Australia" icon="magnify" expanded @input="on_sticky_input" @keyup.enter="next_from_sticky"></b-input>
                <div class="control">
                  <b-button type="is-primary" :loading="sticky_loading" @click="next_from_sticky">Next</b-button>
                </div>
              </b-field>
              <div class="sticky-sub-row">
                <span class="sticky-keys-left">
                  <button type="button" class="text-toggle sticky-keys-toggle has-text-grey is-size-7" :aria-expanded="sticky_keys_open" aria-controls="run-search-keys" @click="sticky_keys_open = !sticky_keys_open">
                    List of Keys {{ sticky_keys_open ? '▴' : '▾' }}
                  </button>
                  <InfoTooltipButton controls="run-search-popover" label="Show search syntax help" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'keys_info'" @open="showStickyTooltip($event, 'keys_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" />
                </span>
                <span v-if="sticky_count !== null" class="sticky-count-below" aria-live="polite" aria-atomic="true">{{ sticky_count.toLocaleString() }} runs</span>
              </div>
            </div>
            <div class="sticky-logos-right">
              <img src="./assets/cmr.png" class="sticky-logo" alt="CMR" />
              <img src="./assets/QUT_SQUARE_RGB_SVG.svg" class="sticky-logo" alt="QUT" />
            </div>
          </div>
          <div id="run-search-keys" class="sticky-keys-panel" :class="{ 'is-open': sticky_keys_open }">
            <div class="sticky-keys-box">
              <div class="sticky-keys-grid">
                <div class="keys-group">
                  <p class="keys-group-title">Location</p>
                  <div class="keys-item"><code>country</code><span class="keys-example">e.g. Australia</span></div>
                  <div class="keys-item"><code>location</code><span class="keys-example">e.g. Pacific Ocean</span></div>
                  <div class="keys-item"><code>latitude</code><span class="keys-example">e.g. -33.8 or -40-30</span></div>
                  <div class="keys-item"><code>longitude</code><span class="keys-example">e.g. 151.2 or 140-160</span></div>
                </div>
                <div class="keys-group">
                  <p class="keys-group-title">Sample</p>
                  <div class="keys-item"><code>year</code><span class="keys-example">e.g. 2010-2015</span></div>
                  <div class="keys-item"><code>release_year</code><span class="keys-example">e.g. 2015-2020</span></div>
                  <div class="keys-item"><code>temperature</code><span class="keys-example">e.g. 20-30</span></div>
                  <div class="keys-item"><code>depth</code><span class="keys-example">e.g. 0-200</span></div>
                  <div class="keys-item"><code>environment</code><span class="keys-example">host or ecological</span></div>
                  <div class="keys-item"><code>low_complexity</code><span class="keys-example">yes or no</span></div>
                  <div class="keys-item">
                    <code class="keys-item-label">age <InfoTooltipButton controls="run-search-popover" label="Show age search help" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'age_info'" @open="showStickyTooltip($event, 'age_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" /></code>
                    <span class="keys-example">e.g. 25 or 20-30</span>
                  </div>
                  <div class="keys-item">
                    <code class="keys-item-label">habitat <InfoTooltipButton controls="run-search-popover" label="Show IndicPiper habitat values" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'habitat_info'" @open="showStickyTooltip($event, 'habitat_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" /></code>
                    <span class="keys-example">e.g. soil</span>
                  </div>
                </div>
                <div class="keys-group">
                  <p class="keys-group-title">Quality / Size</p>
                  <div class="keys-item"><code>spf</code><span class="keys-example">e.g. 50-100 or >50</span></div>
                  <div class="keys-item"><code>ksf</code><span class="keys-example">e.g. 70-100 or >70</span></div>
                  <div class="keys-item"><code>gbp</code><span class="keys-example">e.g. 2-10 or >2</span></div>
                  <div class="keys-item"><code>reads</code><span class="keys-example">e.g. 10-100 or >10</span></div>
                  <div class="keys-item"><code>read_length</code><span class="keys-example">e.g. 100-250 or >100</span></div>
                </div>
                <div class="keys-group">
                  <p class="keys-group-title">Sequencing</p>
                  <div class="keys-item">
                    <code class="keys-item-label">platform <InfoTooltipButton controls="run-search-popover" label="Show platform search help" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'platform_info'" @open="showStickyTooltip($event, 'platform_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" /></code>
                    <span class="keys-example">e.g. Illumina</span>
                  </div>
                  <div class="keys-item">
                    <code class="keys-item-label">instrument <InfoTooltipButton controls="run-search-popover" label="Show instrument search help" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'instrument_info'" @open="showStickyTooltip($event, 'instrument_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" /></code>
                    <span class="keys-example">e.g. HiSeq 2500</span>
                  </div>
                  <div class="keys-item">
                    <code class="keys-item-label">library_strategy <InfoTooltipButton controls="run-search-popover" label="Show library strategy search help" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'library_info'" @open="showStickyTooltip($event, 'library_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" /></code>
                    <span class="keys-example">e.g. WGS</span>
                  </div>
                  <p class="keys-group-title" style="margin-top: 0.75rem;">Taxonomy</p>
                  <div class="keys-item"><code>organism</code><span class="keys-example">e.g. marine metagenome</span></div>
                  <div class="keys-item">
                    <code class="keys-item-label">taxonomy <InfoTooltipButton controls="run-search-popover" label="Show taxonomy search help" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'taxonomy_info'" @open="showStickyTooltip($event, 'taxonomy_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" /></code>
                    <span class="keys-example">e.g. s__Prochlorococcus</span>
                  </div>
                </div>
                <div class="keys-group">
                  <p class="keys-group-title">Study</p>
                  <div class="keys-item"><code>study</code><span class="keys-example">e.g. Tara Oceans</span></div>
                  <div class="keys-item"><code>abstract</code><span class="keys-example">e.g. coral reef</span></div>
                  <div class="keys-item"><code>bioproject</code><span class="keys-example">e.g. PRJNA12345</span></div>
                  <p class="keys-group-title" style="margin-top: 0.75rem;">Identifiers</p>
                  <div class="keys-item"><code>sra_study</code><span class="keys-example">e.g. SRP012345</span></div>
                  <div class="keys-item"><code>experiment</code><span class="keys-example">e.g. SRX012345</span></div>
                  <div class="keys-item"><code>sample_acc</code><span class="keys-example">e.g. SRS012345</span></div>
                  <div class="keys-item"><code>biosample</code><span class="keys-example">e.g. SAMN12345</span></div>
                  <div class="keys-item"><code>organisation</code><span class="keys-example">e.g. MIT</span></div>
                  <div class="keys-item">
                    <code class="keys-item-label">metadata <InfoTooltipButton controls="run-search-popover" label="Show BioSample metadata search help" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'metadata_info'" @open="showStickyTooltip($event, 'metadata_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" /></code>
                    <span class="keys-example">e.g. host=Sus scrofa</span>
                  </div>
                  <div class="keys-item">
                    <code class="keys-item-label">metalog <InfoTooltipButton controls="run-search-popover" label="Show Metalog metadata search help" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'metalog_info'" @open="showStickyTooltip($event, 'metalog_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" /></code>
                    <span class="keys-example">e.g. host=Sus scrofa or diabetes</span>
                  </div>
                </div>
              </div>
              <div class="sticky-syntax-row">
                <span class="sticky-syntax-title">Query Syntax</span>
                <div class="sticky-syntax-items">
                  <span class="sticky-syntax-item"><code>2-10</code> range</span>
                  <span class="sticky-syntax-item"><code>&gt;10</code> greater than</span>
                  <span class="sticky-syntax-item"><code>&gt;=10</code> at least</span>
                  <span class="sticky-syntax-item"><code>&lt;10</code> less than</span>
                  <span class="sticky-syntax-item"><code>&lt;=10</code> at most</span>
                  <span class="sticky-syntax-item"><code>10</code> exact / approx</span>
                  <span class="sticky-syntax-item"><code>(empty)</code> present, any value e.g. "age:"</span>
                </div>
              </div>
              <div class="sticky-example-row">
                <span class="sticky-example-label">Example:</span>
                <code class="sticky-example-query">year: 2015-2020, metadata: sex=male</code>
                <b-button size="is-small" type="is-primary" @click="try_sticky_example">Try it</b-button>
              </div>
            </div>
          </div>
        </div>
        <button v-if="sticky_visible" type="button" class="sticky-close-tab" aria-label="Close run search" @click="sticky_visible = false">
          <span class="sticky-close-label">Close</span>
        </button>
      </div>
      <teleport to="body">
        <div v-if="sticky_tooltip_visible" id="run-search-popover" class="sticky-info-tooltip" :style="{ left: sticky_tooltip_x + 'px', top: sticky_tooltip_y + 'px' }" role="dialog" aria-label="Search field help" @mouseenter="keepStickyTooltipOpen" @mouseleave="hideStickyTooltip" @keydown.esc="hideStickyTooltip">
          <template v-if="sticky_tooltip_name === 'keys_info'">
            <p class="sticky-tooltip-title">Search syntax</p>
            <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.85); font-size: 0.78rem;">
              Filter runs using <strong style="color:#fff">key: value</strong> pairs, separated by commas.
            </p>
            <div class="sticky-tooltip-grid" style="margin-bottom: 0.5rem;">
              <span>country: Australia</span><span>year: 2010-2015</span><span>gbp: 2-10</span>
              <span>environment: ecological</span><span>taxonomy: s__Prochlorococcus</span><span>metadata: host=Sus scrofa</span>
            </div>
            <p style="color: rgba(255,255,255,0.45); font-size: 0.72rem;">Click "List of Keys" to expand all available keys.</p>
          </template>
          <template v-if="sticky_tooltip_name === 'taxonomy_info'">
            <p class="sticky-tooltip-title">Taxonomy — detected presence only</p>
            <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.85); font-size: 0.78rem;">
              Filters runs where a taxon was <strong style="color:#fff">detected</strong> by SingleM — not that the sample is primarily composed of it.
            </p>
            <p style="color: rgba(255,255,255,0.65); font-size: 0.78rem; margin-bottom: 0.4rem;">
              A run labelled "marine metagenome" can still match <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">taxonomy: s__Prochlorococcus</code> if that organism was present in the community.
            </p>
            <p style="color: rgba(255,255,255,0.45); font-size: 0.72rem;">Use GTDB taxonomy strings, e.g. d__, p__, c__, o__, f__, g__, s__</p>
          </template>
          <template v-if="sticky_tooltip_name === 'platform_info'">
            <p class="sticky-tooltip-title">Platform — all values</p>
            <div class="sticky-tooltip-grid">
              <span>ILLUMINA</span><span>Illumina</span><span>Metagenomic</span>
            </div>
          </template>
          <template v-if="sticky_tooltip_name === 'instrument_info'">
            <p class="sticky-tooltip-title">Instrument — all values</p>
            <div class="sticky-tooltip-grid">
              <span>Illumina NovaSeq 6000</span><span>Illumina HiSeq 2500</span><span>Illumina HiSeq 4000</span>
              <span>NextSeq 500</span><span>Illumina HiSeq 2000</span><span>Illumina MiSeq</span>
              <span>HiSeq X Ten</span><span>Illumina NovaSeq X</span><span>NextSeq 2000</span>
              <span>NextSeq 550</span><span>Illumina HiSeq 3000</span><span>Illumina NovaSeq X Plus</span>
              <span>Illumina HiSeq X</span><span>Illumina HiSeq 1000</span><span>Illumina HiSeq 1500</span>
              <span>NextSeq 1000</span><span>Illumina MiniSeq</span><span>Illumina Genome Analyzer IIx</span>
              <span>Illumina Genome Analyzer II</span><span>Illumina Genome Analyzer</span>
              <span>Illumina HiSeq X Ten</span><span>HiSeq X Five</span><span>Illumina HiScanSQ</span>
              <span>Illumina iSeq 100</span><span>Nova seq</span><span>MiSeq i100</span>
            </div>
          </template>
          <template v-if="sticky_tooltip_name === 'library_info'">
            <p class="sticky-tooltip-title">Library strategy — all values</p>
            <div class="sticky-tooltip-grid">
              <span>WGS</span><span>OTHER</span><span>AMPLICON</span><span>WGA</span>
              <span>RNA-Seq</span><span>Targeted-Capture</span><span>POOLCLONE</span><span>WXS</span>
              <span>WCS</span><span>Hi-C</span><span>CLONE</span><span>ChIP-Seq</span>
              <span>Bisulfite-Seq</span><span>Synthetic-Long-Read</span><span>RAD-Seq</span><span>ATAC-seq</span>
              <span>CLONEEND</span><span>Tn-Seq</span><span>shotgun sequencing</span><span>FAIRE-seq</span>
              <span>miRNA-Seq</span><span>FL-cDNA</span><span>DNase-Hypersensitivity</span><span>CTS</span>
              <span>MRE-Seq</span><span>FINISHING</span><span>ssRNA-seq</span><span>EST</span>
              <span>GBS</span><span>RIP-Seq</span><span>ncRNA-Seq</span><span>Ribo-seq</span>
              <span>Tethered Chromatin Conformation Capture</span><span>NOMe-Seq</span><span>MBD-Seq</span>
            </div>
          </template>
          <template v-if="sticky_tooltip_name === 'habitat_info'">
            <p class="sticky-tooltip-title">IndicPiper habitat — all values</p>
            <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.8); font-size: 0.78rem;">
              Matches runs whose genus composition includes indicator genera for this habitat
              (<a href="https://github.com/cliffbueno/IndicPiper" target="_blank" rel="noopener" style="color:#8ecbff;">IndicPiper</a> analysis).
            </p>
            <div class="sticky-tooltip-grid">
              <span>activated sludge</span><span>air</span><span>anaerobic digester</span>
              <span>chicken gut</span><span>compost</span><span>food fermentation</span>
              <span>freshwater sediment</span><span>freshwater water</span><span>groundwater</span>
              <span>hot springs</span><span>human nasopharyngeal</span><span>human oral</span>
              <span>human skin</span><span>human vaginal</span><span>insect</span>
              <span>invertebrate</span><span>mammalian gut</span><span>marine plankton</span>
              <span>marine sediment</span><span>marine water</span><span>mouse gut</span>
              <span>peat</span><span>plant</span><span>soil</span><span>wastewater</span>
            </div>
          </template>
          <template v-if="sticky_tooltip_name === 'age_info'">
            <p class="sticky-tooltip-title">Age</p>
            <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.85); font-size: 0.78rem;">
              Searches <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">age</code> and <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">host_age</code> BioSample attributes by numeric value.
            </p>
            <p style="color: rgba(255,255,255,0.55); font-size: 0.75rem;">
              Age is reported at face value — the relevant scale depends on the organism and study. Could be years for a human cohort, weeks for neonates, or centuries for a tree.
            </p>
          </template>
          <template v-if="sticky_tooltip_name === 'metadata_info'">
            <p class="sticky-tooltip-title">Metadata</p>
            <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.8); font-size: 0.78rem;">
              Searches all free-form BioSample attributes submitted to NCBI.
            </p>
            <div class="sticky-tooltip-grid" style="margin-bottom: 0.5rem;">
              <span>metadata: Sus scrofa — any attribute</span>
              <span>metadata: host=Sus scrofa — specific attribute</span>
            </div>
            <div class="sticky-tooltip-grid">
              <span>host</span><span>tissue</span><span>disease</span><span>treatment</span>
              <span>isolation_source</span><span>env_biome</span><span>body_site</span><span>age</span>
              <span>sex</span><span>phenotype</span><span>genotype</span><span>strain</span>
            </div>
          </template>
          <template v-if="sticky_tooltip_name === 'metalog_info'">
            <p class="sticky-tooltip-title">Metalog metadata</p>
            <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.8); font-size: 0.78rem;">
              Searches Metalog's curated and harmonised metadata. Use a plain value to search every field, or <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">field=value</code> to search one field.
            </p>
            <div class="sticky-tooltip-grid">
              <span>metalog: diabetes</span>
              <span>metalog: host=Sus scrofa</span>
            </div>
          </template>
        </div>
      </teleport>
    </template>

    <router-view :key="$route.name + ($route.params.accession || '')" />

    &nbsp;
    <footer class="footer">
      <div class="content">
        <div class="columns">

          <div class="column has-text-centered is-two-thirds is-offset-one-eigth">
            <p />
            <p />
          <p>
            Sandpiper was devised by the <a
            href="https://research.qut.edu.au/cmr/team/ben-woodcroft/">Woodcroft
            group</a> at the <a href="https://research.qut.edu.au/cmr">Centre
            for Microbiome Research</a>, <br /> School of Biomedical Sciences,
            Queensland University of Technology
          </p>
          </div>

          <div class="column is-one-eigth">
            <a href="https://research.qut.edu.au/cmr"><img src="./assets/cmr.png"  class="footer-image" /></a>
          </div>
          <div class="column is-one-eigth">
            <a href="https://qut.edu.au"><img src="./assets/QUT_SQUARE_RGB_SVG.svg" class="footer-image" /></a>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script>
import { fetchUniversalSearch } from '@/api'
import { RANDOM_DEFAULTS } from '@/constants/randomRun'
import InfoTooltipButton from '@/components/InfoTooltipButton.vue'
import debounce from 'lodash/debounce'

function queryParamToString (value) {
  if (Array.isArray(value)) {
    return value.filter(part => typeof part === 'string' && part.length > 0).join(', ')
  }
  return typeof value === 'string' ? value : ''
}

export default {
  name: 'App',
  components: { InfoTooltipButton },
  data () {
    return {
      sticky_input: '',
      sticky_visible: false,
      sticky_keys_open: false,
      sticky_loading: false,
      sticky_count: null,
      sticky_count_request_id: 0,
      debounced_fetch_count: null,
      last_scroll_y: 0,
      run_history: [],
      sticky_tooltip_visible: false,
      sticky_tooltip_name: null,
      sticky_tooltip_x: 0,
      sticky_tooltip_y: 0,
      sticky_tooltip_timer: null,
      scroll_up_accum: 0,
    }
  },

  created () {
    // Vue binds functions declared in `methods`, which drops Lodash's custom
    // `.cancel()` property. Keep the debouncer as per-instance state instead.
    this.debounced_fetch_count = debounce(this.fetch_count, 450)
  },

  watch: {
    sticky_visible (val) {
      if (!val) {
        this.sticky_keys_open = false
        this.hideStickyTooltip()
      }
    },
    '$route' (to, from) {
      if (from.name === 'Run' && from.params.accession && from.params.accession !== to.params.accession) {
        this.run_history.push({ accession: from.params.accession, q: queryParamToString(from.query.q) })
      }
      this.sticky_count_request_id += 1
      this.debounced_fetch_count.cancel()
      this.sticky_loading = false
      this.sticky_input = queryParamToString(to.query.q)
      this.sticky_visible = false
      this.sticky_count = null
      if (this.sticky_input) this.on_sticky_input()
    }
  },

  mounted () {
    this.last_scroll_y = window.scrollY
    window.addEventListener('scroll', this.handle_scroll, { passive: true })
    if (this.$route.query.q) {
      this.sticky_input = queryParamToString(this.$route.query.q)
      this.on_sticky_input()
    }
  },

  unmounted () {
    window.removeEventListener('scroll', this.handle_scroll)
    this.sticky_count_request_id += 1
    this.debounced_fetch_count.cancel()
    clearTimeout(this.sticky_tooltip_timer)
  },

  methods: {
    handle_scroll () {
      const current = window.scrollY
      const delta = this.last_scroll_y - current
      if (delta > 0 && current > 120) {
        this.scroll_up_accum += delta
        if (this.scroll_up_accum >= 120) {
          this.sticky_visible = true
        }
      } else {
        this.scroll_up_accum = 0
        this.sticky_visible = false
      }
      this.last_scroll_y = current
    },

    on_sticky_input () {
      const requestId = ++this.sticky_count_request_id
      this.sticky_loading = false
      this.sticky_count = null
      const raw = this.sticky_input.trim()
      if (!raw) {
        this.debounced_fetch_count.cancel()
        return
      }
      this.debounced_fetch_count(requestId)
    },

    async fetch_count (requestId) {
      if (requestId !== this.sticky_count_request_id) return
      const raw = this.sticky_input.trim()
      if (!raw) { this.sticky_count = null; return }
      try {
        const { data } = await fetchUniversalSearch(raw)
        if (requestId !== this.sticky_count_request_id) return
        this.sticky_count = data.count
      } catch (e) {
        if (requestId !== this.sticky_count_request_id) return
        this.sticky_count = null
      }
    },

    // An empty search bar means "no filter", which is a legitimate request:
    // give the user another random run rather than silently doing nothing.
    next_random_run () {
      const q = this.$route.query
      this.$router.push({ name: 'RunRandom', query: {
        host: q.host ?? RANDOM_DEFAULTS.host,
        non_human_host: q.non_human_host ?? RANDOM_DEFAULTS.non_human_host,
        ecological: q.ecological ?? RANDOM_DEFAULTS.ecological,
        two_gbp: q.two_gbp ?? RANDOM_DEFAULTS.two_gbp,
        exclude_strict_low_complexity: q.exclude_strict_low_complexity ?? RANDOM_DEFAULTS.exclude_strict_low_complexity
      }})
    },

    async next_from_sticky () {
      const query = this.sticky_input.trim()
      if (!query) { this.next_random_run(); return }
      const requestId = ++this.sticky_count_request_id
      this.debounced_fetch_count.cancel()
      this.sticky_loading = true
      const current = this.$route.params.accession
      try {
        // The backend excludes `current`, so a single request either returns a
        // different run or tells us there isn't one. Sampling repeatedly and
        // discarding matches never worked when the query matched only the run
        // already being viewed.
        const { data } = await fetchUniversalSearch(query, current)
        if (requestId !== this.sticky_count_request_id) return
        this.sticky_count = data.count
        if (data.random_acc) {
          this.$router.push({ name: 'Run', params: { accession: data.random_acc }, query: { q: query } })
        } else if (data.count > 0) {
          this.$buefy.toast.open({
            message: 'No other runs match this search',
            type: 'is-warning'
          })
        } else {
          this.$buefy.toast.open({
            message: 'No runs match this search',
            type: 'is-warning'
          })
        }
      } catch (e) {
        if (requestId !== this.sticky_count_request_id) return
        this.$buefy.toast.open({
          message: 'Search failed, please try again',
          type: 'is-danger'
        })
      } finally {
        if (requestId === this.sticky_count_request_id) this.sticky_loading = false
      }
    },

    try_sticky_example () {
      this.sticky_input = 'year: 2015-2020, metadata: sex=male'
      this.on_sticky_input()
    },

    showStickyTooltip (event, name = 'keys_info') {
      clearTimeout(this.sticky_tooltip_timer)
      const trigger = event.currentTarget || event.target
      const rect = trigger.getBoundingClientRect()
      const tooltipW = 380
      const tooltipH = {
        instrument_info: 420,
        library_info: 480,
        metadata_info: 360,
        platform_info: 100,
        taxonomy_info: 220,
        age_info: 180,
        metalog_info: 200,
      }[name] ?? 200
      let x = rect.right + 10
      if (x + tooltipW > window.innerWidth - 10) x = rect.left - tooltipW - 10
      x = Math.max(10, x)
      let y = rect.top
      if (y + tooltipH > window.innerHeight - 10) y = window.innerHeight - tooltipH - 10
      y = Math.max(10, y)
      this.sticky_tooltip_x = x
      this.sticky_tooltip_y = y
      this.sticky_tooltip_name = name
      this.sticky_tooltip_visible = true
    },
    hideStickyTooltipDelayed () {
      clearTimeout(this.sticky_tooltip_timer)
      this.sticky_tooltip_timer = setTimeout(() => { this.sticky_tooltip_visible = false }, 250)
    },
    keepStickyTooltipOpen () {
      clearTimeout(this.sticky_tooltip_timer)
    },
    hideStickyTooltip () {
      clearTimeout(this.sticky_tooltip_timer)
      this.sticky_tooltip_visible = false
    },

    go_back () {
      const prev = this.run_history.pop()
      if (prev) {
        this.$router.push({ name: 'Run', params: { accession: prev.accession }, query: prev.q ? { q: prev.q } : undefined })
      }
    }
  }
}
</script>

<style lang="scss">
#app {
  // sunburst-related styles
  .pop-up {
    background-color: white;
    border: black;
    pointer-events: none;
    opacity: 0.92;
    font-size: 25px;
  }
  .sunburst {
    width: 100%;
    height: 900px;
    position: relative;
    font-size: 10px;
  }
  .sunburst-annotation {
    width: 100%;
    position: relative;
    font-size: 30px;
  }
  .svg-link {
    fill: blue;
  }

  .sandpiperbackground {
    background-image: url("./assets/sandpiper.jpg");
    background-size: 100%;
  }
  .footer-image {
    height: 50%;
  }
}

.sticky-pull-tab {
  appearance: none;
  position: fixed;
  top: 50vh;
  right: 0;
  z-index: 2001;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-right: none;
  border-radius: 6px 0 0 6px;
  padding: 0.7rem 0.45rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  box-shadow: -2px 2px 10px rgba(0, 0, 0, 0.08);
  user-select: none;
  transition: background 0.15s ease;
}
.sticky-pull-tab:focus-visible,
.sticky-close-tab:focus-visible,
.text-toggle:focus-visible {
  outline: 2px solid #3273dc;
  outline-offset: 2px;
}
.sticky-pull-tab:hover {
  background: rgba(255, 255, 255, 0.96);
}
.sticky-pull-label {
  font-size: 0.65rem;
  font-weight: 600;
  color: #555;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.sticky-search-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 2000;
  background: rgba(255, 255, 255, 1);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.07);
  box-shadow: 0 2px 14px rgba(0, 0, 0, 0.07);
  padding: 0.9rem 3.5rem 0.7rem;
  transform: translateY(-110%);
  transition: transform 0.25s ease;
}
.sticky-search-bar.is-visible {
  transform: translateY(0);
}
.sticky-inner {
  max-width: 1200px;
  margin: 0 auto;
}
.sticky-bar-row {
  display: flex;
  align-items: flex-start;
  gap: 1.75rem;
  min-height: 0;
}
.sticky-input-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
}
.sticky-field-grow {
  margin-bottom: 0 !important;
}
.sticky-sub-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.2rem;
}
.sticky-logos-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
  margin-left: auto;
}
/* Lets the dropped bar be dismissed without hunting for the pull tab (fixed
   at 50vh, which can be far from the reader's eye once the bar is open).
   Same frosted-glass tab treatment as .sticky-pull-tab, and the same
   "flat on the attached edge, rounded on the outer edge" logic -- that one
   hangs off the viewport's right edge, this one hangs off the BAR's
   bottom edge, so the radii are rotated a quarter turn to match. Anchored
   to .sticky-search-bar (position: fixed, so it's a valid containing
   block) rather than the viewport, and offset up by its own border so the
   seam where it meets the bar disappears. `right: 1.5rem` keeps a margin
   off the viewport edge without touching the bar's own content, which
   ends well before the edge inside the bar's 3.5rem side padding. */
.sticky-close-tab {
  appearance: none;
  position: absolute;
  top: 100%;
  right: 1.5rem;
  margin-top: -1px;
  z-index: 1999;
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-top: none;
  border-radius: 0 0 6px 6px;
  padding: 0.45rem 1rem;
  cursor: pointer;
  user-select: none;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
  transition: background 0.15s ease;
}
.sticky-close-tab:hover {
  background: rgba(255, 255, 255, 0.96);
}
.sticky-close-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: #555;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.sticky-logo-left {
  height: 75px;
  width: auto;
  max-width: 250px;
  object-fit: contain;
  flex-shrink: 0;
}
.sticky-logo {
  height: 54px;
  width: auto;
  max-width: 173px;
  object-fit: contain;
  opacity: 0.8;
}
.sticky-count-below {
  font-size: 0.72rem;
  color: rgba(0, 0, 0, 0.35);
  white-space: nowrap;
  pointer-events: none;
}
.sticky-keys-toggle {
  appearance: none;
  border: 0;
  padding: 0;
  background: transparent;
  font: inherit;
  cursor: pointer;
  font-weight: 600;
  user-select: none;
}
.sticky-keys-panel {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
}
.sticky-keys-panel.is-open {
  max-height: 650px;
}
.sticky-syntax-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 0.75rem 0.1rem;
  border-top: 1px solid rgba(0,0,0,0.07);
  margin-top: 0.4rem;
}
.sticky-syntax-title {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #999;
  white-space: nowrap;
}
.sticky-syntax-items {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 0.75rem;
}
.sticky-syntax-item {
  font-size: 0.72rem;
  color: #666;
  white-space: nowrap;
}
.sticky-syntax-item code {
  color: hsl(271, 100%, 71%);
  margin-right: 0.2rem;
}
.sticky-example-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem 0.25rem;
}
.sticky-example-label {
  font-size: 0.75rem;
  color: #666;
  white-space: nowrap;
}
.sticky-example-query {
  font-size: 0.72rem;
  color: #444;
  flex: 1;
}
.sticky-keys-box {
  background: rgba(225, 225, 225, 0.88);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-radius: 6px;
  padding: 0.75rem 1.25rem;
  margin-top: 0.4rem;
}
.sticky-keys-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0 1.5rem;
}
.sticky-keys-grid code {
  color: hsl(271, 100%, 71%);
}
.keys-group {
  min-width: 0;
}
.keys-group-title {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #999;
  border-bottom: 1px solid rgba(0,0,0,0.1);
  padding-bottom: 0.2rem;
  margin-bottom: 0.35rem;
}
.keys-item {
  font-size: 0.8rem;
  margin-bottom: 0.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.02rem;
}
.keys-example {
  color: #aaa;
  font-size: 0.72rem;
  padding-left: 0.2rem;
}
.sticky-keys-left {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}
.keys-item-label {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
}
.sticky-info-icon {
  cursor: help;
  color: #bbb;
  font-size: 0.8rem;
  user-select: none;
}
.sticky-info-icon:hover {
  color: #555;
}
.sticky-info-tooltip {
  position: fixed;
  z-index: 9999;
  background: rgba(25, 25, 35, 0.97);
  color: #fff;
  border-radius: 8px;
  padding: 0.8rem 1rem;
  min-width: 280px;
  max-width: 380px;
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.5);
  font-size: 0.78rem;
  line-height: 1.5;
  pointer-events: auto;
}
.sticky-tooltip-title {
  font-weight: 700;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 0.5rem;
}
.sticky-tooltip-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
.sticky-tooltip-grid span {
  background: rgba(255, 255, 255, 0.12);
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-size: 0.75rem;
  white-space: nowrap;
}

@media (max-width: 1023px) {
  .sticky-search-bar {
    padding-left: 1.25rem;
    padding-right: 1.25rem;
  }
  .sticky-bar-row {
    gap: 1rem;
  }
  .sticky-logo-left {
    height: 56px;
    max-width: 150px;
  }
  .sticky-logos-right {
    display: none;
  }
  .sticky-keys-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  #app {
    overflow-x: hidden;
  }
  #app .container {
    min-width: 0;
  }
  #app .section {
    padding: 1.5rem 1rem;
  }
  #app .section .section {
    padding-left: 0;
    padding-right: 0;
  }
  #app .advanced-search-section {
    padding-left: 0;
    padding-right: 0;
  }
  #app .has-text-justified {
    text-align: left !important;
  }
  #app .title,
  #app .subtitle,
  #app p,
  #app li,
  #app a {
    overflow-wrap: anywhere;
  }
  #app .table-wrapper {
    max-width: 100%;
    overflow-x: auto;
  }
  #app .button,
  #app .input,
  #app .switch {
    min-height: 44px;
  }
  #app .input {
    font-size: 16px;
  }
  #app .sunburst,
  #app .sunburst-annotation {
    height: auto;
    min-height: 0;
  }
  #app svg.sunburst,
  #app svg.sunburst-annotation {
    display: block;
    max-width: 100%;
    aspect-ratio: 1;
  }
  #app .footer {
    padding: 2rem 1rem;
  }
  #app .footer-image {
    display: block;
    width: auto;
    height: auto;
    max-height: 72px;
    margin: 0 auto;
  }
  .sticky-pull-tab {
    top: auto;
    right: 0.75rem;
    bottom: 0.75rem;
    min-height: 44px;
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 999px;
    padding: 0.65rem 0.9rem;
  }
  .sticky-pull-tab.is-drawer-open {
    display: none;
  }
  .sticky-pull-label {
    writing-mode: horizontal-tb;
    text-orientation: initial;
  }
  .sticky-keys-toggle {
    display: inline-flex;
    align-items: center;
    min-height: 44px;
    padding: 0.5rem 0;
  }
  .sticky-search-bar {
    max-height: 100dvh;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 3rem 0.75rem 0.75rem;
  }
  .sticky-bar-row {
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .sticky-input-col {
    order: -1;
    flex: 1 1 100%;
    width: 100%;
  }
  .sticky-logo-left,
  .sticky-logos-right {
    display: none;
  }
  .sticky-close-tab {
    position: fixed;
    top: 0.35rem;
    right: 0.35rem;
    min-width: 44px;
    min-height: 44px;
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 6px;
    padding: 0.45rem 0.7rem;
  }
  .sticky-keys-panel.is-open {
    max-height: none;
  }
  .sticky-keys-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }
  .sticky-info-tooltip {
    left: 10px !important;
    top: 10px !important;
    width: calc(100vw - 20px);
    min-width: 0;
    max-width: none;
    max-height: calc(100dvh - 20px);
    overflow-y: auto;
  }
  .sticky-tooltip-grid span {
    max-width: 100%;
    white-space: normal;
    overflow-wrap: anywhere;
  }
}

@media (max-width: 430px) {
  .sticky-keys-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .sticky-syntax-row,
  .sticky-example-row {
    align-items: flex-start;
    flex-direction: column;
    padding-left: 0;
    padding-right: 0;
  }
  .sticky-syntax-item {
    white-space: normal;
  }
  .sticky-example-query {
    width: 100%;
    overflow-wrap: anywhere;
  }
  .sticky-keys-box {
    padding: 0.75rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sticky-search-bar,
  .sticky-keys-panel {
    transition: none;
  }
}
</style>
