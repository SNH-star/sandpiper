<template>
  <div class="statistics-page">
    <div v-if="stats !== null">
      <header class="section container stat-header">
        <h1 class="title">Release statistics</h1>
        <p class="stat-lede">Statistics based on v{{ stats.version }}, compared against previous releases.</p>

        <dl class="stat-totals">
          <div>
            <dt>Metagenomes</dt>
            <dd class="stat-total-value">{{ stats.totals.runs.toLocaleString('en-US') }}</dd>
            <dd class="stat-total-gloss">sequencing runs scanned with SingleM</dd>
          </div>
          <div>
            <dt>BioProjects</dt>
            <dd class="stat-total-value">{{ stats.totals.bioprojects.toLocaleString('en-US') }}</dd>
            <dd class="stat-total-gloss">studies the runs come from</dd>
          </div>
          <div>
            <dt>Sequence scanned</dt>
            <dd class="stat-total-value">{{ Math.round(stats.totals.terabases).toLocaleString('en-US') }}</dd>
            <dd class="stat-total-gloss">terabases, a million million bases</dd>
          </div>
        </dl>
      </header>

      <nav class="stat-rail" aria-label="Sections">
        <p class="stat-rail-title">On this page</p>
        <div v-for="group in CONTENTS" :key="group.id" class="stat-rail-group">
          <p class="stat-rail-group-title">{{ group.title }}</p>
          <div class="stat-rail-links">
            <a
              v-for="link in group.links"
              :key="link.id"
              :href="'#' + link.id"
              @click.prevent="jumpTo(link.id)"
              :class="{ 'is-current': current_section === link.id }"
              :aria-current="current_section === link.id ? 'location' : null">{{ link.label }}</a>
          </div>
        </div>
      </nav>

      <section id="dataset" class="section container stat-group-head">
        <h2 class="title is-3">Dataset</h2>
        <p class="stat-note">The runs Sandpiper has scanned, and what is known about them.</p>
      </section>

      <section id="release-year" class="section container stat-figure">
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#release-year">#</a> Runs by release year</h3>
        <p class="stat-note">
          How many runs were released in the NCBI SRA each year. The latest year is partial: it only includes runs
          released before {{ stats.scrape_date }}.
        </p>
        <b-switch v-model="separate_by_sample" name="split-by-sample" class="year-switch">Split by type of sample</b-switch>
        <year-chart
          :years="stats.release_years"
          :breakdown="separate_by_sample ? stats.year_breakdown : null"
          :partial-date="stats.scrape_date" />
        <p class="stat-note year-peak is-hidden-tablet">
          Most in a year: {{ peak_year.runs.toLocaleString('en-US') }} runs in {{ peak_year.year }}.
        </p>
        <table class="is-sr-only">
          <caption>Runs by release year</caption>
          <tbody>
            <tr v-for="row in stats.release_years" :key="row.year">
              <th scope="row">{{ row.year }}</th>
              <td>{{ row.runs.toLocaleString('en-US') }} runs</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section id="sequencing-depth" class="section container stat-figure">
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#sequencing-depth">#</a> Sequencing depth by release year</h3>
        <p class="stat-note">
          The total bases sequenced per run, on a log scale, for the runs released in each year (newest version,
          Sandpiper {{ stats.version }}). Shallow runs give less reliable profiles. Years with fewer than 10 runs are left out.
        </p>
        <year-depth-boxplot :partial-date="stats.scrape_date" />
      </section>

      <section id="sample-types" class="section container stat-figure">
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#sample-types">#</a> Types of sample</h3>
        <p class="stat-note">
          Sandpiper predicts whether each run’s sample is associated with a eukaryotic host. The bar shows each
          group’s share of all runs.
        </p>
        <div class="type-bar" role="img" :aria-label="typeBarLabel">
          <span
            v-for="row in stats.sample_types"
            :key="row.key"
            class="type-segment"
            :class="'type-' + row.key"
            :style="{ width: row.percent + '%' }"></span>
        </div>
        <dl class="type-list">
          <div v-for="row in stats.sample_types" :key="row.key">
            <dt><span class="type-swatch" :class="'type-' + row.key" aria-hidden="true"></span>{{ SAMPLE_TYPE_TEXT[row.key].name }}</dt>
            <dd class="type-figures">{{ row.runs.toLocaleString('en-US') }} runs ({{ row.percent }}%)</dd>
            <dd class="stat-note">{{ SAMPLE_TYPE_TEXT[row.key].description }}</dd>
          </div>
        </dl>
      </section>

      <sample-map-chart :data="stats.map" />

      <section id="top-taxa" class="section container stat-figure">
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#top-taxa">#</a> Most widely detected taxa</h3>
        <p class="stat-note">
          The ten taxa found in the most runs. Detected means SingleM found the taxon in a run, not that it was
          abundant there. Select a name to open its page.
        </p>
        <div class="taxa-controls">
          <b-field grouped role="group" aria-label="Taxonomy database">
            <b-radio-button v-model="taxa_database" name="taxa-database" native-value="gtdb" type="is-info">GTDB ({{ GTDB_VERSION }})</b-radio-button>
            <b-radio-button v-model="taxa_database" name="taxa-database" native-value="globdb" type="is-warning">GlobDB ({{ GLOBDB_VERSION }})</b-radio-button>
          </b-field>
          <b-field label="Level" label-for="taxa-level" label-position="on-border">
            <b-select id="taxa-level" name="taxa-level" :compat-fallthrough="false" v-model="taxa_level">
              <option v-for="level in TAXA_LEVELS" :key="level.id" :value="level.id">{{ level.label }}</option>
            </b-select>
          </b-field>
        </div>
        <ol class="taxa-rows">
          <li v-for="row in top_taxa" :key="row.name" class="taxa-row">
            <router-link
              class="taxa-name"
              :class="{ 'is-italic': taxa_level !== 'phylum' }"
              :to="{ name: 'SearchResults', params: { taxonomy: row.name }, query: { taxonomy_type: taxa_database } }">{{ plainName(row.name) }}</router-link>
            <span
              class="taxa-track"
              role="img"
              :style="{ width: taxaWidth(row.runs) + '%' }"
              :aria-label="`${row.host.toLocaleString('en-US')} host-associated and ${row.ecological.toLocaleString('en-US')} ecological runs`">
              <span class="type-host_associated" :style="{ width: (100 * row.host / row.runs) + '%' }"></span>
              <span class="type-ecological" :style="{ width: (100 * row.ecological / row.runs) + '%' }"></span>
            </span>
            <span class="taxa-count">{{ row.runs.toLocaleString('en-US') }} ({{ row.percent }}%)</span>
          </li>
        </ol>
        <p class="taxa-key stat-note">
          <span><span class="type-swatch type-host_associated" aria-hidden="true"></span>Host-associated runs</span>
          <span><span class="type-swatch type-ecological" aria-hidden="true"></span>Ecological runs</span>
          <span>Percentages are of all {{ stats.totals.runs.toLocaleString('en-US') }} runs.</span>
        </p>
      </section>

      <section id="coverage" class="section container stat-figure">
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#coverage">#</a> Information coverage</h3>
        <p class="stat-note">
          The share of all runs that have each kind of information. A short bar means fewer runs have it, not that
          the data is wrong.
        </p>
        <ul class="coverage-list">
          <li v-for="row in stats.coverage" :key="row.key" class="coverage-item">
            <div>
              <p class="coverage-name">{{ COVERAGE_TEXT[row.key].name }}</p>
              <p class="stat-note">{{ COVERAGE_TEXT[row.key].description }}</p>
            </div>
            <div v-if="row.runs !== null">
              <span class="coverage-track" role="img" :aria-label="`${row.percent}% of runs`">
                <span class="coverage-fill" :style="{ width: Math.max(row.percent, 0.5) + '%' }"></span>
              </span>
              <p class="coverage-value">{{ row.percent }}% ({{ row.runs.toLocaleString('en-US') }} runs)</p>
            </div>
            <p v-else class="coverage-value">Not available in this database.</p>
          </li>
        </ul>
      </section>

      <section id="profiling" class="section container stat-group-head">
        <h2 class="title is-3">Profiling specificity</h2>
        <p class="stat-note">How much of each community the reference databases can name.</p>
      </section>

      <known-species-charts :data="stats.known_species" :gtdb-version="GTDB_VERSION" :version="stats.version" />

      <section id="known-by-group" class="section container stat-figure">
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#known-by-group">#</a> Known species fraction by group</h3>
        <div class="group-pair">
          <group-density-charts kind="host" />
          <group-density-charts kind="ecological" />
        </div>
      </section>

      <section id="spf-by-group" class="section container stat-figure">
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#spf-by-group">#</a> Prokaryotic fraction by group</h3>
        <div class="group-pair">
          <group-density-charts kind="host" measure="spf" />
          <group-density-charts kind="ecological" measure="spf" />
        </div>
      </section>

      <year-trend-chart />

      <section id="phyla" class="section container stat-figure">
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#phyla">#</a> Phylum composition by group</h3>
        <div class="group-pair">
          <phylum-composition-charts kind="host_associated" />
          <phylum-composition-charts kind="ecological" />
        </div>
      </section>

      <section id="versions" class="section container stat-group-head">
        <h2 class="title is-3">History</h2>
        <p class="stat-note">How the releases differ.</p>
      </section>

      <version-comparison />

      <section id="taxonomy-databases" class="section container stat-table">
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#taxonomy-databases">#</a> Sanpiper database by version</h3>
        <p class="stat-note">
          The GTDB and GlobDB release each version used, the date the Metalog data was collected (pulled) for the build,
          and the IndicPiper indicator database version. A dash means the release is not known, or the version did not
          include that data.
        </p>
        <div class="taxonomy-table-wrap">
        <table class="taxonomy-table">
          <thead>
            <tr>
              <th scope="col">Version</th>
              <th scope="col">GTDB</th>
              <th scope="col">GlobDB</th>
              <th scope="col">Metalog collected</th>
              <th scope="col">IndicPiper</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in taxonomy_rows" :key="row.id">
              <th scope="row">{{ row.label }}</th>
              <td :class="{ 'is-changed': row.gtdb_new, 'is-unstated': !row.gtdb }">{{ row.gtdb || '-' }}<template v-if="row.gtdb_new">*</template></td>
              <td :class="{ 'is-changed': row.globdb_new, 'is-unstated': !row.globdb }">{{ row.globdb || '-' }}<template v-if="row.globdb_new">*</template></td>
              <td :class="{ 'is-unstated': !row.metalog }">{{ row.metalog || '-' }}</td>
              <td :class="{ 'is-unstated': !row.indicpiper }">{{ row.indicpiper ? 'v' + row.indicpiper : '-' }}</td>
            </tr>
          </tbody>
        </table>
        </div>
        <p class="stat-note taxonomy-footnote"><strong class="taxonomy-new">*</strong> Indicates new release version</p>
        <p class="stat-note taxonomy-footnote"><strong class="taxonomy-new">-</strong> Indicates no specific Sandpiper version</p>
        <p class="stat-note taxonomy-footnote"><em>Older versions of Sandpiper are not displayed here</em></p>
      </section>
    </div>

    <div v-else>
      <div v-if="error_message !== null">
        <section class="section container">
          <b-message title="Error" type="is-warning" :closable="false" has-icon>
            <p>ERROR {{ error_message }}</p>
          </b-message>
        </section>
      </div>

      <div v-else>
        <section class="section container">
          Loading ..
        </section>
      </div>
    </div>
  </div>
