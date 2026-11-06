<template>
  <div class="run-page">
    <div v-if="metadata !== null">
      <section class="section">
        <div class="container" v-if="metadata !== null">
          <h1 class="title run-study-title">{{ metadata.metadata_parsed.study_title }}</h1>

          <div class="run-subhead">
            <p class="subtitle run-subhead-sample">Sample {{ sample_name_mature }}</p>
            <router-link
              v-if="metadata.metadata_parsed.num_related_runs > 0"
              class="run-related-pill"
              :to="{ name: 'Project', query: { model_bioproject: metadata.metadata_parsed.bioproject }}"
            >
              <span v-if="metadata.metadata_parsed.num_related_runs == 1">1 related run</span>
              <span v-else>{{ metadata.metadata_parsed.num_related_runs }} related runs</span>
            </router-link>
          </div>

          <dl class="run-facts">
            <div class="run-fact">
              <dt>Organism</dt>
              <dd>{{ metadata.metadata_parsed.organism }}, {{ metadata.metadata_parsed.host_or_not_mature }}</dd>
            </div>
            <div class="run-fact">
              <dt>Sequencing</dt>
              <dd>{{ sequencingSummary }}</dd>
            </div>
            <div class="run-fact">
              <dt>Timeline</dt>
              <dd>
                <span v-if="metadata.metadata_parsed.collection_time !== null">Collected {{ metadata.metadata_parsed.collection_time }}, released {{ metadata.metadata_parsed.release_month }}</span>
                <span v-else>Released {{ metadata.metadata_parsed.release_month }}</span>
              </dd>
            </div>
          </dl>

          <div class="run-qc-strip">
            <div class="run-qc-meter">
              <span class="run-qc-meter-label">SPF</span>
              <span class="run-qc-meter-track">
                <span
                  class="run-qc-meter-fill"
                  :class="get_smf_category"
                  :style="{ width: Math.max(2, metadata.metadata_parsed.smf) + '%' }"
                ></span>
              </span>
              <span class="run-qc-meter-value">{{ metadata.metadata_parsed.smf }}%</span>
            </div>
            <div class="run-qc-meter">
              <span class="run-qc-meter-label">Known species</span>
              <span class="run-qc-meter-track">
                <span
                  class="run-qc-meter-fill run-qc-meter-fill-neutral"
                  :style="{ width: Math.max(2, known_species_fraction) + '%' }"
                ></span>
              </span>
              <span class="run-qc-meter-value">{{ known_species_fraction }}%</span>
            </div>
            <div class="run-qc-flags">
              <button
                v-for="flag in qc_flags"
                :key="flag.key"
                type="button"
                class="run-qc-flag"
                :class="flag.active ? flag.activeClass : flag.clearClass"
                aria-haspopup="dialog"
                :aria-expanded="qc_tooltip_key === flag.key"
                @mouseenter="showQcTooltip(flag, $event)"
                @mouseleave="hideQcTooltipDelayed"
                @focus="showQcTooltip(flag, $event)"
                @blur="hideQcTooltipDelayed"
                @keydown.esc="hideQcTooltip"
              >
                <img
                  v-if="flag.active && flag.activeImage"
                  :src="flag.activeImage"
                  class="run-qc-flag-icon-img"
                  alt=""
                />
                <b-icon v-else :icon="flag.active ? flag.activeIcon : flag.clearIcon" size="is-small" />
                {{ flag.active ? flag.activeLabel : flag.clearLabel }}
              </button>
            </div>
          </div>

          <div
            v-if="qc_tooltip_key"
            class="run-qc-tooltip"
            role="tooltip"
            :style="{ left: qc_tooltip_x + 'px', top: qc_tooltip_y + 'px' }"
            @mouseenter="keepQcTooltipOpen"
            @mouseleave="hideQcTooltipDelayed"
          >
            {{ qc_tooltip_text }}
            <span class="run-qc-tooltip-search">Search: {{ qc_tooltip_key }}:yes / {{ qc_tooltip_key }}:no</span>
          </div>

          <div class="run-abstract">
            <p class="run-abstract-label">Abstract</p>
            <p class="has-text-justified">{{ metadata.metadata_parsed.study_abstract }}</p>
          </div>

          <div class="run-links-card">
            <div class="run-links-section">
              <p class="run-abstract-label">Identifiers</p>
              <div class="run-link-pills">
                <a :href="bioproject_url" class="run-link-pill">
                  <b-icon icon="link-variant" size="is-small" />
                  BioProject {{ metadata.metadata_parsed.bioproject }}
                </a>
                <a :href="'http://www.ncbi.nlm.nih.gov/sra?term=' + accession" class="run-link-pill">
                  <b-icon icon="link-variant" size="is-small" />
                  SRA {{ accession }}
                </a>
              </div>
            </div>

            <div class="run-links-section">
              <p class="run-abstract-label">Publications</p>
              <p v-if="publications.length===0" class="run-links-note">
                No linked publications recorded. A <a :href="scholar_search_url">search on Google Scholar</a> may find some.
              </p>
              <template v-else>
                <div class="run-link-pills">
                  <a
                    v-for="link in publications"
                    :key="link.study_id"
                    :href="publicationHref(link)"
                    class="run-link-pill"
                  >
                    <span class="run-link-pill-badge">{{ publicationBadge(link) }}</span>
                    {{ link.study_id }}
                  </a>
                </div>
                <p class="run-links-note">A <a :href="scholar_search_url">search on Google Scholar</a> may find further publications.</p>
              </template>
            </div>

            <div v-if="non_publication_study_links.length>0" class="run-links-section">
              <p class="run-abstract-label">Other databases</p>
              <div class="run-link-pills">
                <a v-for="link in non_publication_study_links" :key="link.label" :href="link.url" class="run-link-pill">
                  <b-icon icon="link-variant" size="is-small" />
                  {{ link.label }}
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      <nav class="section run-jump-bar" aria-label="On this page">
        <p class="run-jump-title">On this page</p>
        <div class="container run-jump-links">
          <a
            v-for="item in JUMP_ITEMS"
            :key="item.id"
            :href="'#' + item.id"
            :class="{ 'is-current': current_section === item.id, 'is-group-start': item.start }"
            :aria-current="current_section === item.id ? 'location' : null"
            @click.prevent="jumpTo(item.id)">{{ item.label }}</a>
        </div>
      </nav>

      <section id="taxonomic-profile" class="section">
        <div class="container">
          <h3 class="title">Taxonomic profile</h3>
          <b-field class="taxonomy-selector">
            <b-radio-button name="taxonomy-db" v-model="taxonomy_db" native-value="gtdb" @input="fetchCondensed" type="is-info">
              GTDB ({{ GTDB_VERSION }})
            </b-radio-button>
            <b-radio-button name="taxonomy-db" v-model="taxonomy_db" native-value="globdb" @input="fetchCondensed" type="is-warning" :disabled="db_availability.globdb === false">
              GlobDB ({{ GLOBDB_VERSION }})<span v-if="db_availability.globdb === false"> - unavailable</span>
            </b-radio-button>
          </b-field>
          <div>
            <template v-if="condensed_tree != null">
              <Sunburst3 :json_tree="sunburst_tree" :overall_coverage="10.3" :known_species_fraction="known_species_fraction" root_label="Prokaryotes" scope_note="Shows bacteria and archaea only. Viruses and eukaryotes are not profiled." />
            </template>
          </div>
        </div>
      </section>

      <section id="prokaryotic-fraction" class="section">
        <div class="container">
          <h3 class="title">Prokaryotic fraction</h3>
          <div v-if="metadata.metadata_parsed.smf || metadata.metadata_parsed.smf==0">
            <br />
            <br />
            <b-progress :value="Math.max(0.5, metadata.metadata_parsed.smf)" :max="100" :type=get_smf_category size="is-medium"  />
            <p><span v-if="metadata.metadata_parsed.smf_warning">Warning!</span> SingleM Prokaryotic Fraction (<a href="https://wwood.github.io/singlem/tools/prokaryotic_fraction">SPF</a>) estimated that {{ metadata.metadata_parsed.smf }}% of the reads in this metagenome are bacterial or archaeal.
            <span v-if="metadata.metadata_parsed.smf_warning">However, this community has dominating lineages which are not known to the species level, so the estimate is less reliable.</span></p>
            <br />
            <p>If the non-prokaryotic DNA is from a sequenced genome, <a :href="'https://trace.ncbi.nlm.nih.gov/Traces/?view=run_browser&acc='+accession+'&display=analysis'">NCBI STAT</a> may provide some insight into its source(s).</p>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container is-large">
          <RunMetadata :mdata="metadata.metadata" :mdata_parsed="metadata.metadata_parsed" :accession="accession" />
        </div>
      </section>

      <section id="download" class="section">
        <div class="container is-large">
          <h3 class="title">Download</h3>

          <p>
            The taxonomic profile of this sample can be downloaded in tab-separated "SingleM condensed with extras" format, generated with <a :href="profile_csv_with_extras_link_gtdb">GTDB ({{ GTDB_VERSION }})</a> or <a :href="profile_csv_with_extras_link_globdb">GlobDB ({{ GLOBDB_VERSION }})</a> taxonomy. This details the coverage assigned to each taxon at each taxonomic level, both <a href="https://wwood.github.io/singlem/Glossary">filled and unfilled</a>, plus the relative abundance of each taxon.</p>
          <br />

          <p>Concise "SingleM condensed" format files with three columns sample name, coverage, and taxonomy are also available for download (<a :href="profile_csv_link_gtdb">GTDB ({{ GTDB_VERSION }})</a> or <a :href="profile_csv_link_globdb">GlobDB ({{ GLOBDB_VERSION }})</a>). In this format the coverage of each lineage is the coverage assigned to that taxon and not more specifically e.g. the coverage of a species is not included in the coverage shown for its genus. These taxonomic profiles can be converted to other forms (e.g. one that gives the relative abundance instead of the coverage) using the <a href="https://wwood.github.io/singlem/tools/summarise">SingleM summarise</a> tool.</p>
          <br />

          <p>Unfortunately, for now, the full SingleM OTU table of {{ accession }} (GTDB ({{ GTDB_VERSION }}) annotated) tab-separated file containing information about each OTU from each marker cannot be downloaded directly from this website.</p>
        </div>
      </section>
    </div>

    <div v-else>
      <div v-if="error_message !== null">
        <section class="section container">
          <b-message 
            title="Error" 
            type="is-warning" 
            :closable="false"
            has-icon>
            <p>ERROR {{ error_message }}</p>
          </b-message>
        </section>
      </div>

      <div v-else>
        <section class="section container">
          Searching ..
        </section>
      </div>
    </div>

  </div>
