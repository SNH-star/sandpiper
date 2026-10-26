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
        <div v-if="query_taxon" class="has-text-centered taxonomy-switcher">
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
        <p v-else-if="query_names_partial_taxon" class="has-text-centered help">
          Give a full taxon name (e.g. g__Prochlorococcus) to see relative abundance and coverage.
        </p>
        <p class="has-text-centered help">
          Metagenome runs matching this search.
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
        <div class="has-text-centered taxonomy-switcher">
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
          <div class="level-item has-text-centered">
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

          <h3 class="subtitle is-4">Sample distribution</h3>
          <p class="help section-hint">
            This map is interactive &mdash; click a cluster to zoom in and filter the samples table and the Individual runs map below.
          </p>
          <TaxonomySampleMap :taxon="taxonomy" :query="query" :taxonomy-type="taxonomy_type"
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
          <b-switch v-model="exclude_low_complexity">Exclude low complexity</b-switch>
          <span v-if="!exclude_low_complexity" class="low-complexity-summary">{{ is_query ? num_low_complexity_runs : low_complexity_count }} / {{ total_num_results }} runs have ≥95% reads from one order (Low Complexity)</span>
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

          <b-table-column field='release_year' label="Release year" v-slot="props" centered sortable>
            {{ props.row.release_year }}
          </b-table-column>

          <b-table-column v-if="!is_query || query_taxon" field='relative_abundance' label='Relative abundance (%)' v-slot="props" centered sortable>
            {{ props.row.relative_abundance ?? '–' }}
          </b-table-column>

          <b-table-column v-if="!is_query || query_taxon" field='coverage' label="Genome coverage" v-slot="props" centered sortable>
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
  fetchGlobalDataByTaxonomy, fetchRunsByTaxonomy, api_url,
  fetchQueryGlobalData, fetchQueryRunData, queryCsvUrl
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
    return `Runs with ${this.taxonomy} - Sandpiper`
  },
  // query: set instead of taxonomy by "Explore tabled results" on the advanced
  // search (/search/results?q=) -- the page then shows every run matching it.
  props: ['taxonomy', 'query'],
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
    is_query () {
      return this.query !== undefined && this.query !== null
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
      return { name: 'Search', query: { q: this.query } }
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
      return queryCsvUrl(this.query, this.exclude_low_complexity, this.cluster, this.taxonomy_type)
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
      return !this.query_taxon && this.query_parts.some(p => p.key && p.key.toLowerCase() === 'taxonomy' && p.value)
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
    async fetchGlobalData () {
      if (this.is_query) return this.fetchQueryPage()
      this.other_taxon_available = null
      this.error_message = null
      this.search_result = null
      this.total_num_results = null

      const requestedTaxonomyType = this.$route.query.taxonomy_type

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

      this.other_taxonomy_type = this.taxonomy_type === 'gtdb' ? 'globdb' : 'gtdb'
      this.fetchData()
      this.checkOtherTaxonomyAvailability()
    },
    async fetchGlobalDataForType (taxonomyType) {
      try {
        const response = await fetchGlobalDataByTaxonomy(this.taxonomy, taxonomyType)
        if (typeof response.data.total_num_results === 'number' && response.data.total_num_results > 0) {
          return { success: true, data: response.data }
        }
        const errorMessage = response.data && response.data.taxon ? response.data.taxon : 'No results found.'
        return { success: false, error: errorMessage }
      } catch (error) {
        return { success: false, error: error.message }
      }
    },
    // Search results: no GTDB/GlobDB probe, just the query's runs.
    async fetchQueryPage () {
      this.error_message = null
      this.search_result = null
      this.total_num_results = null
      this.cluster = null
      this.page = 1
      this.sortDirection = 'desc'
      this.taxonomy_type = this.$route.query.taxonomy_type === 'globdb' ? 'globdb' : 'gtdb'
      if (!this.query.trim()) {
        this.error_message = 'No search query given.'
        return
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
        ? await fetchQueryGlobalData(this.query, this.cluster)
        : await fetchGlobalDataByTaxonomy(this.taxonomy, this.taxonomy_type, this.cluster)
      if (request !== this.global_request) return false
      this.populateGlobalData(response.data)
      return true
    },
    // The runs table for the current taxon or query; resolves true if this
    // was still the latest request and the table was filled.
    async requestRuns () {
      const request = ++this.runs_request
      const response = this.is_query
        ? await fetchQueryRunData(this.query, this.page, this.sortField, this.sortDirection,
          this.pageSize, this.exclude_low_complexity, this.cluster,
          this.taxonomy_type)
        : await fetchRunsByTaxonomy(this.taxonomy, this.taxonomy_type, this.page, this.sortField, this.sortDirection,
          this.pageSize, this.exclude_low_complexity, this.cluster)
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
    run_path (acc) {
      return '/run/' + acc
    },
    csv_link () {
      return api_url() + '/taxonomy_search_csv/' + this.taxonomy + '?taxonomy_type=' + this.taxonomy_type
    },
    minimal_csv_link () {
      return api_url() + '/taxonomy_search_csv_minimal/' + this.taxonomy + '?taxonomy_type=' + this.taxonomy_type
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
  .taxonomy-switcher :deep(.field-body > .field.is-grouped) {
    align-items: stretch;
    flex-direction: column;
  }
  .taxonomy-switcher :deep(.control),
  .taxonomy-switcher :deep(.button) {
    width: 100%;
  }
  .taxonomy-switcher :deep(.button) {
    justify-content: flex-start;
    min-height: 44px;
    height: auto;
    white-space: normal;
  }
}
</style>