</template>

<script>
import { fetchSandpiperStatistics } from '@/api'
import {
  KnownSpeciesCharts, YearChart, YearDepthBoxplot, SampleMapChart, VersionComparison,
  GroupDensityCharts, YearTrendChart, PhylumCompositionCharts
} from '@/components/statistics'
import { GTDB_VERSION, GLOBDB_VERSION } from '@/versions'
import { CHANGELOG } from '@/views/About.vue'
import { stopPageLoading, currentLoadingToken } from '@/store/pageLoading'

const SAMPLE_TYPE_TEXT = {
  host_associated: {
    name: 'Host-associated',
    description: 'Predicted to come from inside or on an animal, plant or other eukaryotic host, such as a gut or skin sample.'
  },
  ecological: {
    name: 'Ecological',
    description: 'Predicted not to be host-associated, such as soil, water or sediment.'
  },
  unclassified: {
    name: 'Unclassified',
    description: 'Sandpiper has no prediction for these runs.'
  }
}

const COVERAGE_TEXT = {
  coordinates: {
    name: 'Location',
    description: 'Runs with a latitude and longitude, which can be placed on the maps.'
  },
  metalog: {
    name: 'Metalog metadata',
    description: 'Curated details NCBI does not hold, such as host, diet and environment, matched by BioSample.'
  },
  indicpiper: {
    name: 'IndicPiper habitat indicators',
    description: 'Runs matching at least one habitat, judged by how closely their genera fit those typical of it.'
  },
  low_complexity: {
    name: 'Low complexity flag',
    description: 'Runs where at least 95% of the community is from one order. Take their taxonomy with care.'
  }
}

