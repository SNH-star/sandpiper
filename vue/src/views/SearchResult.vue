<template>
  <section class="section">
    <div v-if="search_result !== null && total_num_results !== null" class="container">
      <section v-if="is_query" class="section">
        <h1 class="title search-topic-title">Search topic:</h1>
        <ul class="query-parts" aria-label="Search topic">
          <li v-for="(part, i) in query_parts" :key="i" class="query-part">
            <span v-if="part.key" class="query-part-key">{{ part.key }}:</span>
            <span class="query-part-value">{{ part.key ? (part.value || 'any value') : part.text }}</span>
          </li>
        </ul>
        <div v-if="query_taxon && !is_amplicon" class="has-text-centered taxonomy-switcher">
          <b-field grouped position="is-centered">
            <b-radio-button
              v-model="taxonomy_type"
              native-value="gtdb"
              :disabled="disableGtdb" type="is-info"
              @input="onTaxonomyTypeChange('gtdb')">
              GTDB ({{ GTDB_VERSION }})
            </b-radio-button>
            <b-radio-button
              v-model="taxonomy_type"
              native-value="globdb"
              :disabled="disableGlobdb" type="is-warning"
              @input="onTaxonomyTypeChange('globdb')">
              GlobDB ({{ GLOBDB_VERSION }})
            </b-radio-button>
          </b-field>
          <p class="help">
            Relative abundance and coverage of {{ query_taxon.name }} from
            {{ taxonomy_type === 'gtdb' ? `GTDB (${GTDB_VERSION})` : `GlobDB (${GLOBDB_VERSION})` }};
            runs where it was only found in the other database show –.
          </p>
        </div>
        <p v-else-if="query_taxon" class="has-text-centered help">
          Relative abundance is {{ query_taxon.name }}'s share of each run's reads.
        </p>
        <p v-else-if="query_names_partial_taxon" class="has-text-centered help">
          Give a full taxon name (e.g. g__Prochlorococcus) to see relative abundance and coverage.
        </p>
        <p class="has-text-centered help">
          {{ is_amplicon ? 'Amplicon runs' : 'Metagenome runs' }} matching this search.
          <router-link :to="back_to_search">Edit search</router-link>
        </p>
        <b-message v-if="total_num_results === 0" type="is-warning" has-icon :closable="false" class="mt-4">
          No runs match this search.
        </b-message>
      </section>
      <section v-else class="section">
        <h1 class="title" style="text-align: center;">
          The {{ taxonomy_level }}
          <span v-if="taxonomy_level==='species' || taxonomy_level==='genus'">
            <i>{{ taxon_name }}</i>
          </span>
          <span v-else>{{ taxon_name }}</span>
          </h1>
        <p style="text-align: center;">{{ lineage.join('; ') }}</p>
        <br />
        <div v-if="is_amplicon" class="has-text-centered taxonomy-switcher">
          <p class="help">Amplicon runs (marker-gene sequencing). Abundance is the taxon's share of each run's reads.</p>
        </div>
        <div v-else class="has-text-centered taxonomy-switcher">
          <b-field grouped position="is-centered">
            <b-radio-button
              v-model="taxonomy_type"
              native-value="gtdb"
              :disabled="disableGtdb" type="is-info"
              @input="onTaxonomyTypeChange('gtdb')">
              GTDB ({{ GTDB_VERSION }})
            </b-radio-button>
            <b-radio-button
              v-model="taxonomy_type"
              native-value="globdb"
              :disabled="disableGlobdb" type="is-warning"
              @input="onTaxonomyTypeChange('globdb')">
              GlobDB ({{ GLOBDB_VERSION }})
            </b-radio-button>
          </b-field>
          <p class="help">Viewing {{ taxonomy_type === 'gtdb' ? `GTDB (${GTDB_VERSION})` : `GlobDB (${GLOBDB_VERSION})` }} entry.</p>
          <p class="help" v-if="other_taxon_available === false">
            <span v-if="taxonomy_type==='gtdb'">Taxon not available in GlobDB ({{ GLOBDB_VERSION }}) view.</span>
            <span v-else>Taxon not available in GTDB ({{ GTDB_VERSION }}) view.</span>
          </p>
        </div>
      </section>

      <section class="section">
        <nav class="level">
          <div class="level-item has-text-centered">
            <div class="level-item">
              <div>
                <a href="#matching-samples">
                  <p class="heading">Matching Samples</p>
                  <p class="title">{{ total_num_results.toLocaleString("en-US") }}</p>
                </a>
                <p class="matching-count-caption">runs total</p>
              </div>
            </div>
          </div>
          <div v-if="is_amplicon" class="level-item has-text-centered">
            <div class="level-item">
              <div>
                <a href="#geographic-distribution">
                  <p class="heading">Marine realms</p>
                  <p class="title">{{ num_realms }}</p>
                </a>
                <p>realms where it was found</p>
              </div>
            </div>
          </div>
          <div v-else class="level-item has-text-centered">
            <div class="level-item">
              <div>
                <a href="#host-association-overview">
                  <p class="heading">Host-association</p>
                  <p class="title">{{ host_percent }}</p>
                </a>
                <p>of runs are eukaryote host-associated</p>
              </div>
            </div>
          </div>
          <div class="level-item has-text-centered">
            <div class="level-item">
              <div>
                <a href="#geographic-distribution">
                  <p class="heading">Geographic Distribution</p>
                  <p class="title" v-if="is_query">{{ total_lat_lon_runs.toLocaleString("en-US") }}</p>
                  <p class="title" v-else-if="num_lat_lon_runs < 1000">{{ num_lat_lon_runs.toLocaleString("en-US") }}</p>
                  <p class="title" v-else>1000+</p>
                </a>
                <p>runs with lat/lon.</p>
              </div>
            </div>
          </div>
        </nav>
      </section>

      <section class="section" id="geographic-distribution">
        <div class="section" v-if="this.lat_lons !== null">
          <h2 class="subtitle is-2 bd-anchor-title">
            <a class="bd-anchor-link" href="#geographic-distribution"># </a>
            <span class="bd-anchor-name">Geographic distribution</span>
          </h2>

          <div class="has-text-centered mapping-mode-switcher">
            <b-field grouped position="is-centered">
              <b-radio-button v-model="mode" native-value="geographic" :type="mode === 'geographic' ? 'is-primary' : ''"
                @input="onModeChange('geographic')">
                Geographical Mapping
              </b-radio-button>
              <b-radio-button v-model="mode" native-value="niche" :type="mode === 'niche' ? 'is-primary' : ''"
                @input="onModeChange('niche')">
                Niche Mapping
              </b-radio-button>
            </b-field>
          </div>

          <div v-if="mode === 'niche'" class="niche-mapping-panel">
            <div class="niche-mapping-panel-header">
              <p class="niche-mapping-eyebrow">Filter by niche</p>
              <b-button v-if="activeNicheFilters" type="is-text" size="is-small" icon-left="close"
                @click="resetNicheFilters">
                Reset filters
              </b-button>
            </div>
            <p v-if="is_amplicon" class="help niche-mapping-help">
              Filter the maps and matching samples below by modelled pH and
              temperature, marine realm and depth zone. Sliders only stop on
              values actually present {{ is_query ? 'in these results' : 'for this taxon' }}, and narrow each other
              as you pick.
            </p>
            <p v-else class="help niche-mapping-help">
              Filter the maps and matching samples below by pH, temperature,
              host association, and IndicPiper community. Sliders only stop on
              values actually present {{ is_query ? 'in these results' : 'for this taxon' }}, and narrow each other
              as you pick.
            </p>

            <div class="niche-field-grid">
              <b-field :label="is_amplicon ? 'pH (modelled)' : 'pH'" class="niche-field">
                <div v-if="phOptions.length" class="niche-slider-row">
                  <input type="number" class="niche-range-input" :step="0.5" :value="phMinDisplay"
                    aria-label="Minimum pH" @change="onPhMinInput($event.target.value)" />
                  <b-slider :model-value="[phMinIndex, phMaxIndex]" type="is-primary" :min="0"
                    :max="phOptions.length - 1" :step="1" ticks
                    :custom-formatter="formatPhIndex" @change="onPhRangeChange" />
                  <input type="number" class="niche-range-input" :step="0.5" :value="phMaxDisplay"
                    aria-label="Maximum pH" @change="onPhMaxInput($event.target.value)" />
                </div>
                <p v-else class="help">No pH data available for the current filters.</p>
              </b-field>

              <b-field :label="is_amplicon ? 'Temperature (°C, modelled)' : 'Temperature (°C)'" class="niche-field">
                <div v-if="temperatureOptions.length" class="niche-slider-row">
                  <input type="number" class="niche-range-input" :step="1" :value="temperatureMinDisplay"
                    aria-label="Minimum temperature" @change="onTemperatureMinInput($event.target.value)" />
                  <b-slider :model-value="[temperatureMinIndex, temperatureMaxIndex]" type="is-primary" :min="0"
                    :max="temperatureOptions.length - 1" :step="1" ticks
                    :custom-formatter="formatTemperatureIndex" @change="onTemperatureRangeChange" />
                  <input type="number" class="niche-range-input" :step="1" :value="temperatureMaxDisplay"
                    aria-label="Maximum temperature" @change="onTemperatureMaxInput($event.target.value)" />
                </div>
                <p v-else class="help">No temperature data available for the current filters.</p>
              </b-field>

              <b-field :label="is_amplicon ? 'Marine realm' : 'Host association'" class="niche-field">
                <b-select v-model="hostAssociation" expanded @update:model-value="onHostAssociationChange">
                  <option value="">Any</option>
                  <option v-for="opt in hostAssociationOptions" :key="opt" :value="opt">
                    {{ is_amplicon ? opt : (opt === 'host' ? 'Host-associated' : 'Ecological') }}
                  </option>
                </b-select>
              </b-field>

              <b-field :label="is_amplicon ? 'Depth zone' : 'IndicPiper community'" class="niche-field">
                <div v-if="piperCommunityOptions.length">
                  <b-select v-model="piperCommunity" expanded @update:model-value="onPiperCommunityChange">
                    <option value="">Any</option>
                    <option v-for="opt in piperCommunityOptions" :key="opt" :value="opt">
                      {{ opt }}
                    </option>
                  </b-select>
                </div>
                <p v-else class="help">No {{ is_amplicon ? 'depth zone' : 'IndicPiper community' }} data available for the current filters.</p>
              </b-field>
            </div>
          </div>

          <h3 class="subtitle is-4">Sample distribution</h3>
          <p class="help section-hint">
            This map is interactive &mdash; click a cluster to zoom in and filter the samples table and the Individual runs map below.
          </p>
          <TaxonomySampleMap :taxon="taxonomy" :query="query" :taxonomy-type="taxonomy_type" :niche-filters="activeNicheFilters"
            @cluster-selected="onClusterSelected" />

          <h3 class="subtitle is-4 section-heading-spaced">Individual runs</h3>
          <template v-if="is_query">
            <p class="individual-runs-caption">{{ query_markers_caption }}</p>
            <p v-if="!cluster && total_num_results > total_lat_lon_runs" class="individual-runs-caption">
              {{ (total_num_results - total_lat_lon_runs).toLocaleString("en-US") }} other runs have no latitude/longitude and are not shown on this map.
            </p>
          </template>
          <p v-else-if="cluster" class="individual-runs-caption">
            Showing the {{ num_lat_lon_runs.toLocaleString("en-US") }} run{{ num_lat_lon_runs === 1 ? '' : 's' }} in your selected map cluster
            (relative abundance &gt;= {{ parseFloat((lat_lons_min_relabund*100).toPrecision(2)) }}%).
          </p>
          <p v-else-if="num_lat_lon_runs < 1000" class="individual-runs-caption">
            {{ num_lat_lon_runs.toLocaleString("en-US") }} runs have relative abundance &gt;=
            {{ parseFloat((lat_lons_min_relabund*100).toPrecision(2)) }}% and associated latitude/longitude metadata.
          </p>
          <p v-else class="individual-runs-caption">
            1,000+ runs have associated latitude/longitude metadata. The 1000 runs with relative abundance
            &gt;= {{ parseFloat((lat_lons_min_relabund*100).toPrecision(2)) }}% are shown below.
          </p>
          <!-- Meaningless once a cluster is selected: cluster membership is
               itself grouped by lat/lon, so every run in the cluster
               necessarily has coordinates -- total_num_results and
               num_lat_lon_runs are then the same cluster-scoped count, and
               this would always read "0 other runs are not shown". -->
          <p v-if="!cluster && !is_query" class="individual-runs-caption">{{ (total_num_results - num_lat_lon_runs).toLocaleString("en-US") }} other runs are not shown on this map.</p>

          <div id="individual-runs-map" class="individual-runs-map">
            <l-map ref="individualRunsMap" style="width: 100%; height: 100%;" :zoom.sync="zoom" :center.sync="center">
              <l-tile-layer :url="url" :attribution="attribution" :options="tile_layer_options" />
              <l-marker v-for="markerLatLng in this.lat_lons" v-bind:key="markerLatLng[0]" :lat-lng="markerLatLng['lat_lon']">
                <l-popup :content="html_for_map_popup(markerLatLng)" :options="{ interactive: true }">
                </l-popup>
              </l-marker>
            </l-map>
          </div>
          <div class="map-reset-row">
            <button type="button" class="map-reset" @click="reset_map()"><b-icon icon="refresh" size="is-small" /> reset zoom</button>
            <button v-if="cluster" type="button" class="map-reset" @click="clearCluster()">
              <b-icon icon="close" size="is-small" /> reset map selection
            </button>
          </div>
        </div>
      </section>

      <section class="section" id="matching-samples">
        <h2 class="subtitle is-2 bd-anchor-title">
          <a class="bd-anchor-link" href="#matching-samples"># </a>
          <span class="bd-anchor-name">Matching samples</span>
        </h2>

        <div v-if="cluster" class="notification is-info is-light cluster-filter">
          <span>
            Showing only samples from the map cluster at
            <b>{{ cluster.lat }}, {{ cluster.lon }}</b>
            ({{ cluster.total.toLocaleString("en-US") }} samples). Sorting,
            paging and the random button all stay within this cluster.
          </span>
          <b-button type="is-info" size="is-small" @click="clearCluster">Show all samples</b-button>
        </div>

        <div class="results-actions">
          <b-button v-if="is_query" tag="a" type="is-info" :href="query_csv_link">Download CSV</b-button>
          <template v-else>
            <b-button tag="a" type="is-info" :href="minimal_csv_link()">Download minimal CSV</b-button>
            <b-button tag="a" type="is-info" :href="csv_link()">Download CSV with extra columns</b-button>
          </template>
          <b-button type="is-light" icon-left="shuffle-variant" class="mobile-shuffle-button" @click="shuffle_runs">Shuffle runs</b-button>
          <b-switch v-if="!is_amplicon" v-model="exclude_low_complexity">Exclude low complexity</b-switch>
          <span v-if="!is_amplicon && !exclude_low_complexity" class="low-complexity-summary">{{ is_query ? num_low_complexity_runs : low_complexity_count }} / {{ total_num_results }} runs have ≥95% reads from one order (Low Complexity)</span>
        </div>
        <b-table
          :data="display_profiles"
          :striped="true"
          :sort-icon="'arrow-up'"
          :default-sort="this.sortField"
          :default-sort-direction="this.sortDirection"
          paginated
          :current-page="this.page"
          :per-page="this.pageSize"
          pagination-simple
          backend-pagination
          backend-sorting
          :total="filtered_total !== null ? filtered_total : total_num_results"
          mobile-cards
          @page-change="onPageChange"
          @sort="onSort">

          <b-table-column :field="is_query ? 'sample_acc' : 'sample_name'" label='Run' :sortable="is_query" useSorted>
            <template #header>
              <span style="display: flex; align-items: center; gap: 0.4rem;">
                Run
                <b-button class="shuffle-btn" size="is-small" icon-left="shuffle-variant" @click.stop="shuffle_runs" title="Shuffle order" />
              </span>
            </template>
            <template #default="props">
              <a :href="run_path(props.row.sample_acc)">{{ props.row.sample_acc }}</a>
            </template>
          </b-table-column>

          <b-table-column field='organism' label='Environment' v-slot="props" sortable>
            {{ props.row.organism }}
          </b-table-column>

          <b-table-column field='release_year' :label="is_amplicon ? 'Collection year' : 'Release year'" v-slot="props" centered sortable>
            {{ props.row.release_year }}
          </b-table-column>

          <b-table-column v-if="!is_query || query_taxon" field='relative_abundance' label='Relative abundance (%)' v-slot="props" centered sortable>
            {{ props.row.relative_abundance ?? '–' }}
          </b-table-column>

          <b-table-column v-if="!is_query || query_taxon" field='coverage' :label="is_amplicon ? 'Reads' : 'Genome coverage'" v-slot="props" centered sortable>
            {{ props.row.coverage ?? '–' }}
          </b-table-column>

        </b-table>
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
            <p>{{ error_message }}</p>
          </b-message>
        </section>
      </div>

      <div v-else>
        <section class="section container">
          Loading...
        </section>
      </div>
    </div>

  </section>