</template>

<script>

/* eslint-disable vue/no-unused-components */
// The jump bar's sections, in page order; each id is on that section's element.
// `start` opens a new group: the profile, the NCBI metadata, then data from elsewhere.
const JUMP_ITEMS = [
  { id: 'taxonomic-profile', label: 'Taxonomic profile' },
  { id: 'prokaryotic-fraction', label: 'Prokaryotic fraction' },
  { id: 'submitter-information', label: 'Submitter', start: true },
  { id: 'sample-information', label: 'Sample information' },
  { id: 'sequencing-information', label: 'Sequencing' },
  { id: 'derived-information', label: 'Derived' },
  { id: 'other-identifiers', label: 'Identifiers' },
  { id: 'study-links', label: 'Study links' },
  { id: 'indicpiper', label: 'IndicPiper', start: true },
  { id: 'download', label: 'Download', start: true }
]

const JUMP_LINE_FRACTION = 0.33
const PIN_RELEASE_EVENTS = ['wheel', 'touchmove', 'keydown']

import Sunburst3 from '@/components/Sunburst3.vue'
import RunMetadata from '@/components/RunMetadata.vue'
import RunMetadataTable from '@/components/RunMetadataTable.vue'
import { LMap, LTileLayer, LMarker } from '@vue-leaflet/vue-leaflet'