const TAXA_LEVELS = [
  { id: 'phylum', label: 'Phylum' },
  { id: 'genus', label: 'Genus' },
  { id: 'species', label: 'Species' }
]

// The page's contents: three groups of figures, in document order.
const CONTENTS = [
  { id: 'dataset', title: 'Dataset', links: [
    { id: 'release-year', label: 'Runs by release year' },
    { id: 'sequencing-depth', label: 'Sequencing depth by release year' },
    { id: 'sample-types', label: 'Types of sample' },
    { id: 'sample-map', label: 'Where samples were collected' },
    { id: 'top-taxa', label: 'Most widely detected taxa' },
    { id: 'coverage', label: 'Information coverage' }
  ] },
  { id: 'profiling', title: 'Profiling specificity', links: [
    { id: 'known-species', label: 'Known species fraction' },
    { id: 'known-by-group', label: 'Fraction by group' },
    { id: 'spf-by-group', label: 'Prokaryotic fraction' },
    { id: 'known-by-year', label: 'Fraction by release year' },
    { id: 'phyla', label: 'Phylum composition' }
  ] },
  { id: 'versions', title: 'History', links: [
    { id: 'versions-known_species_fraction', label: 'Known species fraction' },
    { id: 'versions-genome_size_mb', label: 'Average genome size' },
    { id: 'taxonomy-databases', label: 'Taxonomy databases' }
  ] }
]

