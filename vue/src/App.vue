<template>
  <div id="app">
    <b-navbar :centered="true" type="is-light">
        <template #start>
            <b-navbar-item tag="router-link" :to="{ path: '/' }">Home</b-navbar-item>
            <b-navbar-item tag="router-link" :to="{ path: '/Search' }">Search</b-navbar-item>

            <b-navbar-item tag="router-link" :to="{ path: '/Run/SRR9841429' }">Example 1</b-navbar-item>
            <b-navbar-item tag="router-link" :to="{ path: '/Run/ERR1914274' }">Example 2</b-navbar-item>
            <b-navbar-item tag="router-link" :to="{ path: '/amplicon/run/SRR3741935' }">Amplicon example</b-navbar-item>

            <b-navbar-item tag="router-link" :to="{ path: '/About' }">About</b-navbar-item>
        </template>
    </b-navbar>

    <template v-if="is_run_page">
      <!-- Pull tab — always visible on Run pages (metagenome and amplicon) -->
      <button type="button" class="sticky-pull-tab" :class="{ 'is-drawer-open': sticky_visible }" :aria-expanded="sticky_visible" aria-controls="run-search-panel" aria-label="Continue searching runs" @click="sticky_visible = !sticky_visible">
        <span class="sticky-pull-label">Continue searching</span>
      </button>

      <!-- Sticky bar -->
      <div id="run-search-panel" class="sticky-search-bar" :class="{ 'is-visible': sticky_visible }" :aria-hidden="!sticky_visible" :inert="!sticky_visible">
        <div class="sticky-inner">
          <div class="sticky-bar-row">
            <b-button v-if="run_history.length > 0" type="is-primary" class="sticky-prev-btn" aria-label="Previous run" @click="go_back">←<span class="sticky-prev-label"> Previous</span></b-button>
            <div class="sticky-input-col">
              <b-field class="sticky-field-grow">
                <div class="search-autocomplete-wrap">
                  <b-input id="sticky-run-search" name="sticky-run-search" v-model="sticky_input" aria-label="Filter runs" :placeholder="is_amplicon_run ? 'e.g. marker: ITS' : 'e.g. country: Australia'" icon="magnify" expanded
                    @input="on_sticky_input" @keydown="on_sticky_keydown"></b-input>
                  <div v-if="sticky_ghost_suffix" ref="stickyGhost" class="search-ghost-overlay" aria-hidden="true">
                    <span class="search-ghost-typed">{{ sticky_input }}</span><span class="search-ghost-suffix">{{ sticky_ghost_suffix }}</span>
                  </div>
                  <ul v-if="ac_suggestions.length" class="search-suggest-dropdown" role="listbox">
                    <li v-for="(s, i) in ac_suggestions" :key="s.kind + s.label" role="option" :aria-selected="i === ac_active_index"
                      :class="{ 'is-active': i === ac_active_index }" @mousedown.prevent="on_sticky_click_suggestion(s)">
                      {{ s.label }}
                    </li>
                  </ul>
                </div>
                <div class="control">
                  <b-button type="is-primary" :loading="sticky_loading" @click="next_from_sticky">Next</b-button>
                </div>
              </b-field>
              <div class="sticky-sub-row">
                <span class="sticky-keys-left">
                  <button type="button" class="sticky-keys-toggle" :class="{ 'is-open': sticky_keys_open }" :aria-expanded="sticky_keys_open" aria-controls="run-search-keys" @click="sticky_keys_open = !sticky_keys_open">
                    List of keys
                    <span class="disclosure-chevron" aria-hidden="true">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
                    </span>
                  </button>
                  <InfoTooltipButton controls="run-search-popover" label="Show search syntax help" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'keys_info'" @open="showStickyTooltip($event, 'keys_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" />
                  <b-button type="is-light" size="is-small" icon-left="shuffle-variant" class="sticky-random-button" @click="next_random_run">Random Search</b-button>
                </span>
                <span v-if="sticky_count !== null" class="sticky-count-below" aria-live="polite" aria-atomic="true">{{ sticky_count.toLocaleString() }} runs</span>
              </div>
            </div>
            <div class="sticky-logos-group">
              <img src="./assets/sandpiper_logo.png" width="1009" height="746" class="sticky-logo sticky-logo-left" alt="Sandpiper" />
              <div class="sticky-logos-right">
                <img src="./assets/cmr.png" width="1280" height="1024" class="sticky-logo" alt="CMR" />
                <img src="./assets/QUT_SQUARE_RGB_SVG.svg" width="113" height="113" class="sticky-logo" alt="QUT" />
              </div>
            </div>
          </div>
          <div id="run-search-keys" class="sticky-keys-panel" :class="{ 'is-open': sticky_keys_open }">
            <div class="sticky-keys-box">
              <template v-if="is_amplicon_run">
              <div class="sticky-keys-grid">
                <div v-for="group in amplicon_groups" :key="group" class="keys-group">
                  <p class="keys-group-title">{{ group }}</p>
                  <div v-for="f in amplicon_fields_in(group)" :key="f.key" class="keys-item"><code>{{ f.key }}</code><span class="keys-example">e.g. {{ f.example }}</span></div>
                </div>
              </div>
              <div class="sticky-syntax-row">
                <span class="sticky-syntax-title">Query Syntax</span>
                <div class="sticky-syntax-items">
                  <span class="sticky-syntax-item"><code>ITS</code> exact value</span>
                  <span class="sticky-syntax-item"><code>2010-2015</code> year range</span>
                  <span class="sticky-syntax-item"><code>yes</code> / <code>no</code> QC flags</span>
                  <span class="sticky-syntax-item"><code>"Oahu, Kaneohe Bay"</code> quotes keep a comma inside one value</span>
                </div>
              </div>
              <div class="sticky-example-row">
                <span class="sticky-example-label">Example:</span>
                <code class="sticky-example-query">{{ amplicon_example }}</code>
                <b-button size="is-small" type="is-primary" @click="try_sticky_example">Try it</b-button>
              </div>
              </template>
              <template v-else>
              <div class="sticky-keys-grid">
                <div class="keys-group">
                  <p class="keys-group-title">Keywords</p>
                  <div class="keys-item"><code>keywords</code><span class="keys-example">e.g. "sponge reef, coral"</span></div>
                </div>

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
                  <div class="keys-item"><code>synthetic</code><span class="keys-example">yes or no</span></div>
                  <div class="keys-item"><code>non_metagenome_organism</code><span class="keys-example">yes or no</span></div>
                  <div class="keys-item"><code>rna_or_non_dna</code><span class="keys-example">yes or no</span></div>
                  <div class="keys-item">
                    <code class="keys-item-label">age <InfoTooltipButton controls="run-search-popover" label="Show age search help" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'age_info'" @open="showStickyTooltip($event, 'age_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" /></code>
                    <span class="keys-example">e.g. 25 or 20-30</span>
                  </div>
                  <div class="keys-item">
                    <code class="keys-item-label">habitat <InfoTooltipButton controls="run-search-popover" label="Show IndicPiper habitat values" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'habitat_info'" @open="showStickyTooltip($event, 'habitat_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" /></code>
                    <span class="keys-example">e.g. soil or soil&gt;=0.1</span>
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
                  <div class="keys-item">
                    <code class="keys-item-label">organism <InfoTooltipButton controls="run-search-popover" label="Show organism search help" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'organism_info'" @open="showStickyTooltip($event, 'organism_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" /></code>
                    <span class="keys-example">e.g. marine metagenome</span>
                  </div>
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
                    <code class="keys-item-label">metalog <InfoTooltipButton controls="run-search-popover" label="Show Metalog metadata search help" :expanded="sticky_tooltip_visible && sticky_tooltip_name === 'metalog_info'" @open="showStickyTooltip($event, 'metalog_info')" @close-delayed="hideStickyTooltipDelayed" @close="hideStickyTooltip" /> <button type="button" class="keys-any-btn" title="Match any run with Metalog data present" @click="insert_sticky_metalog_any">Any</button></code>
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
                  <span class="sticky-syntax-item"><code>"Oahu, Kaneohe Bay"</code> quotes keep a comma inside one value</span>
                </div>
              </div>
              <div class="sticky-example-row">
                <span class="sticky-example-label">Example:</span>
                <code class="sticky-example-query">year: 2015-2020, metadata: sex=male</code>
                <b-button size="is-small" type="is-primary" @click="try_sticky_example">Try it</b-button>
              </div>
              </template>
            </div>
          </div>
        </div>
        <button v-if="sticky_visible" type="button" class="sticky-close-tab" :class="{ 'is-keys-open': sticky_keys_open }" aria-label="Close run search" @click="sticky_visible = false">
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
          <template v-if="sticky_tooltip_name === 'organism_info'">
            <p class="sticky-tooltip-title">Organism</p>
            <p style="color: rgba(255,255,255,0.85); font-size: 0.78rem;">
              Searches the NCBI taxon assigned to the run. Covers both single-organism identifications
              (e.g. <em>Homo sapiens</em>, <em>Vibrio cholerae</em>) and NCBI's metagenome pseudo-taxa
              (e.g. <em>soil metagenome</em>, <em>human gut metagenome</em>) — use this field for
              metagenome searches too.
            </p>
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
            <p class="sticky-tooltip-title">Platform — all values <span class="tooltip-hint">(click to use)</span></p>
            <div class="sticky-tooltip-grid is-clickable" @click="insert_sticky_tooltip_value($event, 'platform_info')">
              <span>ILLUMINA</span><span>Illumina</span><span>Metagenomic</span>
            </div>
          </template>
          <template v-if="sticky_tooltip_name === 'instrument_info'">
            <p class="sticky-tooltip-title">Instrument — all values <span class="tooltip-hint">(click to use)</span></p>
            <div class="sticky-tooltip-grid is-clickable" @click="insert_sticky_tooltip_value($event, 'instrument_info')">
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
            <p class="sticky-tooltip-title">Library strategy — all values <span class="tooltip-hint">(click to use)</span></p>
            <div class="sticky-tooltip-grid is-clickable" @click="insert_sticky_tooltip_value($event, 'library_info')">
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
            <p class="sticky-tooltip-title">IndicPiper habitat — all values <span class="tooltip-hint">(click to use)</span></p>
            <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.8); font-size: 0.78rem;">
              Matches runs whose genus composition includes indicator genera for this habitat
              (<a href="https://github.com/cliffbueno/IndicPiper" target="_blank" rel="noopener" style="color:#8ecbff;">IndicPiper</a> analysis).
              Add <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">&gt;=</code>, <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">&gt;</code>, <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">&lt;=</code> or <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">&lt;</code> plus a number to threshold on that habitat's IndicPiper score instead of just matching its presence, e.g. <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">soil&gt;=0.1</code>. Leave the name off and just give a comparison, e.g. <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">habitat: &gt;0.5</code>, to match runs whose strongest habitat match (whichever habitat that is) exceeds it.
            </p>
            <div class="sticky-tooltip-grid is-clickable" @click="insert_sticky_tooltip_value($event, 'habitat_info')">
              <span>human oral</span><span>mammalian gut</span><span>human vaginal</span>
              <span>wastewater</span><span>soil</span><span>phyllosphere</span>
              <span>human skin</span><span>freshwater sediment</span><span>freshwater water</span>
              <span>glacier</span><span>marine sediment</span><span>marine water</span>
              <span>hydrothermal vent</span>
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
            <p class="sticky-tooltip-title">Metadata <span class="tooltip-hint">(click to use)</span></p>
            <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.8); font-size: 0.78rem;">
              Searches all free-form BioSample attributes submitted to NCBI.
            </p>
            <div class="sticky-tooltip-grid is-clickable" style="margin-bottom: 0.5rem;" @click="insert_sticky_tooltip_value($event, 'metadata_info')">
              <span>metadata: Sus scrofa — any attribute</span>
              <span>metadata: host=Sus scrofa — specific attribute</span>
            </div>
            <div class="sticky-tooltip-grid is-clickable" @click="insert_sticky_tooltip_value($event, 'metadata_info')">
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

    <div class="route-content">
      <img v-if="pageLoadingState.isLoading" src="./assets/sandpiper.jpg" width="1024" height="667" alt="" aria-hidden="true" class="route-content-image" />
      <router-view :key="$route.name + ($route.params.accession || '')" />
    </div>

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

          <div class="column is-one-quarter footer-logos">
            <a href="https://research.qut.edu.au/cmr"><img src="./assets/cmr.png" width="1280" height="1024"  class="footer-image" /></a>
            <a href="https://qut.edu.au"><img src="./assets/QUT_SQUARE_RGB_SVG.svg" width="113" height="113" class="footer-image" /></a>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script>
import { fetchUniversalSearch, fetchTaxonomySearchHints, fetchSearchFieldValues } from '@/api'
import { fetchAmpliconUniversalSearch } from '@/api/amplicon'
import { AMPLICON_GROUPS, AMPLICON_EXAMPLE, parseAmpliconQuery } from '@/constants/ampliconFields'
import { ampliconAutocompleteFields, fetchAmpliconLiveValues, loadAmpliconFacets, availableAmpliconFields, unavailableAmpliconKeys } from '@/composables/ampliconAutocomplete'
import { SEARCH_FIELDS } from '@/constants/searchFields'
import { useRoute } from 'vue-router'
import { RANDOM_DEFAULTS } from '@/constants/randomRun'
import InfoTooltipButton from '@/components/InfoTooltipButton.vue'
import { pageLoadingState, startPageLoading } from '@/store/pageLoading'
import { useSearchAutocomplete, splitActiveSegment } from '@/composables/useSearchAutocomplete'
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
  setup () {
    // Same engine as Search.vue's universal bar, wired to sticky_input
    // instead -- see useSearchAutocomplete for the shared ranking/Tab-cycle
    // logic (docs/superpowers/specs/2026-09-14-search-bar-autocomplete-design.md).
    // On an amplicon run page the bar searches amplicon runs: same
    // dropdown, amplicon keys and values.
    const route = useRoute()
    const isAmplicon = () => route.name === 'AmpliconRun'
    const autocomplete = useSearchAutocomplete(async (field, q, signal) => {
      if (isAmplicon()) return fetchAmpliconLiveValues(field, q)
      if (field === 'taxonomy') {
        const { data } = await fetchTaxonomySearchHints(q, undefined, signal)
        return (data.taxonomies || []).map(name => ({ value: name, count: null }))
      }
      const { data } = await fetchSearchFieldValues(field, q, signal)
      return data.values
    }, () => (isAmplicon() ? ampliconAutocompleteFields() : SEARCH_FIELDS))
    return {
      ac_suggestions: autocomplete.suggestions,
      ac_active_index: autocomplete.activeIndex,
      ac_on_input: autocomplete.onInput,
      ac_cycle_next: autocomplete.cycleNext,
      ac_apply_suggestion: autocomplete.applySuggestion,
      ac_clear: autocomplete.clear,
    }
  },
  data () {
    return {
      sticky_input: '',
      sticky_visible: false,
      sticky_keys_open: false,
      sticky_loading: false,
      sticky_count: null,
      sticky_count_request_id: 0,
      sticky_abort: null,
      debounced_fetch_count: null,
      last_scroll_y: 0,
      run_history: [],
      sticky_tooltip_visible: false,
      sticky_tooltip_name: null,
      sticky_tooltip_x: 0,
      sticky_tooltip_y: 0,
      sticky_tooltip_timer: null,
      scroll_up_accum: 0,
      amplicon_groups: AMPLICON_GROUPS,
      amplicon_example: AMPLICON_EXAMPLE,
      pageLoadingState,
    }
  },

  created () {
    // Vue binds functions declared in `methods`, which drops Lodash's custom
    // `.cancel()` property. Keep the debouncer as per-instance state instead.
    this.debounced_fetch_count = debounce(this.fetch_count, 450)
  },

  computed: {
    is_amplicon_run () {
      return this.$route.name === 'AmpliconRun'
    },
    is_run_page () {
      return this.$route.name === 'Run' || this.is_amplicon_run
    },
    // See Search.vue's identical ghost_suffix for the reasoning -- only a
    // literal prefix match gets grey inline completion, even though the
    // dropdown itself allows substring matches.
    sticky_ghost_suffix () {
      const s = this.ac_suggestions[this.ac_active_index]
      if (!s) return ''
      const target = s.kind === 'key' ? s.insertKey : s.insertValue
      if (!target) return ''
      const el = document.getElementById('sticky-run-search')
      const caret = el ? el.selectionStart : this.sticky_input.length
      const seg = splitActiveSegment(this.sticky_input, caret)
      if (!target.toLowerCase().startsWith(seg.value.toLowerCase())) return ''
      return target.slice(seg.value.length)
    },
  },

  watch: {
    sticky_ghost_suffix (value) {
      if (value) this.$nextTick(this.sync_sticky_ghost_overlay_style)
    },
    sticky_visible (val) {
      if (!val) {
        this.sticky_keys_open = false
        this.hideStickyTooltip()
      }
    },
    '$route' (to, from) {
      // Only start the loading window when the router-view key (below)
      // is actually about to change -- that's the only case where the view
      // remounts and its created() hook runs stopPageLoading() to end this
      // window. A same-route query change (e.g. Search's "Try it" example,
      // which does $router.replace({ query }) without changing name/
      // accession) fires this watcher too, but doesn't remount anything --
      // starting the loading state there left it stuck on forever, since
      // nothing was ever going to call stopPageLoading() again.
      const routeKeyChanged = (to.name + (to.params.accession || '')) !== (from.name + (from.params.accession || ''))
      if (routeKeyChanged) startPageLoading()

      if ((from.name === 'Run' || from.name === 'AmpliconRun') && from.params.accession && from.params.accession !== to.params.accession) {
        this.run_history.push({ name: from.name, accession: from.params.accession, q: queryParamToString(from.query.q) })
      }
      if (to.name === 'AmpliconRun') {
        loadAmpliconFacets().catch(err => console.error('Amplicon facets request failed', err))
      }
      this.sticky_count_request_id += 1
      this.sticky_abort?.abort()
      this.debounced_fetch_count.cancel()
      this.sticky_loading = false
      this.sticky_input = queryParamToString(to.query.q)
      this.sticky_visible = false
      this.sticky_count = null
      // Refresh the count only, not autocomplete -- this text arrived from
      // the URL (e.g. Search.vue's own bar just accepted a suggestion and
      // pushed the completed query), not from the user typing into THIS
      // bar. Calling on_sticky_input() here recomputed suggestions for that
      // already-complete text, which still matches itself and related live
      // values, so the sticky dropdown popped open uninvited and stayed
      // open since nothing else ever clears it. See refresh_sticky_state's
      // comment for the identical problem apply_sticky_suggestion avoids.
      // Only the run pages show this bar; elsewhere the page's own search
      // box already fetches this count, so a second request would be a duplicate.
      if (this.sticky_input && this.is_run_page) this.refresh_sticky_state()
      this.ac_clear()
    }
  },

  mounted () {
    this.last_scroll_y = window.scrollY
    window.addEventListener('scroll', this.handle_scroll, { passive: true })
    if (this.$route.query.q) {
      this.sticky_input = queryParamToString(this.$route.query.q)
      if (this.is_run_page) this.refresh_sticky_state()
    }
    this.sync_sticky_ghost_overlay_style()
  },

  unmounted () {
    window.removeEventListener('scroll', this.handle_scroll)
    this.sticky_count_request_id += 1
    this.sticky_abort?.abort()
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
      this.refresh_sticky_state()
      const el = document.getElementById('sticky-run-search')
      this.ac_on_input(this.sticky_input, el ? el.selectionStart : this.sticky_input.length)
    },

    // Count refresh, split out of on_sticky_input so apply_sticky_suggestion
    // (below) can run it WITHOUT also recomputing autocomplete suggestions --
    // see Search.vue's refresh_universal_state for why: a just-accepted value
    // like "Australia: NSW" still matches itself when re-queried, so without
    // this split the dropdown never emptied out and Enter kept re-accepting
    // the same value instead of ever reaching next_from_sticky().
    refresh_sticky_state () {
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

    // Same Tab/Enter/Right/Escape handling as Search.vue's
    // on_universal_keydown, wired to sticky_input; with no suggestion open,
    // Enter falls through to next_from_sticky (this bar's existing
    // "jump to the next matching run" action) rather than search_universal,
    // since that's what this bar has always done.
    on_sticky_keydown (event) {
      if (event.key === 'Tab') {
        if (this.ac_suggestions.length === 0) return
        event.preventDefault()
        this.ac_cycle_next()
        return
      }
      if (event.key === 'Enter') {
        if (this.ac_suggestions.length > 0) {
          event.preventDefault()
          this.accept_sticky_suggestion(event.target)
          return
        }
        this.next_from_sticky()
        return
      }
      if (event.key === 'ArrowRight') {
        const el = event.target
        const atEnd = el.selectionStart === el.value.length && el.selectionStart === el.selectionEnd
        if (atEnd && this.ac_suggestions.length > 0) {
          event.preventDefault()
          this.accept_sticky_suggestion(el)
        }
        return
      }
      if (event.key === 'Escape') {
        this.ac_clear()
      }
    },

    accept_sticky_suggestion (inputEl) {
      const s = this.ac_suggestions[this.ac_active_index]
      if (!s) return
      this.apply_sticky_suggestion(s, inputEl)
    },

    on_sticky_click_suggestion (s) {
      this.apply_sticky_suggestion(s, document.getElementById('sticky-run-search'))
    },

    apply_sticky_suggestion (s, inputEl) {
      const caret = inputEl ? inputEl.selectionStart : this.sticky_input.length
      const { text, caret: newCaret } = this.ac_apply_suggestion(this.sticky_input, caret, s)
      this.sticky_input = text
      this.refresh_sticky_state()
      this.ac_clear()
      this.$nextTick(() => {
        if (!inputEl) return
        inputEl.setSelectionRange(newCaret, newCaret)
        inputEl.focus()
      })
    },

    // See Search.vue's identical sync_ghost_overlay_style for why this
    // copies computed style at runtime instead of hand-matching Bulma's
    // padding constants.
    sync_sticky_ghost_overlay_style () {
      const wrap = this.$el.querySelector('.sticky-input-col .search-autocomplete-wrap')
      const input = wrap && wrap.querySelector('input#sticky-run-search')
      if (!wrap || !input) return
      const cs = window.getComputedStyle(input)
      const overlay = wrap.querySelector('.search-ghost-overlay')
      if (!overlay) return
      for (const prop of ['fontFamily', 'fontSize', 'fontWeight', 'letterSpacing', 'lineHeight', 'padding', 'border', 'boxSizing']) {
        overlay.style[prop] = cs[prop]
      }
    },

    async fetch_count (requestId) {
      if (requestId !== this.sticky_count_request_id) return
      const raw = this.sticky_input.trim()
      if (!raw) { this.sticky_count = null; return }
      try {
        if (this.amplicon_unknown_keys(raw).length > 0) { this.sticky_count = null; return }
        this.sticky_abort?.abort()
        this.sticky_abort = new AbortController()
        const { data } = await this.fetch_matches(raw, undefined, this.sticky_abort.signal)
        if (requestId !== this.sticky_count_request_id) return
        this.sticky_count = data.count
      } catch (e) {
        if (requestId !== this.sticky_count_request_id) return
        this.sticky_count = null
      }
    },

    amplicon_fields_in (group) {
      return availableAmpliconFields(group)
    },

    // Typos and keys the loaded amplicon data has no column for.
    amplicon_unknown_keys (query) {
      return this.is_amplicon_run ? [...parseAmpliconQuery(query).unknown, ...unavailableAmpliconKeys(query)] : []
    },

    fetch_matches (query, exclude, signal) {
      return this.is_amplicon_run ? fetchAmpliconUniversalSearch(query, exclude, signal) : fetchUniversalSearch(query, exclude, signal)
    },

    run_route (accession, query) {
      return { name: this.is_amplicon_run ? 'AmpliconRun' : 'Run', params: { accession }, query: query ? { q: query } : undefined }
    },

    // An empty search bar means "no filter", which is a legitimate request:
    // give the user another random run rather than silently doing nothing.
    async next_random_run () {
      if (this.is_amplicon_run) {
        try {
          const { data } = await fetchAmpliconUniversalSearch('', this.$route.params.accession)
          if (data.random_acc) this.$router.push(this.run_route(data.random_acc))
          else this.$buefy.toast.open({ message: 'No other amplicon runs', type: 'is-warning' })
        } catch (e) {
          this.$buefy.toast.open({ message: 'Search failed, please try again', type: 'is-danger' })
        }
        return
      }
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
      const unknown = this.amplicon_unknown_keys(query)
      if (unknown.length > 0) {
        this.$buefy.toast.open({ message: `Unknown amplicon key(s): ${unknown.join(', ')}`, type: 'is-warning' })
        return
      }
      const requestId = ++this.sticky_count_request_id
      this.debounced_fetch_count.cancel()
      this.sticky_loading = true
      const current = this.$route.params.accession
      try {
        // The backend excludes `current`, so a single request either returns a
        // different run or tells us there isn't one. Sampling repeatedly and
        // discarding matches never worked when the query matched only the run
        // already being viewed.
        const { data } = await this.fetch_matches(query, current)
        if (requestId !== this.sticky_count_request_id) return
        this.sticky_count = data.count
        if (data.random_acc) {
          this.$router.push(this.run_route(data.random_acc, query))
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
      this.sticky_input = this.is_amplicon_run ? AMPLICON_EXAMPLE : 'year: 2015-2020, metadata: sex=male'
      this.on_sticky_input()
    },

    // Adds a "metalog: " clause (empty value -- matches any run with Metalog
    // data present, same semantics as Search.vue's Metalog "Any" toggle) onto
    // whatever the user has already typed, rather than clobbering it the way
    // try_sticky_example's canned example does. No-ops if a metalog clause is
    // already present, so repeated clicks don't stack duplicates.
    insert_sticky_metalog_any () {
      const existing = this.sticky_input.trim()
      if (/(^|,)\s*metalog\s*:/i.test(existing)) return
      this.sticky_input = existing ? `${existing}, metalog: ` : 'metalog: '
      this.on_sticky_input()
    },

    // "List of keys" value-list tooltips (platform/instrument/library/habitat)
    // list every real database value. Clicking one appends "key: value" to the
    // search bar instead of leaving the user to retype it -- same append
    // semantics as insert_sticky_metalog_any, so repeated queries just grow.
    insert_sticky_tooltip_value (event, tooltipName) {
      const target = event.target.closest('span')
      if (!target) return
      const fieldForTooltip = {
        platform_info: 'platform',
        instrument_info: 'instrument',
        library_info: 'library_strategy',
        habitat_info: 'habitat',
        metadata_info: 'metadata',
      }[tooltipName]
      if (!fieldForTooltip) return
      // metadata_info mixes full "key: value — description" example spans
      // (already query-ready once the description is stripped) with bare
      // attribute names (e.g. "host") that need "=" appended so the cursor
      // lands ready for a value.
      const raw = target.textContent.split('—')[0].trim()
      const part = raw.includes(':') ? raw
        : tooltipName === 'metadata_info' ? `${fieldForTooltip}: ${raw}=`
        : `${fieldForTooltip}: ${raw}`
      const existing = this.sticky_input.trim()
      this.sticky_input = existing ? `${existing}, ${part}` : part
      this.hideStickyTooltip()
      this.on_sticky_input()
      this.$nextTick(() => document.getElementById('sticky-run-search')?.focus())
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
        organism_info: 150,
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
        this.$router.push({ name: prev.name, params: { accession: prev.accession }, query: prev.q ? { q: prev.q } : undefined })
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

  // Sunburst3.vue owns its own sizing/responsive rules in scoped styles now;
  // only cross-cutting, non-sunburst-specific rules remain here.

  .sandpiperbackground {
    background-image: url("./assets/sandpiper.jpg");
    // `background-size: 100%` scales the image to the width of the element and
    // leaves its height to the aspect ratio, so the image was tiled a second
    // time down the page whenever the content was taller than that - which is
    // always the case on a narrow (mobile) viewport.
    background-size: cover;
    background-position: center center;
    background-repeat: no-repeat;
  }
  .footer-image {
    max-height: 6.75rem;
    width: auto;
  }
}

.footer {
  margin-top: var(--space-12);
}
// Unconditional (not inside any max-width media query, unlike the two
// #app .footer-image overrides below) -- desktop (>1023px) previously had
// no sizing rule for these at all, leaving each logo's size entirely up to
// the browser's intrinsic-size fallback. cmr.png has real pixel dimensions
// so that fallback always resolved fine; the QUT SVG had no width/height
// attribute of its own (only a viewBox), so its size was ambiguous and
// resolved inconsistently between reloads -- sometimes rendering at a
// sensible size, sometimes collapsing to ~0 and appearing to vanish. Fixed
// on both ends: the SVG now declares real width/height (see
// assets/QUT_SQUARE_RGB_SVG.svg), and this gives every screen size an
// explicit fallback regardless.
.footer-image {
  max-height: 6.75rem;
  width: auto;
}
// Compound selector (.column.footer-logos), not just .footer-logos -- Bulma's
// own `.column { display: block; }` is the same specificity as a bare
// `.footer-logos { display: flex; }` would be, so whichever stylesheet
// happened to load later in the bundle was silently winning and collapsing
// this back to block-stacked (that's what was still happening: the two
// logos stacking, left-aligned like default block flow, instead of the
// flex row below). Pairing both classes on one selector outranks Bulma's
// single-class rule regardless of load order.
.column.footer-logos {
  // Both logos sit in one column and are laid out with flex here instead of
  // as two separate Bulma .columns -- Bulma's grid stacks columns vertically
  // below 769px by default, which put one logo per row on phones.
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-6);
}

.route-content {
  /* Every route fully remounts on navigation (see the router-view key
     above), and most pages fetch their data async with little/no static
     content to show while waiting. Without a floor here, the footer
     visibly jumps up to fill that gap right after navigating and then
     jumps back down once the new page's data loads. */
  position: relative;
  /* Establishes route-content's own stacking context, so the backdrop
     image's z-index: -1 resolves *within it* (painting above this
     background, below the router-view content) instead of escaping to
     whatever ancestor stacking context is next up -- without this, adding
     an opaque background below risked painting behind the backdrop image
     entirely, which would have silently broken the loading backdrop. */
  z-index: 0;
  min-height: 60vh;
  /* Explicit, not inherited from body's near-white Bulma default -- every
     page except Home should sit on genuine white regardless of what the
     loading-state JS is doing. */
  background: #fff;
}
.route-content-image {
  /* Only in the DOM while pageLoadingState.isLoading is true (see
     src/store/pageLoading.ts) -- shown for the "waiting page" moment right
     after navigating, removed again once the new view's created() hook
     confirms its own content is actually ready. Every other page stays
     plain white behind its own content, as intended. */
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 30%;
  filter: contrast(1.3) saturate(1.4) brightness(0.96);
  z-index: -1;
}

.sticky-pull-tab {
  appearance: none;
  position: fixed;
  top: 50vh;
  right: 0;
  z-index: var(--z-sticky-tab);
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
  transition: background 0.2s var(--ease-spring);
}
.sticky-pull-tab:focus-visible,
.sticky-close-tab:focus-visible,
.sticky-keys-toggle:focus-visible {
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
  z-index: var(--z-sticky-nav);
  background: rgba(255, 255, 255, 1);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.07);
  box-shadow: var(--shadow-md);
  padding: 0.9rem 3.5rem 0.7rem;
  transform: translateY(-110%);
  transition: transform 0.35s var(--ease-spring);
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
/* .sticky-logos-group wraps the Sandpiper logo + .sticky-logos-right so the
   three logos can be forced onto one shared centered line on mobile (see the
   768px override below) without changing this file's separate desktop
   layout -- `display: contents` here makes the wrapper invisible to the flex
   context, so its two children (.sticky-logo-left, .sticky-logos-right)
   participate directly as .sticky-bar-row's own flex items. The explicit
   `order` values below (unset elsewhere at this breakpoint) exist purely to
   keep that pre-restructure visual order -- Previous, Sandpiper logo, search
   field, CMR/QUT -- now that Sandpiper logo's DOM position moved next to
   .sticky-logos-right instead of sitting right after Previous. */
.sticky-logos-group {
  display: contents;
}
.sticky-prev-btn {
  order: 0;
}
.sticky-logo-left {
  order: 1;
}
.sticky-input-col {
  order: 2;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
}
.sticky-field-grow {
  margin-bottom: 0 !important;
}
/* Ghost-text autocomplete overlay + suggestion dropdown, shared visual
   structure with Search.vue's copy but colored for the sticky bar's dark
   background. Overlay font/padding is copied at runtime from the real
   input (sync_sticky_ghost_overlay_style) rather than guessed here. */
.sticky-input-col .search-autocomplete-wrap {
  position: relative;
  flex: 1;
  min-width: 0;
}
.sticky-input-col .search-ghost-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  white-space: pre;
  overflow: hidden;
}
.sticky-input-col .search-ghost-typed {
  visibility: hidden;
}
.sticky-input-col .search-ghost-suffix {
  color: rgba(255, 255, 255, 0.4);
}
.sticky-input-col .search-suggest-dropdown {
  position: absolute;
  left: 0;
  right: auto;
  /* As wide as the longest suggestion (never narrower than the input), so
     values aren't cut off; anything past the cap wraps instead. */
  min-width: 100%;
  width: max-content;
  max-width: min(40rem, calc(100vw - 2rem));
  top: 100%;
  margin-top: 0.25rem;
  background: #26282c;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
  max-height: 280px;
  overflow-y: auto;
  z-index: 30;
  list-style: none;
  padding: 0.25rem 0;
  margin-left: 0;
}
.sticky-input-col .search-suggest-dropdown li {
  padding: 0.4rem 0.75rem;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.85);
  cursor: pointer;
  white-space: normal;
  overflow-wrap: anywhere;
}
.sticky-input-col .search-suggest-dropdown li.is-active,
.sticky-input-col .search-suggest-dropdown li:hover {
  background: rgba(255, 255, 255, 0.12);
}
.sticky-sub-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.2rem;
}
.sticky-logos-right {
  order: 3;
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
  z-index: var(--z-sticky-close);
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
  transition: background 0.2s var(--ease-spring);
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
/* Matches Search.vue's redesigned "List of keys" / "Advanced options"
   toggles: plain text + chevron, no pill/button chrome, and a teal-tinted
   card for the expanded content instead of the old frosted grey box. */
.sticky-keys-toggle {
  appearance: none;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 0;
  border-bottom: 1px solid transparent;
  padding: 0;
  background: transparent;
  color: hsl(174, 62%, 26%);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
  transition: border-color 220ms var(--ease-spring), color 220ms var(--ease-spring);
}
.sticky-keys-toggle:hover {
  border-bottom-color: currentColor;
}
.disclosure-chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 300ms var(--ease-spring);
}
.sticky-keys-toggle.is-open .disclosure-chevron {
  transform: rotate(180deg);
}
.sticky-keys-panel {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.35s var(--ease-spring);
}
.sticky-keys-panel.is-open {
  max-height: 650px;
}
.sticky-syntax-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  margin-top: var(--space-1);
  background: hsl(174, 30%, 95%);
}
.sticky-syntax-title {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: hsl(174, 40%, 38%);
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
  color: hsl(174, 55%, 30%);
  font-weight: 600;
  margin-right: 0.2rem;
}
.sticky-example-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-4) var(--space-3);
  background: hsl(174, 30%, 95%);
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
  background: hsl(174, 25%, 98.5%);
  border: 1px solid hsl(174, 25%, 91%);
  border-radius: 12px;
  margin-top: var(--space-2);
  overflow: hidden;
}
.sticky-keys-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4) var(--space-6);
  padding: var(--space-4) var(--space-4) var(--space-2);
}
.sticky-keys-grid code {
  color: hsl(174, 55%, 30%);
}
.keys-group {
  min-width: 150px;
  flex: 1;
}
.keys-group-title {
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: hsl(174, 62%, 24%);
  border-bottom: 2px solid hsl(174, 45%, 85%);
  padding-bottom: var(--space-1);
  margin-bottom: var(--space-2);
}
.keys-item {
  font-size: 0.78rem;
  margin-bottom: 0.15rem;
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
}
.keys-example {
  color: #a3a3a3;
  font-size: 0.75rem;
  padding-left: 0.25rem;
}
.sticky-keys-left {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}
/* Bulma's is-light gives a permanent grey fill/border via a .button.is-light
   compound selector that ties or beats this scoped single-class selector on
   specificity -- !important forces the override regardless of cascade
   order, same precedent as .sticky-prev-btn's positioning above. Invisible
   at rest, the grey rectangle only appears on hover/focus. */