import { api_url, fetchRunMetadata, fetchRunCondensed } from '@/api'
import { GTDB_VERSION, GLOBDB_VERSION } from '@/versions'
import { stopPageLoading, currentLoadingToken } from '@/store/pageLoading'
import rnaIcon from '@/assets/RNA-white.png'

export default {
  name: 'Run',
  title () {
    return `Run ${this.accession} - Sandpiper`
  },
  data: function () {
    return {
      JUMP_ITEMS,
      current_section: null,
      pinned_section: null,
      GTDB_VERSION,
      GLOBDB_VERSION,
      condensed_tree: null,
      condensed_cache: {},
      db_availability: { gtdb: null, globdb: null },
      metadata: null,
      error_message: null,
      taxonomy_db: 'gtdb',
      qc_tooltip_key: null,
      qc_tooltip_text: '',
      qc_tooltip_x: 0,
      qc_tooltip_y: 0,
      qc_tooltip_close_timer: null
    }
  },
  props: ['accession'],
  components: {
    Sunburst3,
    RunMetadata,
    RunMetadataTable,
    LMap,
    LTileLayer,
    LMarker
  },
  computed: {
    bioproject_url: function () {
      return 'https://www.ncbi.nlm.nih.gov/bioproject/' + this.metadata.metadata_parsed.bioproject
    },
    scholar_search_url: function () {
      // Unclear whether including accession helps. 
      return 'https://scholar.google.com/scholar?q=' + this.metadata.metadata_parsed.bioproject + ' OR ' + this.accession
    },
    getNumReads: function () {
      return Math.round(this.metadata.metadata_parsed.spots / 1e6)
    },
    sequencingSummary: function () {
      const parsed = this.metadata.metadata_parsed
      const parts = [
        (parsed.mbases / 1000) + ' Gbp',
        this.getNumReads === 0 ? '<1M reads' : this.getNumReads + 'M reads',
      ]
      if (parsed.read_length_summary !== null) {
        parts.push(parsed.read_length_summary)
      }
      if (parsed.instrument) {
        parts.push(parsed.instrument)
      }
      return parts.join(' · ')
    },
    sunburst_tree: function () {
      return this.condensed_tree.condensed
    },
    known_species_fraction: function () {
      return this.taxonomy_db === 'gtdb'
        ? this.metadata.metadata_parsed.known_species_fraction
        : this.metadata.metadata_parsed.globdb_known_species_fraction
    },
    sample_name_mature: function () {
      return this.metadata.metadata_parsed.sample_name
      // if (this.metadata.metadata_parsed.sample_name_sam !== null) {
      //   return this.metadata.metadata.sample_name_sam
      // } else {
      //   return this.metadata.metadata.sample_name
      // }
    },
    profile_csv_link_gtdb: function () {
      return api_url() + '/condensed_csv/' + this.accession + '?taxonomy_type=gtdb'
    },
    profile_csv_link_globdb: function () {
      return api_url() + '/condensed_csv/' + this.accession + '?taxonomy_type=globdb'
    },
    profile_csv_with_extras_link_gtdb: function () {
      return api_url() + '/condensed_csv_with_extras/' + this.accession + '?taxonomy_type=gtdb'
    },
    profile_csv_with_extras_link_globdb: function () {
      return api_url() + '/condensed_csv_with_extras/' + this.accession + '?taxonomy_type=globdb'
    },
    publications: function () {
      return this.metadata.metadata.study_links.filter(function (link) {
        return (typeof link['database'] !== 'undefined')
      })
    },
    non_publication_study_links: function () {
      return this.metadata.metadata.study_links.filter(function (link) {
        return (typeof link['label'] !== 'undefined')
      })
    },
    get_smf_category: function () {
      if (this.metadata.metadata_parsed.smf_warning === true) {
        return '' // i.e. grey
      } else if (this.metadata.metadata_parsed.smf < 40) {
        return 'is-danger'
      } else if (this.metadata.metadata_parsed.smf < 80) {
        return 'is-warning'
      } else {
        return 'is-success'
      }
    },
    // Low complexity is a genuine pass/fail QC judgment, so it keeps the
    // red/green + flag/tick treatment. The other three are categorical
    // facts, not good/bad verdicts -- e.g. a sample being RNA rather than
    // DNA is information some users are specifically looking for, not a
    // problem. Each of those three gets its own two-color theme (distinct
    // from each other and from the red/green pair) so no color implies a
    // judgment, plus an icon pair that describes the category rather than
    // flagging/confirming it.
    qc_flags: function () {
      const p = this.metadata.metadata_parsed
      return [
        {
          key: 'low_complexity',
          active: p.low_complexity,
          activeLabel: 'Low complexity',
          clearLabel: 'Complex',
          activeHint: 'Samples where ≥95% of the community is assigned to a single order are flagged as low complexity.',
          clearHint: 'Less than 95% of this sample’s community is assigned to a single order.',
          activeIcon: 'flag-variant',
          clearIcon: 'check-circle-outline',
          activeClass: 'run-qc-flag-active',
          clearClass: 'run-qc-flag-clear'
        },
        {
          key: 'non_metagenome_organism',
          active: p.non_metagenome_organism_strict,
          activeLabel: 'Non-metagenome organism',
          clearLabel: 'Metagenome organism',
          activeHint: 'This sample appears to be a single organism, not a genuine metagenome.',
          clearHint: 'This sample appears to be a genuine metagenome, not a single organism.',
          activeIcon: 'account',
          clearIcon: 'account-group',
          activeClass: 'run-qc-flag-organism-single',
          clearClass: 'run-qc-flag-organism-metagenome'
        },
        {
          key: 'synthetic',
          active: p.synthetic,
          activeLabel: 'Synthetic',
          clearLabel: 'Natural',
          activeHint: 'This sample’s reads appear synthetic (e.g. simulated or a mock community), not a real environmental sample.',
          clearHint: 'This sample’s reads do not appear synthetic.',
          activeIcon: 'flask-outline',
          clearIcon: 'leaf',
          activeClass: 'run-qc-flag-synthetic',
          clearClass: 'run-qc-flag-natural'
        },
        {
          key: 'rna_or_non_dna',
          active: p.rna_or_non_dna_strict,
          activeLabel: 'RNA/non-DNA',
          clearLabel: 'DNA',
          activeHint: 'This sample’s reads appear to be RNA or otherwise non-DNA sequencing.',
          clearHint: 'This sample’s reads appear to be standard DNA sequencing.',
          activeImage: rnaIcon,
          clearIcon: 'dna',
          activeClass: 'run-qc-flag-rna',
          clearClass: 'run-qc-flag-dna'
        }
      ]
    }
  },
  created () {
    // fetch the data when the view is created and the data is
    // already being observed
    this.fetchData()
  },
  methods: {
    jumpTo: function (id) {
      const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      // A section near the page end can't scroll up to the top, so hold the click's
      // choice as current until the reader scrolls by hand.
      this.pinned_section = id
      this.current_section = id
      document.getElementById(id)?.scrollIntoView({ behavior: still ? 'auto' : 'smooth', block: 'start' })
    },
    // The current section is the last one whose top has passed a line a third of
    // the way down the window. At the very bottom of the page the last section
    // takes over, unless a jump-bar click pinned another one.
    updateCurrentSection: function () {
      if (this.pinned_section) return
      const line = window.innerHeight * JUMP_LINE_FRACTION
      let current = null
      JUMP_ITEMS.forEach(item => {
        const el = document.getElementById(item.id)
        if (el && el.getBoundingClientRect().top <= line) current = item.id
      })
      const atEnd = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2
      if (atEnd) current = JUMP_ITEMS[JUMP_ITEMS.length - 1].id
      if (current) this.current_section = current
    },
    releasePin: function () {
      if (this.pinned_section) {
        this.pinned_section = null
        this.updateCurrentSection()
      }
    },
    observeSections: function () {
      this.unobserveSections()
      window.addEventListener('scroll', this.updateCurrentSection, { passive: true })
      window.addEventListener('resize', this.updateCurrentSection, { passive: true })
      // Hand input (not the smooth scroll a click starts) releases the pin.
      PIN_RELEASE_EVENTS.forEach(ev => window.addEventListener(ev, this.releasePin, { passive: true }))
      this.updateCurrentSection()
    },
    unobserveSections: function () {
      window.removeEventListener('scroll', this.updateCurrentSection)
      window.removeEventListener('resize', this.updateCurrentSection)
      PIN_RELEASE_EVENTS.forEach(ev => window.removeEventListener(ev, this.releasePin))
    },
    // Same fixed-position, hover/focus-driven popover pattern as
    // Search.vue's advanced-search field tooltips (.info-tooltip-box /
    // showTooltip), scaled down for a single short sentence instead of a
    // multi-column value grid -- no per-tooltip height table or
    // viewport-bottom flip needed since the QC strip sits near the top of
    // the page and the box is always small.
    showQcTooltip (flag, event) {
      clearTimeout(this.qc_tooltip_close_timer)
      const rect = event.currentTarget.getBoundingClientRect()
      const tooltipW = 260
      let x = rect.left
      if (x + tooltipW > window.innerWidth - 10) {
        x = window.innerWidth - tooltipW - 10
      }
      this.qc_tooltip_x = Math.max(10, x)
      this.qc_tooltip_y = rect.bottom + 8
      this.qc_tooltip_key = flag.key
      this.qc_tooltip_text = flag.active ? flag.activeHint : flag.clearHint
    },
    hideQcTooltipDelayed () {
      clearTimeout(this.qc_tooltip_close_timer)
      this.qc_tooltip_close_timer = setTimeout(() => {
        this.qc_tooltip_key = null
      }, 200)
    },
    keepQcTooltipOpen () {
      clearTimeout(this.qc_tooltip_close_timer)
    },
    hideQcTooltip () {
      clearTimeout(this.qc_tooltip_close_timer)
      this.qc_tooltip_key = null
    },
    fetchCondensed (explicitTaxonomy) {
      const accession = this.accession
      const taxonomy = explicitTaxonomy || this.taxonomy_db

      if (this.condensed_cache[taxonomy] !== undefined) {
        if (taxonomy === this.taxonomy_db) {
          this.condensed_tree = this.condensed_cache[taxonomy]
        }
        return
      }

      fetchRunCondensed(accession, taxonomy)
        .then(response => {
          if (response.data.no_data) {
            this.db_availability = { ...this.db_availability, [taxonomy]: false }
            this.condensed_cache[taxonomy] = null
            if (taxonomy === this.taxonomy_db) {
              this.taxonomy_db = 'gtdb'
              this.condensed_tree = this.condensed_cache['gtdb'] || null
            }
          } else {
            this.db_availability = { ...this.db_availability, [taxonomy]: true }
            this.condensed_cache[taxonomy] = response.data
            if (taxonomy === this.taxonomy_db) {
              this.condensed_tree = response.data
            }
          }
        })
    },
    fetchData () {
      const accession = this.accession

      this.condensed_cache = {}
      this.condensed_tree = null
      this.db_availability = { gtdb: null, globdb: null }

      this.fetchCondensed('gtdb')
      this.fetchCondensed('globdb')

      // Captured now, not read lazily inside .finally() -- see
      // src/store/pageLoading.ts for why a stale token must not clear a
      // newer navigation's loading state.
      const loadingToken = currentLoadingToken()
      fetchRunMetadata(accession)
        .then(response => {
          if (response.data.error !== undefined) {
            this.error_message = response.data.error
          } else {
            this.metadata = response.data
          }
        })
        // The template gates on metadata/error_message, so the page is
        // genuinely blank until this settles either way.
        .finally(() => stopPageLoading(loadingToken))
    },
    publicationHref (link) {
      const db = link['database'].toLowerCase()
      if (db === 'pubmed') return 'https://www.ncbi.nlm.nih.gov/pubmed?term=' + link['study_id']
      if (db === 'doi') return 'https://doi.org/' + link['study_id']
      return null
    },
    publicationBadge (link) {
      const db = link['database'].toLowerCase()
      if (db === 'pubmed') return 'PubMed'
      if (db === 'doi') return 'DOI'
      return link['database']
    }
  },
  watch: {
    // call again the method if the route changes
    $route: 'fetchData',
    taxonomy_db: 'fetchCondensed',
    // The sections only exist once the run's metadata has loaded.
    metadata: function () {
      this.$nextTick(this.observeSections)
    }
  },
  beforeUnmount () {
    this.unobserveSections()
  }
}
</script>