// Every changelog entry is a version; its name falls back to the changelog heading.
const VERSIONS = CHANGELOG.map(entry => ({ ...entry, id: entry.version || entry.heading, label: entry.version || entry.heading }))

export default {
  name: 'Statistics',
  components: { KnownSpeciesCharts, YearChart, YearDepthBoxplot, SampleMapChart, VersionComparison, GroupDensityCharts, YearTrendChart, PhylumCompositionCharts },
  title: 'Statistics - Sandpiper',
  data: function () {
    return {
      stats: null,
      error_message: null,
      taxa_database: 'gtdb',
      separate_by_sample: false,
      taxa_level: 'genus',
      TAXA_LEVELS,
      CONTENTS,
      current_section: null,
      GTDB_VERSION,
      GLOBDB_VERSION,
      SAMPLE_TYPE_TEXT,
      COVERAGE_TEXT,
      VERSIONS
    }
  },
  computed: {
    peak_year () {
      return this.stats.release_years.reduce((most, row) => (row.runs > most.runs ? row : most))
    },
    top_taxa () {
      return this.stats.top_taxa[this.taxa_database][this.taxa_level]
    },
    // Bar lengths share one scale across both databases at this level, so
    // switching GTDB <-> GlobDB moves bars only when the counts really differ
    // (scaling each list to its own top taxon made both top bars full width).
    taxa_scale_max () {
      const counts = Object.values(this.stats.top_taxa)
        .flatMap(byLevel => (byLevel[this.taxa_level] || []).map(row => row.runs))
      return Math.max(...counts, 1)
    },
    // One row per release for the GTDB / GlobDB table, newest first. A value is
    // new when it differs from the nearest older release that has one.
    taxonomy_rows () {
      return VERSIONS.map((version, i) => {
        const older = VERSIONS.slice(i + 1)
        return {
          id: version.id,
          label: version.label,
          gtdb: version.gtdb,
          globdb: version.globdb,
          // Only the newest version is the build this database holds, so it alone
          // takes the live values; older versions use what the changelog recorded.
          metalog: version.metalog || (i === 0 && this.stats.metalog_collected_date) || null,
          indicpiper: version.indicpiper || (i === 0 && this.stats.indicpiper_version) || null,
          gtdb_new: Boolean(version.gtdb) && version.gtdb !== older.find(entry => entry.gtdb)?.gtdb,
          globdb_new: Boolean(version.globdb) && version.globdb !== older.find(entry => entry.globdb)?.globdb
        }
      })
    },
    typeBarLabel () {
      return this.stats.sample_types
        .map(row => `${SAMPLE_TYPE_TEXT[row.key].name} ${row.percent}%`)
        .join(', ')
    }
  },
  watch: {
    // The sections only exist once the figures have loaded.
    stats: function () {
      this.$nextTick(this.observeSections)
    }
  },
  created () {
    this.fetchData()
  },
  beforeUnmount () {
    this.sectionObserver?.disconnect()
    this.endObserver?.disconnect()
  },
  methods: {
    // Glides to a section from the contents list (instant when the reader prefers
    // reduced motion), as the Run page's jump bar does.
    jumpTo (id) {
      const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      document.getElementById(id)?.scrollIntoView({ behavior: still ? 'auto' : 'smooth', block: 'start' })
    },
    // Marks the first listed section that is in the upper part of the window. The
    // last one is too near the end of the page to reach it, so it takes over once
    // it is fully on screen.
    observeSections () {
      this.sectionObserver?.disconnect()
      this.endObserver?.disconnect()
      const ids = CONTENTS.flatMap(group => group.links.map(link => link.id))
      const last = ids[ids.length - 1]
      const visible = new Set()
      let atEnd = false
      const update = () => {
        const current = atEnd ? last : ids.find(id => visible.has(id))
        if (current) this.current_section = current
      }
      this.sectionObserver = new IntersectionObserver(entries => {
        entries.forEach(e => (e.isIntersecting ? visible.add(e.target.id) : visible.delete(e.target.id)))
        update()
      }, { rootMargin: '-10% 0px -70% 0px' })
      ids.forEach(id => {
        const section = document.getElementById(id)
        if (section) this.sectionObserver.observe(section)
      })
      const end = document.getElementById(last)
      if (end) {
        this.endObserver = new IntersectionObserver(entries => {
          atEnd = entries[0].isIntersecting
          update()
        }, { threshold: 1 })
        this.endObserver.observe(end)
      }
    },
    plainName (name) {
      return name.replace(/^[a-z]__/, '')
    },
    taxaWidth (runs) {
      return Math.max((100 * runs) / this.taxa_scale_max, 0.5)
    },
    fetchData () {
      // Captured now, not read lazily inside .finally() -- see
      // src/store/pageLoading.ts for why a stale token must not clear a
      // newer navigation's loading state.
      const loadingToken = currentLoadingToken()
      fetchSandpiperStatistics()
        .then(response => {
          this.stats = response.data
        })
        .catch(error => {
          this.error_message = error.message
        })
        // The template gates on stats/error_message, so the page is
        // genuinely blank until this settles either way.
        .finally(() => stopPageLoading(loadingToken))
    }
  }
}
</script>