</template>

<script>
import {
  fetchGlobalDataByTaxonomy, fetchRunsByTaxonomy, fetchTaxonomyNicheOptions, taxonomyApiUrl,
  fetchQueryGlobalData, fetchQueryRunData, fetchQueryNicheOptions, queryCsvUrl
} from '@/api'
import { GTDB_VERSION, GLOBDB_VERSION } from '@/versions'
import { splitQueryParts, unquoteQueryValue } from '@/composables/useSearchAutocomplete'
import { stopPageLoading, currentLoadingToken } from '@/store/pageLoading'

// If you need to reference 'L', such as in 'L.icon', then be sure to
// explicitly import 'leaflet' into your component
// import L from 'leaflet'
import { LMap, LTileLayer, LMarker, LPopup } from '@vue-leaflet/vue-leaflet'
import TaxonomySampleMap from '@/components/TaxonomySampleMap.vue'

import { Icon, latLng } from 'leaflet'

// Import marker icon images as modules
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// Make the marker appear https://vue-leaflet.github.io/vue-leaflet/#/quick-start#marker-icons-are-missing
delete Icon.Default.prototype._getIconUrl
Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow
})

const default_zoom = 1.5

export default {
  name: 'SearchResults',
  title () {
    if (this.query) return `Search results for ${this.query} - Sandpiper`
    return `${this.dataset === 'amplicon' ? 'Amplicon runs' : 'Runs'} with ${this.taxonomy} - Sandpiper`
  },
  // dataset: 'amplicon' (from the /amplicon/taxonomy route) shows the same page on amplicon data.
  // query: set instead of taxonomy by "Explore tabled results" on the advanced
  // search (/search/results?q=) -- the page then shows every run matching it.
  props: ['taxonomy', 'dataset', 'query'],
  components: {
    TaxonomySampleMap,
    LMap,
    LTileLayer,
    LMarker,
    LPopup
  },
  data: function () {
    return {
      search_result: null,
      taxon_name: null,
      lineage: [], // set to empty because otherwise there's a null pointer issue until filled
      sortIcon: 'arrow-up',
      total_num_results: null,
      GTDB_VERSION,
      GLOBDB_VERSION,
      exclude_low_complexity: true,
      shuffled_profiles: null,
      cluster: null,
      filtered_total: null,
      shuffled_profiles: null,
      page: 1,
      pageSize: 100,
      sortField: 'relative_abundance',
      sortDirection: 'desc',
      error_message: null,
      taxonomy_type: 'gtdb',
      other_taxonomy_type: 'globdb',
      other_taxon_available: null,

      mode: 'geographic',
      // Range sliders express "Any" as spanning the full options list (index
      // 0 to length-1) rather than a sentinel value -- since every available
      // bucket already falls inside that span, it's equivalent to no filter
      // and activeNicheFilters skips sending one. route*Min/Max hold the
      // bound read from the URL (possibly a bucket value not yet resolvable
      // to an index, if phOptions hasn't loaded); syncSliderIndices()
      // resolves them into concrete indices once options arrive.
      routePhMin: null,
      routePhMax: null,
      routeTemperatureMin: null,
      routeTemperatureMax: null,
      phMinIndex: 0,
      phMaxIndex: 0,
      temperatureMinIndex: 0,
      temperatureMaxIndex: 0,
      phOptions: [],
      temperatureOptions: [],
      hostAssociation: '',
      hostAssociationOptions: [],
      piperCommunity: '',
      piperCommunityOptions: [],

      num_realms: null,
      lat_lons: null,
      lat_lons_min_relabund: null,
      num_lat_lon_runs: null,
      total_lat_lon_runs: 0,
      // Search results: {name, taxonomy_types} when the search names a whole taxon.
      query_taxon: null,
      num_low_complexity_runs: 0,
      // Only the latest request may update the table / summary (quick clicks overlap).
      runs_request: 0,
      global_request: 0,
      // Use the plain tile.openstreetmap.org host - the a/b/c subdomains are
      // deprecated by the OSM operations working group and just cost extra TLS
      // handshakes now that tiles are served over HTTP/2.
      url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      // OSM's tile servers refuse requests that arrive without a Referer
      // header, serving an "Access blocked" tile instead of the map. Some
      // browsers (notably privacy-hardened mobile ones and in-app webviews)
      // default to no-referrer, so set the policy explicitly on the tile
      // images rather than relying on the browser default. 'origin' sends
      // only https://sandpiper.qut.edu.au/, not the page being viewed.
      tile_layer_options: { referrerPolicy: 'origin' },
      attribution:
        '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',
      defaultCenter: latLng(0, 0),
      center: latLng(0, 0),
      zoom: default_zoom
    }
  },
  computed: {
    is_amplicon () {
      return this.dataset === 'amplicon'
    },
    is_query () {
      return this.query !== undefined && this.query !== null
    },
    queryDataset () {
      return this.is_amplicon ? 'amplicon' : 'metagenome'
    },
    // "environment: host, year: 2015, bog" -> one box per part:
    // [{key: 'environment', value: 'host'}, {key: 'year', value: '2015'}, {text: 'bog'}]
    query_parts () {
      return splitQueryParts(this.query || '').map(text => {
        const match = text.match(/^(\w[\w\s]*?)\s*:\s*(.*)$/)
        return match ? { text, key: match[1], value: unquoteQueryValue(match[2]) } : { text: unquoteQueryValue(text) }
      })
    },
    back_to_search () {
      return { name: 'Search', query: this.is_amplicon ? { mode: 'amplicon', q: this.query } : { q: this.query } }
    },
    // Whole percent, but never a misleading 0% or 100%: a few host runs among
    // thousands (e.g. 24 of 5,295) shows "<1%", a few ecological ones ">99%".
    host_percent () {
      const classified = this.num_host_runs + this.num_ecological_runs
      if (!classified) return '–'
      const percent = this.num_host_runs / classified * 100
      if (this.num_host_runs > 0 && percent < 1) return '<1%'
      if (this.num_ecological_runs > 0 && percent > 99) return '>99%'
      return `${Math.round(percent)}%`
    },
    query_markers_caption () {
      const shown = (this.num_lat_lon_runs || 0).toLocaleString('en-US')
      if (this.num_lat_lon_runs < this.total_lat_lon_runs) {
        return `${this.total_lat_lon_runs.toLocaleString('en-US')} runs have latitude/longitude; the first ${shown} by accession are shown below.`
      }
      return `${shown} run${this.num_lat_lon_runs === 1 ? '' : 's'} with latitude/longitude${this.cluster ? ' in your selected map cluster' : ''}.`
    },
    query_csv_link () {
      return queryCsvUrl(this.query, this.queryDataset, !this.is_amplicon && this.exclude_low_complexity, this.cluster,
        this.activeNicheFilters, this.taxonomy_type)
    },
    disableGtdb () {
      if (this.is_query) return !(this.query_taxon && this.query_taxon.taxonomy_types.includes('gtdb'))
      return this.taxonomy_type === 'globdb' && this.other_taxon_available === false
    },
    disableGlobdb () {
      if (this.is_query) return !(this.query_taxon && this.query_taxon.taxonomy_types.includes('globdb'))
      return this.taxonomy_type === 'gtdb' && this.other_taxon_available === false
    },
    // A taxonomy/taxon term that isn't a whole taxon name (e.g. "Prochlorococcus").
    query_names_partial_taxon () {
      const key = this.is_amplicon ? 'taxon' : 'taxonomy'
      return !this.query_taxon && this.query_parts.some(p => p.key && p.key.toLowerCase() === key && p.value)
    },
    query_names_low_complexity () {
      return this.query_parts.some(p => p.key && p.key.toLowerCase() === 'low_complexity')
    },
    low_complexity_count () {
      if (!this.search_result) return 0
      return this.search_result['condensed_profiles'].filter(
        r => r.top1_order_fraction !== null && r.top1_order_fraction >= 95
      ).length
    },
    filtered_profiles () {
      if (!this.search_result) return []
      if (!this.exclude_low_complexity) return this.search_result['condensed_profiles']
      return this.search_result['condensed_profiles'].filter(
        r => r.top1_order_fraction === null || r.top1_order_fraction < 95
      )
    },
    display_profiles () {
      return this.shuffled_profiles ?? this.filtered_profiles
    },
    activeNicheFilters () {
      if (this.mode !== 'niche') return undefined
      const niche = {}
      if (this.phOptions.length && (this.phMinIndex > 0 || this.phMaxIndex < this.phOptions.length - 1)) {
        niche.phMin = this.phOptions[this.phMinIndex]
        niche.phMax = this.phOptions[this.phMaxIndex]
      }
      if (this.temperatureOptions.length &&
        (this.temperatureMinIndex > 0 || this.temperatureMaxIndex < this.temperatureOptions.length - 1)) {
        niche.temperatureMin = this.temperatureOptions[this.temperatureMinIndex]
        niche.temperatureMax = this.temperatureOptions[this.temperatureMaxIndex]
      }
      if (this.hostAssociation) niche.hostAssociation = this.hostAssociation
      if (this.piperCommunity) niche.piperCommunity = this.piperCommunity
      return Object.keys(niche).length ? niche : undefined
    },
    phMinDisplay () {
      return this.phOptions[this.phMinIndex] ?? ''
    },
    phMaxDisplay () {
      return this.phOptions[this.phMaxIndex] ?? ''
    },
    temperatureMinDisplay () {
      return this.temperatureOptions[this.temperatureMinIndex] ?? ''
    },
    temperatureMaxDisplay () {
      return this.temperatureOptions[this.temperatureMaxIndex] ?? ''
    }
  },
  created () {
    // The template gates on search_result/total_num_results, so the page is
    // genuinely blank until this settles either way. Token captured now,
    // not read lazily inside .finally() -- see src/store/pageLoading.ts
    // for why a stale token must not clear a newer navigation's state.
    const loadingToken = currentLoadingToken()
    this.fetchGlobalData().finally(() => stopPageLoading(loadingToken))
  },
  methods: {
    reset_map: function () {
      this.center = latLng(this.defaultCenter.lat, this.defaultCenter.lng)
      this.zoom = default_zoom
    },
    // Local mode/filter state doesn't derive from the URL automatically like
    // taxonomy_type does -- pull it in from the route on every navigation
    // (toggle, back/forward, direct load of a shared link) before anything
    // refetches.
    syncNicheStateFromRoute () {
      const query = this.$route.query
      this.mode = query.mode === 'niche' ? 'niche' : 'geographic'
      // Back-compat: a bookmarked/shared link from before range support only
      // has the legacy single-value `ph`/`temperature` params -- treat that
      // as a min=max=value range rather than dropping the filter.
      this.routePhMin = query.ph_min !== undefined
        ? Number(query.ph_min)
        : (query.ph !== undefined ? Number(query.ph) : null)
      this.routePhMax = query.ph_max !== undefined
        ? Number(query.ph_max)
        : (query.ph !== undefined ? Number(query.ph) : null)
      this.routeTemperatureMin = query.temperature_min !== undefined
        ? Number(query.temperature_min)
        : (query.temperature !== undefined ? Number(query.temperature) : null)
      this.routeTemperatureMax = query.temperature_max !== undefined
        ? Number(query.temperature_max)
        : (query.temperature !== undefined ? Number(query.temperature) : null)
      this.hostAssociation = query.host_association || ''
      this.piperCommunity = query.piper_community || ''
    },
    // Slider position (indices into *Options) is a pure UI concern derived
    // from the selected bounds + the options list -- recompute it whenever
    // either changes, rather than storing it as the source of truth. An
    // unset bound resolves to the full extent (index 0 / last index), which
    // is what makes an unfiltered axis render as a full-span slider.
    syncSliderIndices () {
      this.phMinIndex = this.routePhMin !== null ? Math.max(0, this.phOptions.indexOf(this.routePhMin)) : 0
      this.phMaxIndex = this.routePhMax !== null
        ? Math.max(0, this.phOptions.indexOf(this.routePhMax))
        : Math.max(0, this.phOptions.length - 1)
      this.temperatureMinIndex = this.routeTemperatureMin !== null
        ? Math.max(0, this.temperatureOptions.indexOf(this.routeTemperatureMin))
        : 0
      this.temperatureMaxIndex = this.routeTemperatureMax !== null
        ? Math.max(0, this.temperatureOptions.indexOf(this.routeTemperatureMax))
        : Math.max(0, this.temperatureOptions.length - 1)
    },
    // Fetches the bucketed pH/temperature/host-association values available
    // for this taxon given whatever is currently selected (each axis
    // computed against the *other* two -- see /taxonomy_niche_options).
    // Returns true if the current selection turned out to be invalid under
    // the refreshed options and this method already corrected the URL via
    // router.replace -- the caller should stop, since the resulting $route
    // change re-invokes this same flow with the corrected filters. Clearing
    // a filter can only ever add back options for the other axes, never
    // remove more, so this converges within one extra round trip.
    async syncNicheOptions () {
      try {
        const selection = {
          phMin: this.routePhMin ?? undefined,
          phMax: this.routePhMax ?? undefined,
          temperatureMin: this.routeTemperatureMin ?? undefined,
          temperatureMax: this.routeTemperatureMax ?? undefined,
          hostAssociation: this.hostAssociation || undefined,
          piperCommunity: this.piperCommunity || undefined
        }
        const response = this.is_query
          ? await fetchQueryNicheOptions(this.query, this.queryDataset, selection)
          : await fetchTaxonomyNicheOptions(this.taxonomy, this.taxonomy_type, selection)
        this.phOptions = response.data.ph_options || []
        this.temperatureOptions = response.data.temperature_options || []
        this.hostAssociationOptions = response.data.host_association_options || []
        this.piperCommunityOptions = response.data.piper_community_options || []
      } catch (error) {
        // Surface it: a failed options request and a taxon with no data look
        // identical otherwise (both leave every axis at "Any" with no
        // explanation), which is exactly how a real 500 here went unnoticed.
        console.error('Failed to load Niche Mapping options', error)
        this.phOptions = []
        this.temperatureOptions = []
        this.hostAssociationOptions = []
        this.piperCommunityOptions = []
        return false
      }

      const phMinInvalid = this.routePhMin !== null && !this.phOptions.includes(this.routePhMin)
      const phMaxInvalid = this.routePhMax !== null && !this.phOptions.includes(this.routePhMax)
      const temperatureMinInvalid = this.routeTemperatureMin !== null &&
        !this.temperatureOptions.includes(this.routeTemperatureMin)
      const temperatureMaxInvalid = this.routeTemperatureMax !== null &&
        !this.temperatureOptions.includes(this.routeTemperatureMax)
      const hostInvalid = this.hostAssociation !== '' && !this.hostAssociationOptions.includes(this.hostAssociation)
      const piperCommunityInvalid = this.piperCommunity !== '' &&
        !this.piperCommunityOptions.includes(this.piperCommunity)

      if (phMinInvalid || phMaxInvalid || temperatureMinInvalid || temperatureMaxInvalid ||
        hostInvalid || piperCommunityInvalid) {
        const query = { ...this.$route.query }
        if (phMinInvalid || phMaxInvalid) { delete query.ph; delete query.ph_min; delete query.ph_max }
        if (temperatureMinInvalid || temperatureMaxInvalid) {
          delete query.temperature; delete query.temperature_min; delete query.temperature_max
        }
        if (hostInvalid) delete query.host_association
        if (piperCommunityInvalid) delete query.piper_community
        this.$router.replace({ name: this.$route.name, params: { taxonomy: this.taxonomy }, query })
        return true
      }

      this.syncSliderIndices()
      return false
    },
    async fetchGlobalData () {
      if (this.is_query) return this.fetchQueryPage()
      this.other_taxon_available = null
      this.error_message = null
      this.search_result = null
      this.total_num_results = null
      this.syncNicheStateFromRoute()

      const requestedTaxonomyType = this.is_amplicon ? 'amplicon' : this.$route.query.taxonomy_type

      // The niche-options lookup and the marker-map fetch below are
      // independent queries -- start it now rather than after awaiting the
      // marker map, so the two round trips overlap instead of stacking.
      // Only possible once the taxonomy type is already known; the cold-load
      // gtdb/globdb probe below resolves that first, so this stays null and
      // syncNicheOptions runs after it instead (rare path, first load only).
      const nicheOptionsPromise = (this.mode === 'niche' && requestedTaxonomyType)
        ? this.syncNicheOptions()
        : null

      if (requestedTaxonomyType) {
        const globalDataResult = await this.fetchGlobalDataForType(requestedTaxonomyType)
        if (!globalDataResult.success) {
          this.error_message = globalDataResult.error
          return
        }
        this.taxonomy_type = requestedTaxonomyType
        this.populateGlobalData(globalDataResult.data)
      } else {
        const detected = await this.determineInitialTaxonomyType()
        if (!detected) {
          return
        }
      }

      if (this.mode === 'niche') {
        const redirected = await (nicheOptionsPromise ?? this.syncNicheOptions())
        if (redirected) return
      } else {
        this.phOptions = []
        this.temperatureOptions = []
        this.hostAssociationOptions = []
        this.piperCommunityOptions = []
      }

      if (this.is_amplicon) this.other_taxonomy_type = null
      else this.other_taxonomy_type = this.taxonomy_type === 'gtdb' ? 'globdb' : 'gtdb'
      this.fetchData()
      this.checkOtherTaxonomyAvailability()
    },
    async fetchGlobalDataForType (taxonomyType) {
      try {
        const response = await fetchGlobalDataByTaxonomy(this.taxonomy, taxonomyType, this.activeNicheFilters)
        if (typeof response.data.total_num_results === 'number' && response.data.total_num_results > 0) {
          return { success: true, data: response.data }
        }
        const errorMessage = response.data && response.data.taxon ? response.data.taxon : 'No results found.'
        return { success: false, error: errorMessage }
      } catch (error) {
        return { success: false, error: error.message }
      }
    },
    // Search results: no GTDB/GlobDB probe or Niche Mapping, just the query's runs.
    async fetchQueryPage () {
      this.error_message = null
      this.search_result = null
      this.total_num_results = null
      this.cluster = null
      this.page = 1
      this.sortDirection = 'desc'
      this.taxonomy_type = this.is_amplicon ? 'amplicon' : (this.$route.query.taxonomy_type === 'globdb' ? 'globdb' : 'gtdb')
      this.syncNicheStateFromRoute()
      if (!this.query.trim()) {
        this.error_message = 'No search query given.'
        return
      }
      // Niche Mapping works here as on the taxonomy page (it filters on each
      // sample's own metadata). Load the slider options first, so the counts
      // below are fetched with the selection already applied.
      if (this.mode === 'niche') {
        if (await this.syncNicheOptions()) return
      } else {
        this.phOptions = []
        this.temperatureOptions = []
        this.hostAssociationOptions = []
        this.piperCommunityOptions = []
      }
      // The default sort only depends on the global-data response when the query
      // names a taxon (which adds relative abundance). Otherwise the summary and
      // the runs table are independent, so both requests go out together.
      const mayNameTaxon = /\btaxon(?:omy)?\s*:/i.test(this.query)
      if (!mayNameTaxon) {
        this.sortField = 'release_year'
        this.fetchData()
      }
      try {
        if (!(await this.requestGlobalData())) return
      } catch (error) {
        this.error_message = error.response?.data?.error || error.message
        return
      }
      if (mayNameTaxon) {
        // Like the taxonomy page: most abundant first when there is a taxon.
        this.sortField = this.query_taxon ? 'relative_abundance' : 'release_year'
        this.fetchData()
      }
    },
    // Summary + marker-map data for the current taxon or query (and map cluster).
    async requestGlobalData () {
      const request = ++this.global_request
      const response = this.is_query
        ? await fetchQueryGlobalData(this.query, this.queryDataset, this.cluster, this.activeNicheFilters)
        : await fetchGlobalDataByTaxonomy(this.taxonomy, this.taxonomy_type, this.activeNicheFilters, this.cluster)
      if (request !== this.global_request) return false
      this.populateGlobalData(response.data)
      return true
    },
    // The runs table for the current taxon or query; resolves true if this
    // was still the latest request and the table was filled.
    async requestRuns () {
      const request = ++this.runs_request
      const response = this.is_query
        ? await fetchQueryRunData(this.query, this.queryDataset, this.page, this.sortField, this.sortDirection,
          this.pageSize, !this.is_amplicon && this.exclude_low_complexity, this.cluster, this.activeNicheFilters,
          this.taxonomy_type)
        : await fetchRunsByTaxonomy(this.taxonomy, this.taxonomy_type, this.page, this.sortField, this.sortDirection,
          this.pageSize, this.exclude_low_complexity, this.cluster, this.activeNicheFilters)
      if (request !== this.runs_request) return false
      this.search_result = response.data.results
      this.filtered_total = response.data.results.filtered_total ?? null
      return true
    },
    populateGlobalData (data) {
      this.taxon_name = data.taxon_name
      this.lineage = data.lineage
      this.taxonomy_level = data.taxonomy_level
      this.total_num_results = data.total_num_results
      this.lat_lons = data.lat_lons
      this.lat_lons_min_relabund = data.lat_lons_min_relabund
      this.num_lat_lon_runs = data.num_lat_lon_runs
      this.total_lat_lon_runs = data.total_lat_lon_runs ?? 0
      this.num_low_complexity_runs = data.num_low_complexity_runs ?? 0
      if (this.is_query) this.query_taxon = data.taxon ?? null
      this.num_host_runs = data.num_host_runs
      this.num_ecological_runs = data.num_ecological_runs
      this.num_realms = data.num_realms ?? null
      this.center = latLng(this.defaultCenter.lat, this.defaultCenter.lng)
    },
    async determineInitialTaxonomyType () {
      const gtdbResult = await this.fetchGlobalDataForType('gtdb')
      if (gtdbResult.success) {
        this.taxonomy_type = 'gtdb'
        this.populateGlobalData(gtdbResult.data)
        return true
      }

      const globdbResult = await this.fetchGlobalDataForType('globdb')
      if (globdbResult.success) {
        this.taxonomy_type = 'globdb'
        this.populateGlobalData(globdbResult.data)
        return true
      }

      this.error_message = globdbResult.error || gtdbResult.error || 'No results found.'
      return false
    },
    async checkOtherTaxonomyAvailability () {
      if (!this.other_taxonomy_type) {
        this.other_taxon_available = null
        return
      }
      try {
        const response = await fetchGlobalDataByTaxonomy(this.taxonomy, this.other_taxonomy_type)
        this.other_taxon_available = typeof response.data.total_num_results === 'number' && response.data.total_num_results > 0
      } catch (error) {
        this.other_taxon_available = false
      }
    },
    fetchData () {
      if (!this.taxonomy_type) {
        return
      }
      this.search_result = null

      this.requestRuns()
    },
    onTaxonomyTypeChange (value) {
      if (value === this.$route.query.taxonomy_type) {
        return
      }
      if (this.is_query) {
        // Same search, abundance from the other database.
        this.$router.push({ name: this.$route.name, query: { ...this.$route.query, taxonomy_type: value } })
        return
      }

      this.$router.push({
        name: 'SearchResults',
        params: { taxonomy: this.taxonomy },
        query: { taxonomy_type: value }
      })
    },
    onModeChange (value) {
      if (value === this.mode && value === (this.$route.query.mode || 'geographic')) {
        return
      }

      const query = { ...this.$route.query }
      if (value === 'niche') {
        query.mode = 'niche'
      } else {
        delete query.mode
      }
      this.page = 1
      this.$router.push({ name: this.$route.name, params: { taxonomy: this.taxonomy }, query })
    },
    // b-slider's built-in drag tooltip otherwise shows the raw index (its own
    // 0..N model value), not the actual bucketed pH/temperature the index
    // maps to -- that mismatch was the "shows 8 while dragging, jumps to 17
    // on release" bug. These map the index through the same *Options array
    // the change handlers below use, so the tooltip always agrees with the
    // released value.
    formatPhIndex (index) {
      return this.phOptions[index] !== undefined ? String(this.phOptions[index]) : ''
    },
    formatTemperatureIndex (index) {
      return this.temperatureOptions[index] !== undefined ? String(this.temperatureOptions[index]) : ''
    },
    // The nearest available bucket to a typed value -- editable inputs can't
    // land on an arbitrary number, only on values the slider actually stops
    // at (same values /taxonomy_niche_options returned).
    nearestOptionIndex (value, options) {
      let nearest = 0
      let nearestDiff = Infinity
      options.forEach((option, index) => {
        const diff = Math.abs(option - value)
        if (diff < nearestDiff) {
          nearestDiff = diff
          nearest = index
        }
      })
      return nearest
    },
    onPhRangeChange ([minIndex, maxIndex]) {
      this.phMinIndex = minIndex
      this.phMaxIndex = maxIndex
      this.pushNicheFilterQuery()
    },
    onTemperatureRangeChange ([minIndex, maxIndex]) {
      this.temperatureMinIndex = minIndex
      this.temperatureMaxIndex = maxIndex
      this.pushNicheFilterQuery()
    },
    onPhMinInput (rawValue) {
      const value = Number(rawValue)
      if (rawValue === '' || Number.isNaN(value)) return
      this.phMinIndex = Math.min(this.nearestOptionIndex(value, this.phOptions), this.phMaxIndex)
      this.pushNicheFilterQuery()
    },
    onPhMaxInput (rawValue) {
      const value = Number(rawValue)
      if (rawValue === '' || Number.isNaN(value)) return
      this.phMaxIndex = Math.max(this.nearestOptionIndex(value, this.phOptions), this.phMinIndex)
      this.pushNicheFilterQuery()
    },
    onTemperatureMinInput (rawValue) {
      const value = Number(rawValue)
      if (rawValue === '' || Number.isNaN(value)) return
      this.temperatureMinIndex = Math.min(
        this.nearestOptionIndex(value, this.temperatureOptions), this.temperatureMaxIndex
      )
      this.pushNicheFilterQuery()
    },
    onTemperatureMaxInput (rawValue) {
      const value = Number(rawValue)
      if (rawValue === '' || Number.isNaN(value)) return
      this.temperatureMaxIndex = Math.max(
        this.nearestOptionIndex(value, this.temperatureOptions), this.temperatureMinIndex
      )
      this.pushNicheFilterQuery()
    },
    onHostAssociationChange (value) {
      this.hostAssociation = value
      this.pushNicheFilterQuery()
    },
    onPiperCommunityChange (value) {
      this.piperCommunity = value
      this.pushNicheFilterQuery()
    },
    resetNicheFilters () {
      this.phMinIndex = 0
      this.phMaxIndex = Math.max(0, this.phOptions.length - 1)
      this.temperatureMinIndex = 0
      this.temperatureMaxIndex = Math.max(0, this.temperatureOptions.length - 1)
      this.hostAssociation = ''
      this.piperCommunity = ''
      this.pushNicheFilterQuery()
    },
    // Pushes the current slider/dropdown values into the URL, which the
    // $route watcher below (fetchGlobalData) picks up to refetch the maps
    // and table -- same round trip onModeChange/onTaxonomyTypeChange use.
    pushNicheFilterQuery () {
      const query = { ...this.$route.query, mode: 'niche' }
      for (const key of ['ph', 'ph_min', 'ph_max', 'temperature', 'temperature_min', 'temperature_max',
        'host_association', 'piper_community']) {
        delete query[key]
      }
      const niche = this.activeNicheFilters
      if (niche) {
        if (niche.phMin !== undefined) query.ph_min = niche.phMin
        if (niche.phMax !== undefined) query.ph_max = niche.phMax
        if (niche.temperatureMin !== undefined) query.temperature_min = niche.temperatureMin
        if (niche.temperatureMax !== undefined) query.temperature_max = niche.temperatureMax
        if (niche.hostAssociation) query.host_association = niche.hostAssociation
        if (niche.piperCommunity) query.piper_community = niche.piperCommunity
      }
      this.page = 1
      this.$router.push({ name: this.$route.name, params: { taxonomy: this.taxonomy }, query })
    },
    onPageChange (page) {
      this.page = page
      this.fetchData()
    },
    onSort (field, direction) {
      const scrollY = window.scrollY
      this.sortField = field
      this.sortDirection = direction
      this.requestRuns()
        .then(isCurrent => { if (isCurrent) this.$nextTick(() => window.scrollTo(0, scrollY)) })
    },
    numericColumnTdAttrs (_row, _column) {
      return {
        style: 'text-align: center;'
      }
    },
    html_for_map_popup (markerLatLng) {
      let toReturn = ''
      Object.entries(markerLatLng.samples).forEach((description_samples) => {
        toReturn += '<p>' + description_samples[0] + '</p>'
        toReturn += '<ul>'
        description_samples[1].forEach((sample) => {
          toReturn += '<li><a href="' + this.run_path(sample) + '">' + sample + '</a></li>'
        })
        toReturn += '</ul>'
      })
      return toReturn
    },
    onClusterSelected (cluster) {
      // Filtering happens server-side, so reset to page 1 and refetch. The
      // filter is deliberately sticky: it clears only on navigating back or
      // reloading, which is what makes the run list and the random button
      // agree on the same subset.
      //
      // Deliberately NOT calling fetchData() here: it nulls search_result
      // synchronously, which unmounts the whole v-if="search_result !== null"
      // container (map included) until the refetch resolves. That collapses
      // the page and snaps window scroll to the top before scrollIntoView
      // below ever gets a #matching-samples element to target. Fetching
      // directly and swapping search_result in place (same pattern as
      // onSort/exclude_low_complexity) keeps the page mounted throughout.
      this.cluster = cluster
      this.page = 1
      this.shuffled_profiles = null
      this.requestRuns()

      // Also refetches the global/summary data (lat_lons, num_lat_lon_runs,
      // total_num_results) scoped to this cluster -- without this, the
      // Individual Runs map below only pans/zooms to the cluster while still
      // showing (and describing, via num_lat_lon_runs/total_num_results in
      // the template) every marker for the whole taxon, which contradicts
      // what's actually on screen once zoomed in.
      this.requestGlobalData()

      // Zoom the marker map to the cluster, then bring it into view. This is
      // the "Individual runs" l-map (id="individual-runs-map") that actually
      // pans/zooms to the cluster -- not #matching-samples further down,
      // which is a different section (the results table).
      //
      // Keep these in sync for reset_map()/display purposes, but don't rely
      // on the :zoom.sync/:center.sync props alone to move the map: Vue only
      // pushes a prop update through when the value actually changes, so
      // clicking a second cluster that also wants zoom 6 (identical to the
      // previous click's target) is a silent no-op -- the map pans (center
      // differs) but never re-zooms. Calling setView() on the underlying
      // Leaflet instance directly applies every click regardless of whether
      // the target zoom repeats.
      this.center = latLng(cluster.lat, cluster.lon)
      this.zoom = 6
      this.$nextTick(() => {
        const mapComponent = this.$refs.individualRunsMap
        if (mapComponent && mapComponent.leafletObject) {
          mapComponent.leafletObject.setView([cluster.lat, cluster.lon], 6)
        }
        const target = document.getElementById('individual-runs-map')
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' })
      })
    },
    clearCluster () {
      this.cluster = null
      this.page = 1
      this.shuffled_profiles = null
      this.fetchData()
      // fetchData() above only refetches the table -- restore the global/
      // summary data (lat_lons, num_lat_lon_runs, total_num_results) back to
      // its unfiltered state too, matching what onClusterSelected() scoped
      // down when the cluster was first selected.
      this.requestGlobalData()
    },
    shuffle_runs () {
      const arr = [...this.filtered_profiles]
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]]
      }
      this.shuffled_profiles = arr
    },
    niche_query_suffix () {
      const niche = this.activeNicheFilters
      if (!niche) return ''
      let suffix = ''
      if (niche.ph !== undefined) suffix += '&ph=' + niche.ph
      if (niche.temperature !== undefined) suffix += '&temperature=' + niche.temperature
      if (niche.hostAssociation) suffix += '&host_association=' + niche.hostAssociation
      if (niche.piperCommunity) suffix += '&piper_community=' + encodeURIComponent(niche.piperCommunity)
      return suffix
    },
    run_path (acc) {
      return (this.is_amplicon ? '/amplicon/run/' : '/run/') + acc
    },
    csv_link () {
      return taxonomyApiUrl(this.taxonomy_type) + '/taxonomy_search_csv/' + this.taxonomy + '?taxonomy_type=' + this.taxonomy_type + this.niche_query_suffix()
    },
    minimal_csv_link () {
      return taxonomyApiUrl(this.taxonomy_type) + '/taxonomy_search_csv_minimal/' + this.taxonomy + '?taxonomy_type=' + this.taxonomy_type + this.niche_query_suffix()
    },
    shuffle_runs () {
      const arr = [...this.filtered_profiles]
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]]
      }
      this.shuffled_profiles = arr
    }
  },
  watch: {
    $route: 'fetchGlobalData',
    filtered_profiles () {
      this.shuffled_profiles = null
    },
    // A query that filters on low_complexity itself (e.g. "low_complexity: yes")
    // turns the switch off -- otherwise "yes" plus the default exclusion
    // empties the table while the count above still says hundreds. Declared
    // before the exclude_low_complexity watcher so the immediate run on load
    // doesn't trigger a second runs request.
    query_names_low_complexity: {
      handler (names) { if (names) this.exclude_low_complexity = false },
      immediate: true
    },
    exclude_low_complexity () {
      const scrollY = window.scrollY
      this.page = 1
      this.requestRuns()
        .then(isCurrent => { if (isCurrent) this.$nextTick(() => window.scrollTo(0, scrollY)) })
    }
  }
}
</script>