<style scoped>
/* Under the study header, "On this page" is a strip above the sections. On very
   wide screens it moves into the empty space left of the centred content and stays
   in view as the page scrolls, so the content itself never shifts. */
.run-jump-bar {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-rule);
}
.run-page .run-jump-bar.section {
  padding-top: 0;
  padding-bottom: 0;
}
.run-jump-title {
  display: none;
}
.run-jump-links {
  display: flex;
  gap: var(--space-6);
  overflow-x: auto;
  white-space: nowrap;
  scrollbar-width: none;
}
.run-jump-links::-webkit-scrollbar {
  display: none;
}
.run-jump-bar a {
  position: relative;
  flex: none;
  padding: var(--space-3) 0;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-ink-muted);
  text-decoration: none;
  transition: color 0.15s;
}
/* The current section is marked in the accent, drawn in from the start. */
.run-jump-bar a::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  background: var(--color-accent);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.2s var(--ease-spring);
}
/* A hairline in the gap before each new group of sections. */
.run-jump-bar a.is-group-start::before {
  content: '';
  position: absolute;
  left: calc(-1 * var(--space-3));
  top: 30%;
  bottom: 30%;
  width: 1px;
  background: var(--color-rule);
}
.run-jump-bar a:hover,
.run-jump-bar a.is-current {
  color: var(--color-ink);
}
.run-jump-bar a.is-current::after {
  transform: scaleX(1);
}
.run-jump-bar a:active {
  color: var(--color-accent-strong);
}
.run-jump-bar a:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: 2px;
}