<style scoped>
.statistics-page {
  --radius-bar: 2px;
  overflow-wrap: anywhere;
}
.statistics-page .section {
  padding-top: var(--space-8);
  padding-bottom: var(--space-4);
}
.stat-note {
  max-width: 62ch;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--color-ink-muted);
}
.year-peak {
  margin-top: var(--space-2);
}
.section-anchor:active {
  color: var(--color-accent-strong);
}
.section-anchor:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}


/* Types of sample */
.type-bar {
  display: flex;
  height: 1rem;
  margin: var(--space-6) 0 var(--space-4);
  border-radius: var(--radius-bar);
  overflow: hidden;
  background: var(--color-track);
}
.type-segment {
  display: block;
  height: 100%;
}
.type-host_associated { background: var(--color-sample-host); }
.type-ecological { background: var(--color-sample-ecological); }
.type-unclassified { background: var(--color-sample-unclassified); }
.type-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: var(--space-4) var(--space-8);
}
.type-list dt {
  font-weight: 600;
  color: var(--color-ink);
}
.type-swatch {
  display: inline-block;
  width: 0.8rem;
  height: 0.8rem;
  margin-right: var(--space-2);
  border-radius: var(--radius-bar);
}
.type-figures {
  font-variant-numeric: tabular-nums;
  color: var(--color-ink);
}

