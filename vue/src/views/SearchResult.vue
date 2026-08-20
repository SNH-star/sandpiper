<template>
  <section class="section">
    <div v-if="search_result !== null && total_num_results !== null" class="container">
      <section class="section">
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
                  <p class="title"> {{ Math.round((num_host_runs/(num_host_runs+num_ecological_runs)*100)) }}%</p>
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
                  <p class="title" v-if="num_lat_lon_runs < 1000">{{ num_lat_lon_runs.toLocaleString("en-US") }}</p>
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
              <b-radio-button v-model="mode" native-value="geographic" type="is-info"
                @input="onModeChange('geographic')">
                Geographical Mapping
              </b-radio-button>
              <b-radio-button v-model="mode" native-value="niche" type="is-warning"
                @input="onModeChange('niche')">
                Niche Mapping
              </b-radio-button>
            </b-field>
          </div>
          <br />

          <div v-if="mode === 'niche'" class="niche-mapping-panel">
            <div class="niche-mapping-panel-header">
              <h3 class="subtitle is-4">Niche Mapping</h3>
              <b-button v-if="activeNicheFilters" type="is-text" size="is-small" icon-left="close"
                @click="resetNicheFilters">
                Reset filters
              </b-button>
            </div>
            <p class="help">
              Filter the maps and matching samples below by pH, temperature,
              host association, and Piper community. Sliders only stop on
              values actually present for this taxon, and narrow each other
              as you pick.
            </p>

            <b-field label="pH">
              <div v-if="phOptions.length" class="niche-slider-row">
                <b-slider v-model="phIndex" :min="0" :max="phOptions.length" :step="1" ticks
                  :custom-formatter="formatPhIndex" @change="onPhIndexChange" />
                <span class="niche-slider-value">{{ ph !== null ? ph : 'Any' }}</span>
              </div>
              <p v-else class="help">No pH data available for the current filters.</p>
            </b-field>

            <b-field label="Temperature (°C)">
              <div v-if="temperatureOptions.length" class="niche-slider-row">
                <b-slider v-model="temperatureIndex" :min="0" :max="temperatureOptions.length" :step="1" ticks
                  :custom-formatter="formatTemperatureIndex" @change="onTemperatureIndexChange" />
                <span class="niche-slider-value">{{ temperature !== null ? temperature : 'Any' }}</span>
              </div>
              <p v-else class="help">No temperature data available for the current filters.</p>
            </b-field>

            <b-field label="Host association">
              <b-select v-model="hostAssociation" @update:model-value="onHostAssociationChange">
                <option value="">Any</option>
                <option v-for="opt in hostAssociationOptions" :key="opt" :value="opt">
                  {{ opt === 'host' ? 'Host-associated' : 'Ecological' }}
                </option>
              </b-select>
            </b-field>

            <b-field label="Piper community">
              <div v-if="piperCommunityOptions.length">
                <b-select v-model="piperCommunity" @update:model-value="onPiperCommunityChange">
                  <option value="">Any</option>
                  <option v-for="opt in piperCommunityOptions" :key="opt" :value="opt">
                    {{ opt }}
                  </option>
                </b-select>
              </div>
              <p v-else class="help">No IndicPiper community data available for the current filters.</p>
            </b-field>
          </div>

          <h3 class="subtitle is-4">Sample distribution</h3>
          <TaxonomySampleMap :taxon="taxonomy" :taxonomy-type="taxonomy_type" :niche-filters="activeNicheFilters"
            @cluster-selected="onClusterSelected" />
          <br />

          <h3 class="subtitle is-4">Individual runs</h3>
          <div v-if="this.num_lat_lon_runs < 1000">
            {{ this.num_lat_lon_runs.toLocaleString("en-US") }} runs have relative abundance >= 
            {{ parseFloat((this.lat_lons_min_relabund*100).toPrecision(2))}}% and associated latitude/longitude metadata.
          </div>
          <div v-else>
            1,000+ runs have associated latitude/longitude metadata. The 1000 runs with relative abundance 
            >= {{ parseFloat((this.lat_lons_min_relabund*100).toPrecision(2))}}% are shown below.
          </div>
          <br /><p>{{ (total_num_results - num_lat_lon_runs).toLocaleString("en-US") }} other runs are not shown on this map.</p><br />
          
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
          <b-button tag="a" type="is-info" :href="minimal_csv_link()">Download minimal CSV</b-button>
          <b-button tag="a" type="is-info" :href="csv_link()">Download CSV with extra columns</b-button>
          <b-button type="is-light" icon-left="shuffle-variant" class="mobile-shuffle-button" @click="shuffle_runs">Shuffle runs</b-button>
          <b-switch v-model="exclude_low_complexity">Exclude low complexity</b-switch>
          <span v-if="!exclude_low_complexity" class="low-complexity-summary">{{ low_complexity_count }} / {{ total_num_results }} runs have ≥95% reads from one order (Low Complexity)</span>
        </div>
        <br />
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
          @page-change="onPageChange"
          @sort="onSort">

          <b-table-column field='sample_name' useSorted>
            <template #header>
              <span style="display: flex; align-items: center; gap: 0.4rem;">
                Run
                <b-button class="shuffle-btn" size="is-small" icon-left="shuffle-variant" @click.stop="shuffle_runs" title="Shuffle order" />
              </span>
            </template>
            <template #default="props">
              <a :href="'/run/' + props.row.sample_acc">{{ props.row.sample_acc }}</a>
            </template>
          </b-table-column>

          <b-table-column field='organism' label='Environment' v-slot="props" sortable>
            {{ props.row.organism }}
          </b-table-column>

          <b-table-column field='release_year' label='Release year' v-slot="props" centered sortable>
            {{ props.row.release_year }}
          </b-table-column>

          <b-table-column field='relative_abundance' label='Relative abundance (%)' v-slot="props" centered sortable>
            {{ props.row.relative_abundance }}
          </b-table-column>

          <b-table-column field='coverage' label='Coverage' v-slot="props" centered sortable>
            {{ props.row.coverage }}
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
import { api_url, fetchGlobalDataByTaxonomy, fetchRunsByTaxonomy, fetchTaxonomyNicheOptions } from '@/api'
import { GTDB_VERSION, GLOBDB_VERSION } from '@/versions'

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
    return `Runs with ${this.taxonomy} - Sandpiper`
  },
  props: ['taxonomy'],
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
      // ph/temperature: selected bucket value, or null for "Any". phIndex/
      // temperatureIndex are the slider's own position (0 = Any, i = the
      // i-1'th entry of the matching *Options array) -- kept in sync with
      // ph/temperature by syncSliderIndices(), since b-slider needs a plain
      // numeric v-model rather than reasoning about null or a value list.
      ph: null,
      temperature: null,
      phIndex: 0,
      temperatureIndex: 0,
      phOptions: [],
      temperatureOptions: [],
      hostAssociation: '',
      hostAssociationOptions: [],
      piperCommunity: '',
      piperCommunityOptions: [],

      lat_lons: null,
      lat_lons_min_relabund: null,
      num_lat_lon_runs: null,
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
    disableGtdb () {
      return this.taxonomy_type === 'globdb' && this.other_taxon_available === false
    },
    disableGlobdb () {
      return this.taxonomy_type === 'gtdb' && this.other_taxon_available === false
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
      if (this.ph !== null) niche.ph = this.ph
      if (this.temperature !== null) niche.temperature = this.temperature
      if (this.hostAssociation) niche.hostAssociation = this.hostAssociation
      if (this.piperCommunity) niche.piperCommunity = this.piperCommunity
      return Object.keys(niche).length ? niche : undefined
    }
  },
  created () {
    // fetch the data when the view is created and the data is
    // already being observed
    this.fetchGlobalData()
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
      this.ph = query.ph !== undefined ? Number(query.ph) : null
      this.temperature = query.temperature !== undefined ? Number(query.temperature) : null
      this.hostAssociation = query.host_association || ''
      this.piperCommunity = query.piper_community || ''
    },
    // Slider position (an index into *Options) is a pure UI concern derived
    // from the selected value + the options list -- recompute it whenever
    // either changes, rather than storing it as the source of truth.
    syncSliderIndices () {
      this.phIndex = this.ph !== null ? this.phOptions.indexOf(this.ph) + 1 : 0
      this.temperatureIndex = this.temperature !== null ? this.temperatureOptions.indexOf(this.temperature) + 1 : 0
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
        const response = await fetchTaxonomyNicheOptions(this.taxonomy, this.taxonomy_type, {
          ph: this.ph ?? undefined,
          temperature: this.temperature ?? undefined,
          hostAssociation: this.hostAssociation || undefined,
          piperCommunity: this.piperCommunity || undefined
        })
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

      const phInvalid = this.ph !== null && !this.phOptions.includes(this.ph)
      const temperatureInvalid = this.temperature !== null && !this.temperatureOptions.includes(this.temperature)
      const hostInvalid = this.hostAssociation !== '' && !this.hostAssociationOptions.includes(this.hostAssociation)
      const piperCommunityInvalid = this.piperCommunity !== '' &&
        !this.piperCommunityOptions.includes(this.piperCommunity)

      if (phInvalid || temperatureInvalid || hostInvalid || piperCommunityInvalid) {
        const query = { ...this.$route.query }
        if (phInvalid) delete query.ph
        if (temperatureInvalid) delete query.temperature
        if (hostInvalid) delete query.host_association
        if (piperCommunityInvalid) delete query.piper_community
        this.$router.replace({ name: 'SearchResults', params: { taxonomy: this.taxonomy }, query })
        return true
      }

      this.syncSliderIndices()
      return false
    },
    async fetchGlobalData () {
      this.other_taxon_available = null
      this.error_message = null
      this.search_result = null
      this.total_num_results = null
      this.syncNicheStateFromRoute()

      const requestedTaxonomyType = this.$route.query.taxonomy_type

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

      this.other_taxonomy_type = this.taxonomy_type === 'gtdb' ? 'globdb' : 'gtdb'
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
    populateGlobalData (data) {
      this.taxon_name = data.taxon_name
      this.lineage = data.lineage
      this.taxonomy_level = data.taxonomy_level
      this.total_num_results = data.total_num_results
      this.lat_lons = data.lat_lons
      this.lat_lons_min_relabund = data.lat_lons_min_relabund
      this.num_lat_lon_runs = data.num_lat_lon_runs
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

      fetchRunsByTaxonomy(this.taxonomy, this.taxonomy_type, this.page, this.sortField, this.sortDirection, this.pageSize, this.exclude_low_complexity, this.cluster, this.activeNicheFilters)
        .then(response => {
          this.search_result = response.data.results
          this.filtered_total = response.data.results.filtered_total ?? null
        })
    },
    onTaxonomyTypeChange (value) {
      if (value === this.$route.query.taxonomy_type) {
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
      this.$router.push({ name: 'SearchResults', params: { taxonomy: this.taxonomy }, query })
    },
    // Buefy's v-model update and the @change/@input event on the same
    // element aren't guaranteed to land in the order the template lists them
    // under Vue 3, so reading `this.ph`/`this.hostAssociation` etc. here can
    // see a stale value from before the user's change. Each handler below
    // takes the emitted value directly instead, so the pushed URL always
    // matches what the user just picked -- this is what map/table refetches
    // ultimately read. Index 0 is the "Any" slider stop.
    // b-slider's built-in drag tooltip otherwise shows the raw index (its own
    // 0..N model value), not the actual bucketed pH/temperature the index
    // maps to -- that mismatch was the "shows 8 while dragging, jumps to 17
    // on release" bug. These map the index through the same *Options array
    // the change handlers below use, so the tooltip always agrees with the
    // released value.
    formatPhIndex (index) {
      return index > 0 ? String(this.phOptions[index - 1]) : 'Any'
    },
    formatTemperatureIndex (index) {
      return index > 0 ? String(this.temperatureOptions[index - 1]) : 'Any'
    },
    onPhIndexChange (index) {
      this.phIndex = index
      this.ph = index > 0 ? this.phOptions[index - 1] : null
      this.pushNicheFilterQuery()
    },
    onTemperatureIndexChange (index) {
      this.temperatureIndex = index
      this.temperature = index > 0 ? this.temperatureOptions[index - 1] : null
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
      this.ph = null
      this.temperature = null
      this.hostAssociation = ''
      this.piperCommunity = ''
      this.pushNicheFilterQuery()
    },
    // Pushes the current slider/dropdown values into the URL, which the
    // $route watcher below (fetchGlobalData) picks up to refetch the maps
    // and table -- same round trip onModeChange/onTaxonomyTypeChange use.
    pushNicheFilterQuery () {
      const query = { ...this.$route.query, mode: 'niche' }
      for (const key of ['ph', 'temperature', 'host_association', 'piper_community']) {
        delete query[key]
      }
      const niche = this.activeNicheFilters
      if (niche) {
        if (niche.ph !== undefined) query.ph = niche.ph
        if (niche.temperature !== undefined) query.temperature = niche.temperature
        if (niche.hostAssociation) query.host_association = niche.hostAssociation
        if (niche.piperCommunity) query.piper_community = niche.piperCommunity
      }
      this.page = 1
      this.$router.push({ name: 'SearchResults', params: { taxonomy: this.taxonomy }, query })
    },
    onPageChange (page) {
      this.page = page
      this.fetchData()
    },
    onSort (field, direction) {
      const scrollY = window.scrollY
      this.sortField = field
      this.sortDirection = direction
      fetchRunsByTaxonomy(this.taxonomy, this.taxonomy_type, this.page, this.sortField, this.sortDirection, this.pageSize, this.exclude_low_complexity, this.cluster, this.activeNicheFilters)
        .then(response => {
          this.search_result = response.data.results
          this.filtered_total = response.data.results.filtered_total ?? null
          this.$nextTick(() => window.scrollTo(0, scrollY))
        })
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
          toReturn += '<li><a href="/run/' + sample+ '">' + sample + '</a></li>'
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
      fetchRunsByTaxonomy(this.taxonomy, this.taxonomy_type, this.page, this.sortField, this.sortDirection, this.pageSize, this.exclude_low_complexity, this.cluster, this.activeNicheFilters)
        .then(response => {
          this.search_result = response.data.results
          this.filtered_total = response.data.results.filtered_total ?? null
        })

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
    csv_link () {
      return api_url() + '/taxonomy_search_csv/' + this.taxonomy + '?taxonomy_type=' + this.taxonomy_type + this.niche_query_suffix()
    },
    minimal_csv_link () {
      return api_url() + '/taxonomy_search_csv_minimal/' + this.taxonomy + '?taxonomy_type=' + this.taxonomy_type + this.niche_query_suffix()
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
    exclude_low_complexity () {
      const scrollY = window.scrollY
      this.page = 1
      fetchRunsByTaxonomy(this.taxonomy, this.taxonomy_type, this.page, this.sortField, this.sortDirection, this.pageSize, this.exclude_low_complexity, this.cluster, this.activeNicheFilters)
        .then(response => {
          this.search_result = response.data.results
          this.filtered_total = response.data.results.filtered_total ?? null
          this.$nextTick(() => window.scrollTo(0, scrollY))
        })
    }
  }
}
</script>

<style scoped>
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
  max-width: 640px;
  margin: 0 auto 1.5rem;
  padding: 1.25rem 1.5rem;
  background: #fafaf7;
  border: 1px solid #eee7d8;
  border-radius: 6px;
}
.niche-mapping-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
.niche-mapping-panel-header .subtitle {
  margin-bottom: 0;
}
.niche-slider-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  width: 100%;
}
.niche-slider-row :deep(.b-slider) {
  flex: 1 1 auto;
}
.niche-slider-value {
  flex: 0 0 auto;
  min-width: 5rem;
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: #555;
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