@media (min-width: 1440px) {
  /* Content is capped at 1152px (Bulma's widescreen width) so the list fits beside it
     on laptop screens; wider screens just get wider gutters. */
  .run-page :deep(.container:not(.run-jump-links)) {
    max-width: 1152px;
  }
  .run-jump-bar {
    /* Pinned to the window's left edge at a fixed width: as the window narrows, the
       space between the list and the content shrinks, and the list never moves.
       The 1440px breakpoint is where that space is still about 1.5rem. */
    position: fixed;
    top: 8rem;
    z-index: 100;
    left: 1rem;
    width: 6.5rem;
    background: none;
    border: 0;
  }
  .run-page .run-jump-bar.section {
    padding: 0;
  }
  .run-jump-bar .container {
    max-width: none;
    margin: 0;
  }
  .run-jump-title {
    display: block;
    margin-bottom: var(--space-2);
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--color-ink);
  }
  .run-jump-links {
    flex-direction: column;
    gap: 0;
    overflow: visible;
    white-space: normal;
    border-left: 1px solid var(--color-rule);
  }
  .run-jump-bar a {
    padding: var(--space-1) 0 var(--space-1) var(--space-3);
    font-size: 0.82rem;
    line-height: 1.35;
  }
  .run-jump-bar a.is-group-start {
    margin-top: var(--space-3);
  }
  .run-jump-bar a.is-group-start::before {
    display: none;
  }
  /* The accent runs down the list's own hairline, beside the current section. */
  .run-jump-bar a::after {
    left: -1px;
    right: auto;
    top: 0;
    bottom: 0;
    width: 2px;
    height: auto;
    transform: scaleY(0);
    transform-origin: top;
  }
  .run-jump-bar a.is-current::after {
    transform: scaleY(1);
  }
}
@media (prefers-reduced-motion: reduce) {
  .run-jump-bar a,
  .run-jump-bar a::after {
    transition: none;
  }
}
/* A little air above a jumped-to section. */
.run-page .section[id],
.run-page :deep(.metadata-section[id]) {
  scroll-margin-top: var(--space-4);
}
.run-page,
.run-page a,
.run-study-title,
.run-links-card {
  overflow-wrap: anywhere;
}
.run-sunburst {
  max-width: 100%;
}