/* Most widely detected taxa */
.taxa-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--space-4) var(--space-6);
  margin-top: var(--space-6);
}
.taxa-rows {
  margin: var(--space-2) 0 0;
  padding: 0;
  list-style: none;
}
.taxa-row {
  display: grid;
  grid-template-columns: minmax(8rem, 13rem) minmax(0, 1fr) 10.5rem;
  align-items: center;
  gap: var(--space-3);
  border-bottom: 1px solid var(--color-rule);
}
.taxa-row:last-child {
  border-bottom: 0;
}
.taxa-name {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
}
.taxa-track {
  display: flex;
  height: 0.75rem;
  border-radius: var(--radius-bar);
  overflow: hidden;
}
.taxa-track > span {
  display: block;
  height: 100%;
}
.taxa-count {
  font-variant-numeric: tabular-nums;
  text-align: right;
  color: var(--color-ink);
}
.taxa-key {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-6);
  margin-top: var(--space-3);
}

.group-pair {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-8);
}
@media (max-width: 900px) {
  .group-pair {
    grid-template-columns: minmax(0, 1fr);
  }
}
.year-switch {
  margin-top: var(--space-4);
}

/* Information coverage */
.coverage-list {
  margin: var(--space-4) 0 0;
  padding: 0;
  list-style: none;
}
.coverage-item {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: var(--space-2) var(--space-8);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-rule);
}
.coverage-item:last-child {
  border-bottom: 0;
}
.coverage-name {
  font-weight: 600;
  color: var(--color-ink);
}
.coverage-track {
  display: block;
  height: 0.6rem;
  margin-top: var(--space-2);
  border-radius: var(--radius-bar);
  overflow: hidden;
  background: var(--color-track);
}
.coverage-fill {
  display: block;
  height: 100%;
  background: var(--color-accent);
}
.coverage-value {
  margin-top: var(--space-1);
  font-variant-numeric: tabular-nums;
  color: var(--color-ink);
}