<style scoped>
/* Search results heading: one box per query part under the title, so several
   parts stay easy to tell apart. Smaller than the title; within each box the
   search term (key) stands out more than the user's value. */
.search-topic-title {
  text-align: center;
  margin-bottom: 0.5rem;
}
.query-parts {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.query-part {
  display: inline-flex;
  align-items: baseline;
  gap: 0.4rem;
  padding: 0.3rem 0.9rem;
  border: 1px solid hsl(174, 25%, 82%);
  border-radius: 8px;
  background: hsl(174, 25%, 97%);
  font-size: 1.1rem;
  overflow-wrap: anywhere;
}
.query-part-key {
  font-weight: 700;
  color: hsl(174, 62%, 22%);
}
.query-part-value {
  font-weight: 400;
  color: hsl(0, 0%, 35%);
}
.shuffle-btn {
  background: transparent;
  border: none;
  box-shadow: none;
  color: #aaa;
}
.shuffle-btn:hover,
.shuffle-btn:focus,
.shuffle-btn:active,
.shuffle-btn:focus:not(:active) {
  background: transparent;
  border: none;
  box-shadow: none;
  color: #111;
  outline: none;
}

.section-hint {
  margin-top: 0.15rem;
  margin-bottom: 1rem;
}
.section-heading-spaced {
  margin-top: 1.75rem;
}
.individual-runs-caption {
  margin-bottom: 0.4rem;
}

.cluster-filter {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}
.matching-count-caption {
  text-align: center;
}
.niche-mapping-panel {
  max-width: 720px;
  margin: 0 auto 1.5rem;
  padding: var(--space-6);
  background: hsl(174, 25%, 98.5%);
  border: 1px solid hsl(174, 25%, 91%);
  border-radius: 12px;
  text-align: left;
}
.niche-mapping-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}
.niche-mapping-eyebrow {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: hsl(174, 62%, 24%);
  margin: 0;
}
.niche-mapping-help {
  margin-top: var(--space-1);
  margin-bottom: var(--space-4);
}
.niche-field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 var(--space-6);
}
.niche-field {
  min-width: 0;
}
.niche-slider-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
}
.niche-slider-row :deep(.b-slider) {
  flex: 1 1 auto;
}
.niche-range-input {
  flex: 0 0 auto;
  width: 3.75rem;
  min-height: 32px;
  padding: 0.2rem 0.4rem;
  border: 1px solid hsl(174, 25%, 82%);
  border-radius: 6px;
  background: #fff;
  font-variant-numeric: tabular-nums;
  font-size: 0.85rem;
  color: #444;
  text-align: center;
}
.niche-range-input:focus-visible {
  outline: 2px solid hsl(174, 62%, 28%);
  outline-offset: 1px;
}
.individual-runs-map {
  width: 100%;
  height: 900px;
  max-width: 100%;
}
.map-reset-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1.25rem;
}
.map-reset {
  appearance: none;
  min-height: 44px;
  border: 0;
  padding: 0.4rem 0;
  background: transparent;
  color: #3273dc;
  cursor: pointer;
  font: inherit;
}
.map-reset:focus-visible {
  outline: 2px solid #3273dc;
  outline-offset: 2px;
}
.results-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.mapping-mode-switcher {
  margin-bottom: 1.25rem;
}
.low-complexity-summary {
  align-self: center;
  font-weight: bold;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.mobile-shuffle-button {
  display: none;
}

@media (max-width: 768px) {
  .taxonomy-switcher :deep(.field-body > .field.is-grouped) {
    flex-wrap: wrap;
  }
  .niche-mapping-panel {
    padding: var(--space-4);
  }
  .niche-field-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 0;
  }
  /* Buefy's default slider thumb (1rem/16px) is well under a comfortable
     touch target -- fine for a mouse pointer, but a real problem for a
     *range* slider on a phone where two thumbs can sit close together and
     need to be grabbed individually with a fingertip. Enlarge the thumb,
     track and tick marks together so the track still reads as one
     proportioned control, not just a bigger dot on a thin line. */
  .niche-slider-row :deep(.b-slider-thumb) {
    height: 1.5rem;
    width: 1.5rem;
  }
  .niche-slider-row :deep(.b-slider-track) {
    height: 0.75rem;
  }
  .niche-slider-row :deep(.b-slider-tick) {
    height: 0.375rem;
  }
  .niche-range-input {
    min-height: 44px;
    width: 4.5rem;
  }
  .individual-runs-map {
    height: clamp(320px, 60vh, 500px);
    height: clamp(320px, 60dvh, 500px);
  }
  .results-actions {
    align-items: stretch;
    flex-direction: column;
  }
  .results-actions :deep(.button),
  .results-actions :deep(.switch) {
    justify-content: center;
    width: 100%;
    max-width: 100%;
    min-height: 44px;
    height: auto;
    white-space: normal;
  }
  .mobile-shuffle-button {
    display: inline-flex;
  }
  .bd-anchor-title {
    font-size: 1.65rem;
    line-height: 1.2;
  }
  .low-complexity-summary {
    align-self: stretch;
  }
}

@media (max-width: 430px) {
  .taxonomy-switcher :deep(.field-body > .field.is-grouped),
  .mapping-mode-switcher :deep(.field-body > .field.is-grouped) {
    align-items: stretch;
    flex-direction: column;
  }
  .taxonomy-switcher :deep(.control),
  .taxonomy-switcher :deep(.button),
  .mapping-mode-switcher :deep(.control),
  .mapping-mode-switcher :deep(.button) {
    width: 100%;
  }
  .taxonomy-switcher :deep(.button),
  .mapping-mode-switcher :deep(.button) {
    justify-content: flex-start;
    min-height: 44px;
    height: auto;
    white-space: normal;
  }
}
</style>