/* Identity: title + sample id + related-runs pill */
.run-subhead {
  display: flex;
  /* centre, not baseline, so the similarity ring's middle lines up with the
     middle of the related-runs pill and the sample id. */
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
}
/* Links to each database in the Sample information help: the same pastel
   colour as the rows they explain; hover and click go darker. */
.source-link { background-color: transparent; text-decoration: none; }
.source-link:hover, .source-link:active { text-decoration: underline; }
.source-link.src-ncbi:link, .source-link.src-ncbi:visited { color: #8fb8de; }
.source-link.src-ncbi:hover { color: #0f3f73; }
.source-link.src-ncbi:active { color: #0a2a4d; }
.source-link.src-ena:link, .source-link.src-ena:visited { color: #92c98a; }
.source-link.src-ena:hover { color: #1b5218; }
.source-link.src-ena:active { color: #113410; }
.source-link.src-ddbj:link, .source-link.src-ddbj:visited { color: #f0b86e; }
.source-link.src-ddbj:hover { color: #7a4800; }
.source-link.src-ddbj:active { color: #4d2e00; }
.source-link.src-metalog:link, .source-link.src-metalog:visited { color: #b89fd9; }
.source-link.src-metalog:hover { color: #45266f; }
.source-link.src-metalog:active { color: #2b1748; }
.run-subhead-sample {
  margin-bottom: 0 !important;
  /* Overrides app.scss's global .subtitle rule, which puts every subtitle
     in the serif display font -- the sample id is an identifier, not a
     headline, so it reads better in the body sans stack. */
  font-family: system-ui, -apple-system, "Segoe UI", "Ubuntu", "Cantarell", sans-serif;
}
/* Same purple hue as the site's $purple token (hsl(271, 100%, 71%) --
   see .keys-columns code in Search.vue), darkened for legible white text
   on a solid pill instead of the raw bright value. */
.run-related-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  background: var(--color-accent);
  color: hsl(0, 0%, 100%);
  font-size: 0.85rem;
  white-space: nowrap;
  transition: background-color 0.15s;
}
.run-related-pill:hover {
  background: var(--color-accent-strong);
}

/* Specimen facts: label-over-value pairs, not run-on prose */
.run-facts {
  display: flex;
  flex-wrap: wrap;
  /* row-gap stays var(--space-8); column-gap (the horizontal space between
     Organism/Sequencing/Timeline) is 10% more than that same
     2rem base -- 2.2rem. */
  gap: var(--space-8) 2.2rem;
  /* 10% more than var(--space-6) (1.5rem) -- widens the gap between the
     specimen facts (Organism, Sequencing, ...) and the QC strip below. */
  margin: 0 0 1.65rem;
  padding-bottom: 1.65rem;
  border-bottom: 1px solid hsl(0, 0%, 90%);
}
.run-fact {
  min-width: 0;
}
.run-fact dt {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-ink-muted);
  margin-bottom: 0.2rem;
}
.run-fact dd {
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}

/* QC status strip: meters + flag chips, separated from the facts row */
.run-qc-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-6) var(--space-8);
  margin-bottom: var(--space-6);
}
.run-qc-meter {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.run-qc-meter-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-ink-muted);
  white-space: nowrap;
}
.run-qc-meter-track {
  display: inline-block;
  width: 5rem;
  height: 0.4rem;
  border-radius: 999px;
  background: hsl(0, 0%, 92%);
  overflow: hidden;
}
.run-qc-meter-fill {
  display: block;
  height: 100%;
  background: hsl(0, 0%, 65%);
}
.run-qc-meter-fill.is-success {
  background: hsl(141, 60%, 40%);
}
.run-qc-meter-fill.is-warning {
  background: hsl(38, 95%, 50%);
}
.run-qc-meter-fill.is-danger {
  background: hsl(348, 85%, 55%);
}
.run-qc-meter-fill-neutral {
  background: hsl(174, 55%, 32%);
}
.run-qc-meter-value {
  font-variant-numeric: tabular-nums;
  font-size: 0.85rem;
  color: hsl(0, 0%, 35%);
  white-space: nowrap;
}
.run-qc-flags {
  display: flex;
  flex-wrap: wrap;
  /* row-gap stays var(--space-2); column-gap widened so the pills (Low
     complexity/Complex, Metagenome organism, Natural, DNA) sit a bit
     further apart horizontally. */
  gap: var(--space-2) 0.9rem;
}
.run-qc-flag {
  appearance: none;
  border: 0;
  margin: 0;
  font: inherit;
  cursor: help;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  font-size: 0.8rem;
  white-space: nowrap;
}
.run-qc-flag:focus-visible {
  outline: 2px solid #3273dc;
  outline-offset: 2px;
}
/* Low complexity is the one genuine pass/fail QC judgment among these
   four, so it alone keeps the red/green verdict treatment -- same green
   as .run-qc-meter-fill.is-success and same red as .is-danger above (and
   Bulma's $green/$red/is-success/is-danger used site-wide). */
.run-qc-flag-clear {
  background: hsl(141, 60%, 34%);
  color: hsl(0, 0%, 100%);
}
.run-qc-flag-active {
  background: hsl(348, 75%, 42%);
  color: hsl(0, 0%, 100%);
}
/* The remaining three flags are categorical facts, not verdicts (e.g. RNA
   vs. DNA isn't "bad" -- some users want RNA specifically), so each pair
   gets its own two-color theme instead of reusing red/green. */
.run-qc-flag-organism-single {
  background: hsl(235, 45%, 50%);
  color: hsl(0, 0%, 100%);
}
.run-qc-flag-organism-metagenome {
  background: hsl(205, 60%, 38%);
  color: hsl(0, 0%, 100%);
}
.run-qc-flag-synthetic {
  background: hsl(45, 70%, 38%);
  color: hsl(0, 0%, 100%);
}
.run-qc-flag-natural {
  background: hsl(25, 50%, 34%);
  color: hsl(0, 0%, 100%);
}
.run-qc-flag-rna {
  background: hsl(290, 45%, 48%);
  color: hsl(0, 0%, 100%);
}
.run-qc-flag-dna {
  background: hsl(265, 40%, 40%);
  color: hsl(0, 0%, 100%);
}
.run-qc-flag-icon-img {
  width: 1em;
  height: 1em;
  vertical-align: -0.125em;
}
/* Same visual language as Search.vue's .info-tooltip-box (dark fixed-
   position popover), scaled down for one short sentence instead of a
   value grid. */
.run-qc-tooltip {
  position: fixed;
  z-index: var(--z-tooltip);
  background: rgba(25, 25, 35, 0.97);
  color: #fff;
  border-radius: 8px;
  padding: 0.6rem 0.8rem;
  max-width: 260px;
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.5);
  font-size: 0.78rem;
  line-height: 1.5;
  pointer-events: auto;
}
.run-qc-tooltip-search {
  display: block;
  margin-top: 0.4rem;
  font-family: "SF Mono", "Cascadia Code", Consolas, monospace;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.6);
}

/* Bookends the header card (title/facts/QC strip) with a matching top rule,
   the same way .run-facts already closes it off with a bottom one -- without
   this, the QC chips ran straight into abstract prose with only a bare <br>
   between them, reading as a continuation of the same block instead of a
   new section. */
.run-abstract {
  padding-top: var(--space-6);
  border-top: 1px solid hsl(0, 0%, 90%);
}
.run-abstract-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-ink-muted);
  margin-bottom: var(--space-2);
}

.run-links-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  margin-top: var(--space-6);
}
.run-link-pills {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
/* A softer, non-fully-rounded chip -- distinct from the header's solid
   status pills (related-runs, QC flags), which signal state. These are
   just references out to other sites, so a quieter outline treatment. */
.run-link-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.7rem;
  border: 1px solid hsl(0, 0%, 87%);
  border-radius: 6px;
  color: hsl(0, 0%, 25%);
  font-size: 0.85rem;
  text-decoration: none;
  transition: border-color 0.15s, background-color 0.15s;
}
.run-link-pill:hover,
.run-link-pill:focus-visible {
  border-color: hsl(271, 55%, 55%);
  background: hsl(271, 45%, 97%);
}
.run-link-pill-badge {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: hsl(174, 55%, 30%);
}
.run-links-note {
  margin-top: var(--space-2);
  color: hsl(0, 0%, 45%);
  font-size: 0.85rem;
}

@media (max-width: 768px) {
  .run-page :deep(.section) {
    padding: 1.5rem 1rem;
  }
  .run-study-title {
    font-size: 1.5rem;
    line-height: 1.25;
  }
  .run-page :deep(.subtitle) {
    font-size: 1.1rem;
  }
  .run-abstract .has-text-justified {
    text-align: left !important;
  }
  .run-facts {
    flex-direction: column;
    gap: var(--space-4);
  }
  .taxonomy-selector :deep(.field-body > .field.has-addons) {
    display: flex;
    flex-wrap: wrap;
    max-width: 100%;
  }
  .taxonomy-selector :deep(.button) {
    height: auto;
    min-height: 44px;
    white-space: normal;
  }
  .run-page :deep(p),
  .run-page :deep(li) {
    overflow-wrap: anywhere;
  }
}

@media (max-width: 430px) {
  .taxonomy-selector :deep(.field-body > .field.has-addons) {
    align-items: stretch;
    flex-direction: column;
  }
  .taxonomy-selector :deep(.button) {
    justify-content: flex-start;
    width: 100%;
    border-radius: 4px !important;
  }
}
</style>