/* Taxonomy databases by version */
.taxonomy-table-wrap {
  max-width: 46rem;
  overflow-x: auto;
}
.taxonomy-table {
  width: 100%;
  max-width: 46rem;
  margin-top: var(--space-4);
  border-collapse: collapse;
}
.taxonomy-table th,
.taxonomy-table td {
  padding: var(--space-2) var(--space-3) var(--space-2) 0;
  border-bottom: 1px solid var(--color-rule);
  text-align: left;
  font-variant-numeric: tabular-nums;
}
.taxonomy-table thead th,
.taxonomy-table td {
  white-space: nowrap;
}
.taxonomy-table thead th {
  font-size: 0.85rem;
  font-weight: 400;
  color: var(--color-ink-muted);
}
.taxonomy-table tbody th {
  font-weight: 400;
  color: var(--color-ink);
}
.taxonomy-table td.is-unstated {
  color: var(--color-ink-muted);
}
.taxonomy-table td.is-changed {
  font-weight: 700;
  color: var(--color-accent-strong);
}
.taxonomy-footnote {
  margin-top: var(--space-2);
}
.taxonomy-new {
  color: var(--color-accent-strong);
}

@media (max-width: 768px) {
  .statistics-page .subtitle.is-3 {
    font-size: 1.6rem;
    font-variant-numeric: tabular-nums;
  }
  .taxa-row {
    grid-template-columns: minmax(0, 1fr);
    gap: 0;
    padding-bottom: var(--space-2);
  }
  .taxa-count {
    margin-top: var(--space-1);
    text-align: left;
  }
  .coverage-item {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

<style>
/* Statistics page system: header, groups of figures and panels. */
/* Header */
.statistics-page .stat-header {
  padding-top: var(--space-12);
  padding-bottom: var(--space-4);
}
.statistics-page .stat-header .title {
  margin-bottom: var(--space-2);
  font-size: clamp(2rem, 1.4rem + 2vw, 3rem);
  font-variant-numeric: tabular-nums;
}
/* Wrapping: balance short blocks so a heading or caption never ends on a lone
   word; "pretty" avoids orphans in running text. Unscoped so it reaches the
   chart components' own notes and captions. */
.statistics-page .stat-title,
.statistics-page .title,
.statistics-page .stat-lede,
.statistics-page .stat-total-gloss,
.statistics-page .coverage-name,
.statistics-page .stat-rail-title,
.statistics-page .stat-rail-group-title {
  text-wrap: balance;
}
.statistics-page .stat-note,
.statistics-page figcaption,
.statistics-page dd {
  text-wrap: pretty;
}
.statistics-page .stat-lede {
  max-width: 62ch;
  color: var(--color-ink-muted);
}
.statistics-page .stat-totals {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-8);
  margin-top: var(--space-8);
  padding: var(--space-6) 0;
  border-top: 1px solid var(--color-rule);
  border-bottom: 1px solid var(--color-rule);
}
.statistics-page .stat-totals dt {
  font-size: 0.9rem;
  color: var(--color-ink-muted);
}
.statistics-page .stat-total-value {
  margin: var(--space-1) 0;
  font-family: var(--font-display);
  font-size: clamp(1.8rem, 1.2rem + 2vw, 2.6rem);
  font-weight: 600;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
  color: var(--color-accent-strong);
}
.statistics-page .stat-total-gloss {
  max-width: 28ch;
  font-size: 0.9rem;
  line-height: 1.4;
  color: var(--color-ink-muted);
}

/* Groups */
.statistics-page .section.stat-group-head {
  padding-top: var(--space-16);
  padding-bottom: 0;
}
.statistics-page .stat-group-head .title {
  margin-bottom: var(--space-1);
  padding-bottom: var(--space-2);
  border-bottom: 2px solid var(--color-accent);
}

/* Figures and tables: a title, then the caption and the chart */
.statistics-page .section.stat-figure,
.statistics-page .section.stat-table {
  margin-top: var(--space-8);
  padding-top: var(--space-8);
  padding-bottom: 0;
  border-top: 1px solid var(--color-rule);
}
.statistics-page .stat-group-head + .stat-figure,
.statistics-page .stat-group-head + .stat-table {
  margin-top: var(--space-4);
  border-top: 0;
}
.statistics-page .stat-title {
  position: relative;
  margin-bottom: var(--space-3);
}
.statistics-page .stat-title .section-anchor {
  position: absolute;
  left: -1.1rem;
  bottom: 0;
  opacity: 0;
  text-decoration: none;
}
.statistics-page .stat-title:hover .section-anchor,
.statistics-page .stat-title .section-anchor:focus-visible {
  opacity: 1;
}

/* Panels inside a figure */
.statistics-page .stat-panel-title {
  margin-bottom: var(--space-2);
  font-family: var(--font-sans);
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-ink);
}
.statistics-page .stat-panel-title .section-anchor {
  display: none;
}

