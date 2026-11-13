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
            <dd class="stat-total-gloss">sequencing runs scanned with SingleM + Weebill</dd>
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

      <page-rail :groups="CONTENTS" :current="current_section" @jump="jumpTo" />

      <section id="dataset" class="section container stat-group-head">
        <h2 class="title is-3">Metadata</h2>
        <p class="stat-note">The runs Sandpiper has scanned, and what is known about them.</p>
      </section>

      <section id="release-year" class="section container stat-figure">
        <chart-download target="#release-year" name="runs-by-release-year" />
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#release-year">#</a> Runs by release year</h3>
        <p class="stat-note">
          How many runs were released in the NCBI SRA each year. The latest year is partial: it only includes runs
          released before {{ stats.scrape_date }}.
        </p>
        <b-switch v-model="separate_by_sample" name="split-by-sample" class="year-switch">Split by type of sample</b-switch>
        <b-switch v-model="cumulative_years" name="cumulative-years" class="year-switch">Cumulative</b-switch>
        <year-chart
          :years="stats.release_years"
          :cumulative="cumulative_years"
          :breakdown="separate_by_sample ? stats.year_breakdown : null"
          :partial-date="stats.scrape_date" />
        <p v-if="!cumulative_years" class="stat-note year-peak is-hidden-tablet">
          Most in a year: {{ peak_year.runs.toLocaleString('en-US') }} runs in {{ peak_year.year }}.
        </p>
        <table class="is-sr-only">
          <caption>Runs by release year</caption>
          <tbody>
            <tr v-for="row in stats.release_years" :key="row.year">
              <th scope="row">{{ row.year }}</th>
              <td>{{ row.runs.toLocaleString('en-US') }} {{ row.runs === 1 ? 'run' : 'runs' }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section id="sequencing-depth" class="section container stat-figure">
        <chart-download target="#sequencing-depth" name="sequencing-depth-by-release-year" />
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#sequencing-depth">#</a> Sequencing depth by release year</h3>
        <p class="stat-note">
          The total bases sequenced per run, on a square-root scale, for the runs released in each year (newest version,
          Sandpiper {{ stats.version }}). Shallow runs give less reliable profiles. Years with fewer than 10 runs are left out.
        </p>
        <year-depth-boxplot :partial-date="stats.scrape_date" />
      </section>

      <section id="sample-types" class="section container stat-figure">
        <chart-download target="#sample-types" name="types-of-sample" />
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
            <dd class="type-figures">{{ row.runs.toLocaleString('en-US') }} runs ({{ pct(row.percent) }}%)</dd>
            <dd class="stat-note">{{ SAMPLE_TYPE_TEXT[row.key].description }}</dd>
          </div>
        </dl>
      </section>

      <sample-hex-map-chart :data="stats.map" />

      <section id="collection-to-release" class="section container stat-figure">
        <chart-download target="#collection-to-release" name="collection-to-release" />
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#collection-to-release">#</a> Time from collection to release</h3>
        <collection-lag-chart />
      </section>

      <section id="coverage" class="section container stat-figure">
        <chart-download target="#coverage" name="information-coverage" />
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
              <span v-if="splitParts(row).length" class="coverage-track is-split" role="img"
                    :aria-label="splitParts(row).map(part => `${part.percent}% ${part.label.toLowerCase()}`).join(', ')">
                <span v-for="part in splitParts(row)" :key="part.key" class="coverage-fill has-tip" :class="'is-' + part.key"
                      tabindex="0" :style="{ width: part.percent + '%' }">
                  <span class="coverage-tip" role="tooltip">{{ part.tip }}</span>
                </span>
              </span>
              <span v-else class="coverage-track" role="img" :aria-label="`${row.percent}% of runs`">
                <span class="coverage-fill" :style="{ width: Math.max(row.percent, 0.5) + '%' }"></span>
              </span>
              <p class="coverage-value">{{ pct(row.percent) }}% ({{ row.runs.toLocaleString('en-US') }} runs)</p>
              <ul v-if="splitParts(row).length" class="coverage-legend" aria-label="IndicPiper runs by warning">
                <li v-for="part in splitParts(row)" :key="part.key" class="has-tip" tabindex="0">
                  <span class="coverage-swatch" :class="'is-' + part.key" aria-hidden="true"></span>{{ part.label }}: {{ pct(part.percent) }}% ({{ part.runs.toLocaleString('en-US') }} runs)
                  <span class="coverage-tip" role="tooltip">{{ part.tip }}</span>
                </li>
              </ul>
            </div>
            <p v-else class="coverage-value">Not available in this database.</p>
          </li>
        </ul>
      </section>

      <section id="profiling" class="section container stat-group-head">
        <h2 class="title is-3">Profiles</h2>
        <p class="stat-note">How well Sandpiper's profiles name the species, phyla and genomes in each run.</p>
      </section>

      <known-species-charts :data="stats.known_species" :gtdb-version="GTDB_VERSION" :version="stats.version" />

      <section id="known-by-group" class="section container stat-figure">
        <chart-download target="#known-by-group" name="known-species-fraction-by-group" />
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#known-by-group">#</a> Known species fraction by group</h3>
        <p class="stat-note is-wide">
          The share of a run’s community that belongs to species already named in GTDB, for host-associated runs
          by host and ecological runs by environment. Each group is the runs whose organism is
          “&lt;name&gt; metagenome” (for bovine, human, mouse and pig also “&lt;name&gt; gut metagenome”). This uses the
          newest version (Sandpiper {{ stats.version }}, GTDB {{ GTDB_VERSION }}). Curves show density, so the area
          under each is 1.
        </p>
        <div class="group-pair">
          <group-density-charts kind="host" bare />
          <group-density-charts kind="ecological" bare />
        </div>
      </section>

      <section id="spf-by-group" class="section container stat-figure">
        <chart-download target="#spf-by-group" name="prokaryotic-fraction-by-group" />
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#spf-by-group">#</a> Prokaryotic read fraction</h3>
        <p class="stat-note is-wide">
          The share of a run’s reads that SingleM estimates are bacterial or archaeal (SPF), for host-associated runs
          by host and ecological runs by environment. Each group is the runs whose organism is
          “&lt;name&gt; metagenome” (for bovine, human, mouse and pig also “&lt;name&gt; gut metagenome”). This uses the
          newest version (Sandpiper {{ stats.version }}, GTDB {{ GTDB_VERSION }}). Curves show density, so the area
          under each is 1.
        </p>
        <div class="group-pair">
          <group-density-charts kind="host" measure="spf" bare />
          <group-density-charts kind="ecological" measure="spf" bare />
        </div>
      </section>

      <section id="phyla" class="section container stat-figure">
        <chart-download target="#phyla" name="phylum-composition" />
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#phyla">#</a> Phylum composition by group</h3>
        <p class="stat-note">
          The mean relative abundance of each phylum across a group’s runs, so each bar sums to 100%. The ten phyla
          with the highest mean abundance are shown; the rest, and anything not placed in a phylum, are Other. Groups
          are the same runs as the known species fraction figures, listed from the most runs to the fewest (the run
          count is under each name).
        </p>
        <div class="group-pair">
          <phylum-composition-charts kind="host_associated" />
          <phylum-composition-charts kind="ecological" />
        </div>
      </section>

      <section id="top-taxa" class="section container stat-figure">
        <chart-download target="#top-taxa" name="most-widely-detected-taxa" />
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#top-taxa">#</a> Most widely detected taxa</h3>
        <p class="stat-note">
          The ten taxa found in the most runs. Detected means SingleM found the taxon in a run, not that it was
          abundant there. Select a name to open its page.
        </p>
        <div class="taxa-controls">
          <b-field grouped role="group" aria-label="Sample type">
            <b-radio-button v-model="taxa_call" name="taxa-call" native-value="all">All runs</b-radio-button>
            <b-radio-button v-model="taxa_call" name="taxa-call" native-value="host">Host-associated</b-radio-button>
            <b-radio-button v-model="taxa_call" name="taxa-call" native-value="ecological">Ecological</b-radio-button>
          </b-field>
          <b-field v-if="taxa_group_choices.length" label="Group" label-for="taxa-group" label-position="on-border">
            <b-select id="taxa-group" name="taxa-group" :compat-fallthrough="false" v-model="taxa_group">
              <option value="">{{ taxa_call === 'host' ? 'All host-associated runs' : 'All ecological runs' }}</option>
              <option v-for="group in taxa_group_choices" :key="group.name" :value="group.name">{{ group.label }}</option>
            </b-select>
          </b-field>
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
              :aria-label="taxaLabel(row)">
              <template v-if="row.segments">
                <span
                  v-for="segment in row.segments"
                  :key="segment.key"
                  :style="{ width: (100 * segment.runs / row.runs) + '%', background: segment.colour }"
                  :title="`${segment.label}: ${segment.runs.toLocaleString('en-US')} runs`"></span>
              </template>
              <template v-else>
                <span class="type-host_associated" :style="{ width: (100 * row.host / row.runs) + '%' }"></span>
                <span class="type-ecological" :style="{ width: (100 * row.ecological / row.runs) + '%' }"></span>
              </template>
            </span>
            <span class="taxa-count">{{ row.runs.toLocaleString('en-US') }} ({{ pct(row.percent) }}%)</span>
          </li>
        </ol>
        <p class="taxa-key stat-note">
          <template v-if="taxa_segment_key.length">
            <span v-for="item in taxa_segment_key" :key="item.key"><span class="type-swatch" :style="{ background: item.colour }" aria-hidden="true"></span>{{ item.label }}</span>
          </template>
          <template v-else>
            <span v-if="taxa_call !== 'ecological'"><span class="type-swatch type-host_associated" aria-hidden="true"></span>Host-associated runs</span>
            <span v-if="taxa_call !== 'host'"><span class="type-swatch type-ecological" aria-hidden="true"></span>Ecological runs</span>
          </template>
          <span>Percentages are of {{ taxa_total_text }}. Bars use one scale in every view: a full bar is {{ taxa_scale_max.toLocaleString('en-US') }} runs.</span>
        </p>
      </section>

      <section id="genome-size-by-group" class="section container stat-figure">
        <chart-download target="#genome-size-by-group" name="average-genome-size-by-group" />
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#genome-size-by-group">#</a> Average genome size</h3>
        <p class="stat-note is-wide">
          The average genome size of the bacteria and archaea in each run, for host-associated runs by host and
          ecological runs by environment. Genome size is predicted with SingleM’s
          <a href="https://wwood.github.io/singlem/tools/prokaryotic_fraction">prokaryotic_fraction</a> mode, as the
          average genome length of the taxa in a run’s community profile, weighted by their coverage
          (Eisenhofer, Alberdi &amp; Woodcroft, 2024, <i>ISME Communications</i>,
          <a href="https://doi.org/10.1093/ismeco/ycae111">https://doi.org/10.1093/ismeco/ycae111</a>).
          Runs above 8 Mb are counted in the last bin. Each group is the runs whose
          organism is “&lt;name&gt; metagenome” (for bovine, human, mouse and pig also “&lt;name&gt; gut metagenome”).
          This uses the newest version (Sandpiper {{ stats.version }}, GTDB {{ GTDB_VERSION }}). Curves show density,
          so the area under each is 1. For how genome size has changed between Sandpiper versions, see
          <a href="#versions-genome_size_mb" @click.prevent="jumpTo('versions-genome_size_mb')">Genome size by version</a> in the History section.
        </p>
        <div class="group-pair">
          <group-density-charts kind="host" measure="genome" bare />
          <group-density-charts kind="ecological" measure="genome" bare />
        </div>
      </section>

      <section id="indicpiper-by-group" class="section container stat-figure">
        <chart-download target="#indicpiper-by-group" name="indicpiper-indicator-genera-by-habitat" />
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#indicpiper-by-group">#</a> IndicPiper indicator genera by habitat</h3>
        <p class="stat-note is-wide">
          For each of IndicPiper’s habitats, the average indicator abundance (the summed abundance of the genera
          IndicPiper names as indicators of that habitat, as a percentage of the sample) and the average number of those
          genera per run. A habitat’s runs are those whose organism is recorded as that habitat, and runs with no indicator
          genus count as zero, so these averages are lower than the ones marked on each run page, which include only runs
          that have at least one indicator genus.
        </p>
        <indic-piper-group-chart />
      </section>

      <year-trend-chart />
      <year-trend-chart kind="host" />
      <year-trend-chart kind="ecological" />

      <section id="versions" class="section container stat-group-head">
        <h2 class="title is-3">History</h2>
        <p class="stat-note">How the releases differ.</p>
      </section>

      <version-comparison />

      <section id="taxonomy-databases" class="section container stat-table">
        <chart-download target="#taxonomy-databases" name="database-by-version" />
        <h3 class="subtitle is-3 stat-title"><a class="section-anchor" href="#taxonomy-databases">#</a> Sandpiper database by version</h3>
        <p class="stat-note">
          The month each version was released, the GTDB and GlobDB release it used, the date the GOLD (JGI) data was retrieved and the date the
          Metalog data was collected (pulled) for the build, and the IndicPiper indicator database version. A dash means the release is not known, or the version did not
          include that data.
        </p>
        <div class="taxonomy-table-wrap">
        <table class="taxonomy-table">
          <thead>
            <tr>
              <th scope="col">Version</th>
              <th scope="col">Released</th>
              <th scope="col">GTDB</th>
              <th scope="col">GlobDB</th>
              <th scope="col">GOLD (JGI) retrieved</th>
              <th scope="col">Metalog collected</th>
              <th scope="col">IndicPiper version</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in taxonomy_rows" :key="row.id">
              <th scope="row">{{ row.label }}</th>
              <td :class="{ 'is-unstated': !row.released }">{{ row.released || '-' }}</td>
              <td :class="{ 'is-changed': row.gtdb_new, 'is-unstated': !row.gtdb }">{{ row.gtdb || '-' }}<template v-if="row.gtdb_new">*</template></td>
              <td :class="{ 'is-changed': row.globdb_new, 'is-unstated': !row.globdb }">{{ row.globdb || '-' }}<template v-if="row.globdb_new">*</template></td>
              <td :class="{ 'is-unstated': !row.gold }">{{ row.gold || '-' }}</td>
              <td :class="{ 'is-unstated': !row.metalog }">{{ row.metalog || '-' }}</td>
              <td :class="{ 'is-unstated': !row.indicpiper }">{{ row.indicpiper || '-' }}</td>
            </tr>
          </tbody>
        </table>
        </div>
        <p class="stat-note taxonomy-footnote"><strong class="taxonomy-new">*</strong> Indicates new release version</p>
        <p class="stat-note taxonomy-footnote"><strong class="taxonomy-new">-</strong> Indicates that the inforamtion wasn't included within the release</p>
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
  KnownSpeciesCharts, YearChart, YearDepthBoxplot, SampleHexMapChart, VersionComparison,
  GroupDensityCharts, YearTrendChart, PhylumCompositionCharts, CollectionLagChart, IndicPiperGroupChart
} from '@/components/statistics'
import { GTDB_VERSION, GLOBDB_VERSION } from '@/versions'
import { CHANGELOG } from '@/views/About.vue'
import { monthYear } from '@/components/statistics/releases'
import ChartDownload from '@/components/statistics/ChartDownload.vue'
import PageRail from '@/components/PageRail.vue'
import SUMMARIES from '@/constants/groupSummaries.json'
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
  gold: {
    name: 'GOLD (JGI) metadata',
    description: 'Runs sequenced by the Joint Genome Institute, whose GOLD project ID gives curated habitat, collection details and publications. Every GOLD field can be searched.'
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

// IndicPiper's bar splits its runs by whether they carry a warning.
const INDICPIPER_PARTS = [
  { key: 'clear', label: 'IndicPiper habitat', tip: 'IndicPiper raised no warning for these runs.' },
  { key: 'caution', label: 'non-IndicPiper habitat', tip: 'These runs are either deemed not a part of the training set or contradict the metadata, so proceed with caution.' }
]

// How many taxa the list shows.
const TAXA_ROW_COUNT = 10
// Each group's most widely detected taxa (from summarise_groups.py --db); none when the file was built without a database.
const TAXA_BY_GROUP = SUMMARIES.top_taxa_by_group || {}
// The side's most widely detected taxa split by group, for stacked bars (same source; none without a database).
const TAXA_GROUP_BREAKDOWN = SUMMARIES.taxa_group_breakdown || {}
// The groups of each side in the order they are stacked, with the colours the other group charts give them.
const GROUP_SEGMENTS = {
  host: [
    { key: 'plant', label: 'Plant', colour: 'var(--color-pastel-purple)' },
    { key: 'bovine', label: 'Bovine', colour: 'var(--color-pastel-orange)' },
    { key: 'pig', label: 'Pig', colour: 'var(--color-pastel-red)' },
    { key: 'human', label: 'Human', colour: 'var(--color-pastel-blue)' },
    { key: 'mouse', label: 'Mouse', colour: 'var(--color-pastel-green)' }
  ],
  ecological: [
    { key: 'soil', label: 'Soil', colour: 'var(--color-pastel-green)' },
    { key: 'sediment', label: 'Sediment', colour: 'var(--color-pastel-red)' },
    { key: 'marine', label: 'Marine', colour: 'var(--color-pastel-blue)' },
    { key: 'freshwater', label: 'Freshwater', colour: 'var(--color-pastel-orange)' },
    { key: 'aquatic', label: 'Aquatic', colour: 'var(--color-pastel-purple)' }
  ]
}
// Runs of a side that are in none of its named groups.
const OTHER_SEGMENTS = {
  host: { key: 'other', label: 'Other host-associated runs', colour: 'var(--color-phylum-other)' },
  ecological: { key: 'other', label: 'Other ecological runs', colour: 'var(--color-phylum-other)' }
}

const TAXA_LEVELS = [
  { id: 'phylum', label: 'Phylum' },
  { id: 'genus', label: 'Genus' },
  { id: 'species', label: 'Species' }
]

// The page's contents: three groups of figures, in document order.
const CONTENTS = [
  { id: 'dataset', title: 'Metadata', links: [
    { id: 'release-year', label: 'Runs by release year' },
    { id: 'sequencing-depth', label: 'Sequencing depth by release year' },
    { id: 'sample-types', label: 'Types of sample' },
    { id: 'sample-map', label: 'Where samples were collected' },
    { id: 'collection-to-release', label: 'Time from collection to release' },
    { id: 'coverage', label: 'Information coverage' }
  ] },
  { id: 'profiling', title: 'Profiles', links: [
    { id: 'known-species', label: 'Known species fraction' },
    { id: 'known-by-group', label: 'Known species fraction by group' },
    { id: 'spf-by-group', label: 'Prokaryotic read fraction' },
    { id: 'phyla', label: 'Phylum composition by group' },
    { id: 'top-taxa', label: 'Most widely detected taxa' },
    { id: 'genome-size-by-group', label: 'Average genome size' },
    { id: 'indicpiper-by-group', label: 'IndicPiper indicator genera' },
    { id: 'known-by-year', label: 'Known species fraction by release year' },
    { id: 'known-by-year-host', label: 'Host-associated by release year' },
    { id: 'known-by-year-ecological', label: 'Ecological by release year' }
  ] },
  { id: 'versions', title: 'History', links: [
    { id: 'versions-known_species_fraction', label: 'Species fraction by version' },
    { id: 'versions-genome_size_mb', label: 'Genome size by version' },
    { id: 'taxonomy-databases', label: 'Sandpiper database by version' }
  ] }
]

// Every changelog entry is a version; its name falls back to the changelog heading.
const VERSIONS = CHANGELOG.map(entry => ({ ...entry, id: entry.version || entry.heading, label: entry.version || entry.heading }))

export default {
  name: 'Statistics',
  components: { PageRail, ChartDownload, KnownSpeciesCharts, YearChart, YearDepthBoxplot, SampleHexMapChart, VersionComparison, GroupDensityCharts, YearTrendChart, PhylumCompositionCharts, CollectionLagChart, IndicPiperGroupChart },
  title: 'Statistics - Sandpiper',
  data: function () {
    return {
      stats: null,
      error_message: null,
      taxa_database: 'gtdb',
      separate_by_sample: false,
      cumulative_years: false,
      taxa_level: 'genus',
      // Which runs the taxa are counted in: all, one side, or one group (pig, soil, ...) of that side.
      taxa_call: 'all',
      taxa_group: '',
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
    // The groups of the chosen side, in the order the Statistics page lists them (empty until the database has them).
    taxa_group_choices () {
      if (this.taxa_call === 'all') return []
      return Object.entries(TAXA_BY_GROUP)
        .filter(([, group]) => group.call === this.taxa_call)
        .map(([name, group]) => ({ name, label: `${name.charAt(0).toUpperCase()}${name.slice(1)} (${group.runs.toLocaleString('en-US')} runs)` }))
    },
    top_taxa () {
      return this.taxaRows(this.taxa_database)
    },
    // The runs the percentages are of.
    taxa_total () {
      return this.taxaTotal(this.taxa_call)
    },
    taxa_total_text () {
      const runs = this.taxa_total.toLocaleString('en-US')
      if (this.taxa_group) return `the ${runs} ${this.taxa_group} runs`
      if (this.taxa_call === 'all') return `all ${runs} runs`
      return `the ${runs} ${this.taxa_call === 'host' ? 'host-associated' : 'ecological'} runs`
    },
    // One scale for every bar in every view (All, Host, Ecological and each group), both databases and this
    // level, so a bar of 7,000 runs is short beside one of 460,000 wherever they are shown.
    taxa_scale_max () {
      const counts = ['all', 'host', 'ecological'].flatMap(call => ['gtdb', 'globdb'].flatMap(
        database => this.taxaRows(database, call, false).map(row => row.runs)))
      return Math.max(...counts, 1)
    },
    // The legend of a stacked view: the groups that have runs in the rows shown, then the rest of the side.
    taxa_segment_key () {
      if (this.taxa_group) {
        const item = GROUP_SEGMENTS[this.taxa_call].find(group => group.key === this.taxa_group)
        const side = this.taxa_call === 'host' ? 'Host-associated' : 'Ecological'
        return [{ ...item, label: `${side}: ${item.label} only` }]
      }
      const rows = ['gtdb', 'globdb'].flatMap(database => this.taxaRows(database))
      if (!rows.some(row => row.segments)) return []
      const used = new Set(rows.flatMap(row => (row.segments || []).map(segment => segment.key)))
      return [...GROUP_SEGMENTS[this.taxa_call], OTHER_SEGMENTS[this.taxa_call]].filter(item => used.has(item.key))
    },
    // One row per release for the GTDB / GlobDB table, newest first. A value is
    // new when it differs from the nearest older release that has one.
    taxonomy_rows () {
      return VERSIONS.map((version, i) => {
        const older = VERSIONS.slice(i + 1)
        return {
          id: version.id,
          label: version.label,
          released: monthYear(version.date),
          gtdb: version.gtdb,
          globdb: version.globdb,
          gold: version.gold || null,
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
        .map(row => `${SAMPLE_TYPE_TEXT[row.key].name} ${this.pct(row.percent)}%`)
        .join(', ')
    }
  },
  watch: {
    // The sections only exist once the figures have loaded.
    stats: function () {
      this.$nextTick(this.observeSections)
    },
    // A group belongs to one side, so changing the side clears the group.
    taxa_call: function () {
      this.taxa_group = ''
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
    // The coloured parts of a coverage bar (only IndicPiper's has any): runs without and with a warning.
    splitParts (row) {
      if (row.caution_runs === undefined) return []
      return INDICPIPER_PARTS.map(part => ({ ...part, percent: row[part.key + '_percent'], runs: row[part.key + '_runs'] }))
    },
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
    // A percentage with one decimal, so 54 reads 54.0 and the figures line up.
    pct (value) {
      return Number(value).toFixed(1)
    },
    plainName (name) {
      return name.replace(/^[a-z]__/, '')
    },
    // The runs a view's percentages are of: the group's, the side's, or all.
    taxaTotal (call) {
      if (call === this.taxa_call && this.taxa_group) return TAXA_BY_GROUP[this.taxa_group].runs
      if (call === 'all') return this.stats.totals.runs
      const key = call === 'host' ? 'host_associated' : 'ecological'
      return this.stats.sample_types.find(row => row.key === key).runs
    },
    // The ten taxa of the chosen runs in one database, each with its host and ecological run counts and its percent.
    // `call` is the side to show (the chosen one unless a scale is being worked out); the group applies to the chosen side.
    // `useGroup` false gives the side's own rows even while a group is chosen (for the scale).
    taxaRows (database, call = this.taxa_call, useGroup = true) {
      const level = this.taxa_level
      const share = runs => +(100 * runs / this.taxaTotal(call)).toFixed(1)
      if (useGroup && this.taxa_group && call === this.taxa_call) {
        const group = TAXA_BY_GROUP[this.taxa_group]
        const side = group.call === 'host' ? 'host' : 'ecological'
        // One segment in the group's own colour, as in the other group charts.
        const colour = GROUP_SEGMENTS[side].find(item => item.key === this.taxa_group)
        return ((group.taxa[database] || {})[level] || []).map(row => ({
          name: row.name, host: 0, ecological: 0, [side]: row.runs, runs: row.runs, percent: share(row.runs),
          segments: [{ ...colour, runs: row.runs }]
        }))
      }
      const stacked = (TAXA_GROUP_BREAKDOWN[call] || {})[database]
      if (stacked && stacked[level]) {
        return stacked[level].map(row => this.stackedRow(row, call, share))
      }
      const rows = this.stats.top_taxa[database][level]
      if (call === 'all') return rows.slice(0, TAXA_ROW_COUNT)
      const other = call === 'host' ? 'ecological' : 'host'
      return rows
        .filter(row => row[call] > 0)
        .map(row => ({ ...row, [other]: 0, runs: row[call], percent: share(row[call]) }))
        .sort((a, b) => b.runs - a.runs)
        .slice(0, TAXA_ROW_COUNT)
    },
    // A row of a side's view with its runs split by group; what no named group holds is the rest of the side.
    stackedRow (row, side, share) {
      const named = GROUP_SEGMENTS[side]
        .map(item => ({ ...item, runs: row.groups[item.key] || 0 }))
        .filter(item => item.runs > 0)
      const rest = row.runs - named.reduce((total, item) => total + item.runs, 0)
      const other = side === 'host' ? 'ecological' : 'host'
      return {
        name: row.name, host: 0, ecological: 0, [side]: row.runs, [other]: 0, runs: row.runs, percent: share(row.runs),
        segments: rest > 0 ? [...named, { ...OTHER_SEGMENTS[side], runs: rest }] : named
      }
    },
    taxaLabel (row) {
      if (row.segments) {
        return `${row.segments.map(segment => `${segment.runs.toLocaleString('en-US')} ${segment.label.toLowerCase()}`).join(', ')}`
      }
      const parts = []
      if (row.host) parts.push(`${row.host.toLocaleString('en-US')} host-associated`)
      if (row.ecological) parts.push(`${row.ecological.toLocaleString('en-US')} ecological`)
      return `${parts.join(' and ')} runs`
    },
    // Bars share one scale across every view, so their length is their number of runs.
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
  column-width: 16rem;
  column-gap: var(--space-6);
  margin-top: var(--space-3);
}
.taxa-key > span { display: block; break-inside: avoid; margin-bottom: var(--space-1); }

.stat-note.is-wide {
  max-width: none;
}
.group-pair {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-8);
  margin-top: var(--space-4);
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
/* IndicPiper's bar: runs with no warning, then runs with one, each explaining itself on hover or focus. */
.coverage-track.is-split {
  display: flex;
  overflow: visible;
}
.coverage-fill.is-clear,
.coverage-swatch.is-clear {
  background: var(--color-accent);
}
.coverage-fill.is-caution,
.coverage-swatch.is-caution {
  background: var(--color-unique-star);
}
.coverage-track.is-split .coverage-fill {
  flex: none;
}
.coverage-track.is-split .coverage-fill:first-child {
  border-radius: var(--radius-bar) 0 0 var(--radius-bar);
}
.coverage-track.is-split .coverage-fill:last-child {
  border-radius: 0 var(--radius-bar) var(--radius-bar) 0;
}
.has-tip {
  position: relative;
  cursor: help;
}
.coverage-tip {
  position: absolute;
  bottom: calc(100% + var(--space-2));
  left: 0;
  z-index: 5;
  display: none;
  width: max-content;
  max-width: min(20rem, 80vw);
  padding: var(--space-2) var(--space-3);
  font-size: 0.8rem;
  font-weight: 400;
  line-height: 1.4;
  color: var(--color-ink);
  background: var(--color-surface);
  border: 1px solid var(--color-rule);
  border-radius: var(--radius-bar);
}
.has-tip:hover > .coverage-tip,
.has-tip:focus > .coverage-tip,
.has-tip:focus-visible > .coverage-tip {
  display: block;
}
.has-tip:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
.coverage-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-6);
  margin: var(--space-1) 0 0;
  padding: 0;
  list-style: none;
  font-size: 0.85rem;
  color: var(--color-ink-muted);
}
.coverage-swatch {
  display: inline-block;
  width: 0.8rem;
  height: 0.8rem;
  margin-right: var(--space-2);
  border-radius: var(--radius-bar);
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
.statistics-page .coverage-name {
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

/* On wide windows the contents list (PageRail) is pinned in the gutter beside the content, so the content is
   capped at 1152px (Bulma's widescreen width) to leave it room; wider windows just get wider gutters. */
@media (min-width: 1440px) {
  /* The :not()s match Bulma's own rule so this cap outranks its 1344px one. */
  .statistics-page .container:not(.is-max-desktop):not(.is-max-widescreen) {
    max-width: 1152px;
  }
}
</style>