.sticky-random-button {
  background: transparent !important;
  border-color: transparent !important;
  box-shadow: none !important;
}
.sticky-random-button:hover,
.sticky-random-button:focus-visible {
  background: hsl(0, 0%, 92%) !important;
  border-color: hsl(0, 0%, 92%) !important;
}
.keys-item-label {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
}
.keys-any-btn {
  appearance: none;
  border: 1px solid hsl(174, 45%, 70%);
  background: transparent;
  color: hsl(174, 55%, 30%);
  font: inherit;
  font-size: 0.68rem;
  font-weight: 600;
  line-height: 1;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}
.keys-any-btn:hover {
  background: hsl(174, 45%, 92%);
  border-color: hsl(174, 45%, 55%);
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
  z-index: var(--z-tooltip);
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
.tooltip-hint {
  text-transform: none;
  font-weight: 400;
  letter-spacing: normal;
  color: rgba(255, 255, 255, 0.35);
}
.sticky-tooltip-grid.is-clickable span {
  cursor: pointer;
  transition: background-color 120ms ease, color 120ms ease;
}
.sticky-tooltip-grid.is-clickable span:hover,
.sticky-tooltip-grid.is-clickable span:focus-visible {
  background: rgba(255, 255, 255, 0.28);
  color: #fff;
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
  #app .footer {
    padding: 2rem 1rem;
  }
  #app .footer-image {
    display: block;
    width: auto;
    height: auto;
    max-height: 4.5rem;
    // Not `margin: 0 auto` -- flexbox resolves left/right auto margins as
    // flexible space, which would fight .footer-logos' own `gap` +
    // `justify-content: center` and push the two logos apart instead of
    // keeping them side by side.
    margin: 0;
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
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 3rem 0.75rem 0.75rem;
  }
  .sticky-bar-row {
    position: relative;
    flex-wrap: wrap;
    gap: 0.4rem;
    align-items: center;
    // Room for .sticky-prev-btn, which is pulled out of flex flow entirely
    // (see below) and overlaid on top instead -- padding-left reserves its
    // 44px + gap so the search field doesn't render underneath it.
    padding-left: 52px;
  }
  // Pulled out of the flex row and absolutely positioned in the top-left
  // corner instead of trying to keep it flex-shrinking to fit alongside
  // the search field -- that depends on Buefy's field/control/input nested
  // flex contexts all correctly reporting min-width:0, which turned out to
  // be unreliable in practice. An absolutely positioned 44px corner button
  // (the same pattern .sticky-close-tab/.sticky-pull-tab already use in
  // this file) is deterministic regardless of how the row's content sizes.
  // !important on the position/offset properties: proven necessary by a
  // direct test (a version without !important visibly regressed to the old
  // un-positioned layout) -- same precedent as .sticky-info-tooltip's
  // left/top below. The exact competing rule wasn't pinned down, but the
  // effect is reproducible.
  .sticky-prev-btn {
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    z-index: 1 !important;
    min-width: 44px !important;
    width: 44px !important;
    height: 44px !important;
    padding: 0 !important;
    justify-content: center;
  }
  .sticky-prev-label {
    display: none;
  }
  .sticky-input-col {
    order: 1;
    flex: 1 1 0%;
    width: auto;
    min-width: 0;
  }
  /* min-width:0 on .sticky-input-col alone isn't enough -- Buefy's field/
     field-body/control wrapping around the search input is itself nested
     flex contexts (exact structure/breakpoints are Buefy internals, not
     worth pinning to), and every one of those defaults to min-width:auto
     (refuses to shrink below its content's intrinsic width) unless told
     otherwise. That intrinsic width was propagating all the way up, forcing
     the whole input column (and so Previous, which shares its line) to wrap
     onto its own line instead of shrinking to fit next to Previous. Reset
     every descendant rather than targeting specific Buefy classes, since
     nothing in here has a legitimate reason to resist shrinking. */
  .sticky-field-grow,
  .sticky-field-grow * {
    min-width: 0;
  }
  .sticky-field-grow .input {
    width: 100%;
  }
  .sticky-input-col .button {
    padding: 0 0.55rem;
    font-size: 0.78rem;
    white-space: nowrap;
  }
  .sticky-logos-group {
    // .sticky-logos-group is `display: contents` by default (see the base
    // rule above) so Sandpiper logo + .sticky-logos-right act as separate
    // .sticky-bar-row flex items on desktop. Only here, on phones, does it
    // become a real flex item itself -- flex-basis 100% forces it onto its
    // own line after row 1, and this internal flex context is what actually
    // groups + centers all three logos as one row.
    //
    // `.sticky-bar-row`'s 52px padding-left (below) exists only to reserve
    // room for `.sticky-prev-btn`, which is absolutely positioned in the
    // top-left corner on row 1 -- but that padding applies to the whole row,
    // including this group once it wraps onto its own line 2, where there's
    // no Previous button to avoid. Left uncorrected, `justify-content:
    // center` only centers the three logos *within* a box that's itself
    // already shifted 52px right of the row's true left edge, so the whole
    // cluster (and the Sandpiper logo, being its leftmost member) visibly
    // drifts right of centre. `flex-basis: calc(100% + 52px)` + `margin-left:
    // -52px` grows this item back out to the row's full unpadded width and
    // realigns its left edge to x=0, so centering happens against the same
    // width the row's own horizontal padding is already centered within.
    display: flex;
    order: 2;
    flex: 1 0 calc(100% + 52px);
    margin-left: -52px;
    justify-content: center;
    align-items: center;
    gap: 0.75rem;
  }
  .sticky-logo-left {
    order: initial;
    height: 36px;
    max-width: 110px;
  }
  .sticky-logos-right {
    // Overrides the 1023px breakpoint's `display: none` -- these logos
    // should still appear on phones.
    order: initial;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.75rem;
    margin-left: 0;
  }
  .sticky-logo {
    height: 32px;
    max-width: 100px;
  }
  .sticky-close-tab {
    // Compact bar (keys closed) is short enough to fit without scrolling,
    // so there's no need for a viewport-fixed button here -- settle into
    // normal flow right after the logo row instead, same reasoning as the
    // .is-keys-open sticky variant below (which needs it for the genuinely
    // long, scrollable keys list). Fixed positioning independent of content
    // height was what let this sit on top of the logo row in the first
    // place.
    position: static;
    display: flex;
    justify-content: center;
    width: fit-content;
    margin: 0.5rem auto 0;
    min-width: 44px;
    min-height: 44px;
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 999px;
    padding: 0.65rem 0.9rem;
  }
  // With the keys list expanded, a viewport-fixed close button sits at a
  // constant screen spot regardless of scroll -- which means whatever
  // list content happens to scroll underneath it gets covered ("stuck at
  // habitat"). Switching to `sticky` puts it back in normal flow as the
  // last child of .sticky-search-bar: it still clings to the bottom of
  // the visible scroll area while there's panel content still below the
  // fold (so it moves along with the user's scroll), but once scrolling
  // reaches the true end of that content, sticky has nowhere further to
  // pin to and the button settles into its natural resting spot right
  // after the last item -- no overlap, no going past the box.
  .sticky-close-tab.is-keys-open {
    position: sticky;
    bottom: 0.75rem;
    width: fit-content;
    margin-left: auto;
    margin-right: 0.75rem;
    right: auto;
  }
  .sticky-keys-panel.is-open {
    max-height: none;
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
  // .sticky-search-bar clips overflow-x on this breakpoint (see above) --
  // without wrapping, a narrow viewport would silently clip the Random
  // Search button (and eventually the run count) off the right edge
  // instead of just reflowing them onto their own line.
  .sticky-sub-row {
    flex-wrap: wrap;
    row-gap: 0.3rem;
  }
  .sticky-keys-left {
    flex-wrap: wrap;
    row-gap: 0.3rem;
  }
}

@media (max-width: 430px) {
  .keys-group {
    flex-basis: 100%;
  }
  .sticky-syntax-row,
  .sticky-example-row {
    align-items: flex-start;
    flex-direction: column;
    padding-left: var(--space-3);
    padding-right: var(--space-3);
  }
  .sticky-syntax-item {
    white-space: normal;
  }
  .sticky-example-query {
    width: 100%;
    overflow-wrap: anywhere;
  }
  .sticky-keys-grid {
    padding: var(--space-3) var(--space-3) var(--space-1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .sticky-search-bar,
  .sticky-keys-panel {
    transition: none;
  }
}
</style>