@media (max-width: 768px) {
  .statistics-page .stat-totals {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-6);
  }
}

/* Contents list pinned in the empty space left of the centred content, on very wide
   screens only. */
.statistics-page .stat-rail {
  display: none;
}
@media (min-width: 1440px) {
  /* Content is capped at 1152px (Bulma's widescreen width) so the list fits beside it
     on laptop screens; wider screens just get wider gutters. */
  /* The :not()s match Bulma's own rule so this cap outranks its 1344px one. */
  .statistics-page .container:not(.is-max-desktop):not(.is-max-widescreen) {
    max-width: 1152px;
  }
  .statistics-page .stat-rail {
    /* Pinned to the window's left edge at a fixed width: as the window narrows, the
       space between the list and the content shrinks, and the list never moves.
       The 1440px breakpoint is where that space is still about 1.5rem. */
    position: fixed;
    top: 8rem;
    z-index: 100;
    left: 1rem;
    width: 6.5rem;
    display: block;
    max-height: calc(100vh - 10rem);
    overflow-y: auto;
    scrollbar-width: none;
  }
  .statistics-page .stat-rail::-webkit-scrollbar {
    display: none;
  }
  .statistics-page .stat-rail-title {
    margin-bottom: var(--space-2);
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--color-ink);
  }
  .statistics-page .stat-rail-group + .stat-rail-group {
    margin-top: var(--space-3);
  }
  .statistics-page .stat-rail-group-title {
    margin-bottom: var(--space-1);
    font-size: 0.8rem;
    color: var(--color-ink-muted);
  }
  .statistics-page .stat-rail-links {
    border-left: 1px solid var(--color-rule);
  }
  .statistics-page .stat-rail-links a {
    position: relative;
    display: block;
    padding: var(--space-1) 0 var(--space-1) var(--space-3);
    font-size: 0.82rem;
    font-weight: 500;
    line-height: 1.35;
    color: var(--color-ink-muted);
    text-decoration: none;
    transition: color 0.15s;
  }
  /* The accent runs down the list's own hairline, beside the current section. */
  .statistics-page .stat-rail-links a::after {
    content: '';
    position: absolute;
    left: -1px;
    top: 0;
    bottom: 0;
    width: 2px;
    background: var(--color-accent);
    transform: scaleY(0);
    transform-origin: top;
    transition: transform 0.2s var(--ease-spring);
  }
  .statistics-page .stat-rail-links a:hover,
  .statistics-page .stat-rail-links a.is-current {
    color: var(--color-ink);
  }
  .statistics-page .stat-rail-links a.is-current::after {
    transform: scaleY(1);
  }
  .statistics-page .stat-rail-links a:active {
    color: var(--color-accent-strong);
  }
  .statistics-page .stat-rail-links a:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
    border-radius: 2px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .statistics-page .stat-rail-links a,
  .statistics-page .stat-rail-links a::after {
    transition: none;
  }
}
</style>
