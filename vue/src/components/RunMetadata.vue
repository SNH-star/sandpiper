<template>
  <div>
    <div id="submitter-information" class="container metadata-section">
      <section>
        <h3 class="title">Submitter information</h3>
        <RunMetadataTable :table_data="this.mdata.contact_metadata" />
      </section>
    </div>

    <div id="sample-information" class="container metadata-section">
      <section>
        <h3 class="title section-heading">
          <span>
            Sample information
            <button type="button" class="metalog-info" :aria-expanded="show_sample_help" aria-controls="sample-help" aria-label="About sample information" @click="show_sample_help = !show_sample_help">
              <b-icon icon="information-outline" size="is-small" />
            </button>
          </span>
        </h3>
        <div v-if="show_sample_help" id="sample-help" class="content metalog-help">
          <p>
            Details about the sample this run was sequenced from, such as where and when it was collected, the host or
            environment, and anything else the submitter recorded. Rows coloured green come from Metalog.
          </p>
          <p>
            <b><a href="https://metalog.embl.de/downloads" target="_blank" rel="noopener" class="source-link src-metalog">Metalog</a></b>: curated extra details from Metalog, added only when this sample is found there.
          </p>
        </div>
        <div v-if="lat_lon() !== null">
          <!-- I cannot get center.sync to reset when reset_map() is clicked, oh well -->
          <l-map :style="map_style" :zoom.sync="zoom" :center.sync="center">
            <l-tile-layer :url="url" :attribution="attribution" :options="tile_layer_options" />
            <l-marker :lat-lng="lat_lon()" />
          </l-map>
          <button type="button" class="map-reset" @click="reset_map()"><b-icon icon="refresh" size="is-small" /> reset zoom</button>
          <br />
        </div>
        <RunMetadataTable :table_data="filtered_sample_rows" :empty_text="sample_filters_active ? 'No fields match these filters.' : null">
          <template #after-key>
            <fieldset class="sample-filters">
              <legend class="sample-filters-title">Filter fields</legend>
              <label v-for="f in SAMPLE_FILTERS" :key="f.key" v-show="!f.difference || difference_counts[f.key] > 0" class="sample-filter">
                <input type="checkbox" name="sample-filters" :id="'sample-filter-' + f.key" v-model="sample_filters" :value="f.key" />
                <span v-if="f.difference" :class="['diff-swatch', 'diff-' + f.key]" aria-hidden="true"></span>
                <span>{{ f.label }}<template v-if="f.difference"> ({{ difference_counts[f.key] }})</template></span>
              </label>
              <button v-if="sample_filters_active" type="button" class="sample-filters-clear" @click="sample_filters = []">Clear filters</button>
            </fieldset>
            <p v-if="difference_counts.only_here > 0" class="section-note">
              Yellow rows are fields no other sample in this BioProject has. That can reflect a data retrieval gap rather than a real difference.
            </p>
          </template>
        </RunMetadataTable>
        <div v-if="metalog_metadata().length > 0" id="metalog" class="section-note">
          Metalog rows
          <button type="button" class="metalog-info" :aria-expanded="show_metalog_help" aria-controls="metalog-help-merged" aria-label="About Metalog metadata" @click="show_metalog_help = !show_metalog_help">
            <b-icon icon="information-outline" size="is-small" />
          </button>
          <b-button tag="a" type="is-info" size="is-small" :href="metalog_csv_link()">Download Run Specific CSV</b-button>
          <div v-if="show_metalog_help" id="metalog-help-merged" class="content metalog-help">
            <p>
              Derived from
              <a href="https://metalog.embl.de/" target="_blank" rel="noopener">Metalog</a>,
              a curated collection of additional metadata for public metagenomes,
              last updated on {{ metalog_last_update }}.
              Please cite Kuhn et al.,
              <i>Metalog: curated and harmonised contextual data for global metagenomics samples</i>,
              <i>Nucleic Acids Research</i> (2025),
              <a href="https://doi.org/10.1093/nar/gkaf1118" target="_blank" rel="noopener">https://doi.org/10.1093/nar/gkaf1118</a>.
              Records are matched by BioSample, so every run sharing this BioSample shows the same record.
              Bulk download for all Metalog metadata is on the <router-link to="/about#bulk-download">About page</router-link>.
            </p>
          </div>
        </div>
      </section>
    </div>

    <div id="sequencing-information" class="container metadata-section">
      <section>
        <h3 class="title">Sequencing information</h3>
        <RunMetadataTable :table_data="this.mdata.sequencing_metadata" />
      </section>
    </div>

    <div id="derived-information" class="container metadata-section">
      <section>
        <h3 class="title">Derived information</h3>
        <RunMetadataTable :table_data="classification_metadata()" />
      </section>
    </div>

    <div id="other-identifiers" class="container metadata-section">
      <section>
        <h3 class="title">Other identifiers</h3>
        <RunMetadataTable :table_data="this.mdata.identity_metadata" />
      </section>
    </div>

    <div id="study-links" class="container metadata-section">
      <section>
        <h3 class="title">Study links</h3>
        <div v-if="Object.keys(gatherMetadata ('study_links')).length===0">
          <p>No linked studies recorded</p>
        </div>
        <div v-else>
          <b-table :data="gatherMetadata ('study_links')" :columns="studyLinksColumns()" :striped="true" />
        </div>
      </section>
    </div>

    <!-- Runs with Metalog data show it inside Sample information instead. -->
    <template v-if="metalog_metadata().length === 0">
    <div id="metalog" class="container metadata-section">
      <section class="metadata-block">
        <h3 class="title section-heading">
          <span>
            Metalog additional information
            <button type="button" class="metalog-info" :aria-expanded="show_metalog_help" aria-controls="metalog-help" aria-label="About Metalog metadata" @click="show_metalog_help = !show_metalog_help">
              <b-icon icon="information-outline" size="is-small" />
            </button>
          </span>
          <b-button v-if="metalog_metadata().length > 0" tag="a" type="is-info" size="is-small" :href="metalog_csv_link()">Download Run Specific CSV</b-button>
        </h3>
        <p class="section-note">
          Bulk download for all Metalog metadata found in this database is available on the <router-link to="/about#bulk-download">About page</router-link>.
        </p>
        <div v-if="show_metalog_help" id="metalog-help" class="content metalog-help">
          <p>
            Derived from
            <a href="https://metalog.embl.de/" target="_blank" rel="noopener">Metalog</a>,
            a curated collection of additional metadata for public metagenomes,
            last updated on {{ metalog_last_update }}.
            Please cite Kuhn et al.,
            <i>Metalog: curated and harmonised contextual data for global metagenomics samples</i>,
            <i>Nucleic Acids Research</i> (2025),
            <a href="https://doi.org/10.1093/nar/gkaf1118" target="_blank" rel="noopener">https://doi.org/10.1093/nar/gkaf1118</a>.
          </p>
          <p>
            Metalog describes samples, not runs, so records are matched by
            BioSample: this run's BioSample accession is looked up in Metalog,
            and every run sharing that BioSample shows the same record. Runs
            whose BioSample is absent from Metalog show nothing here.
          </p>
        </div>
        <div v-if="metalog_metadata().length === 0">
          <p>No Metalog metadata recorded for this run</p>
        </div>
        <RunMetadataTable v-else :table_data="metalog_metadata()" />
      </section>
    </div>
    </template>

    <div id="indicpiper" class="container metadata-section">
      <section class="metadata-block">
        <h3 class="title section-heading">
          <span>
            IndicPiper habitat indicators
            <span v-if="indicpiper_version" class="indicpiper-version">(indicator database v{{ indicpiper_version }})</span>
            <button type="button" class="metalog-info" :aria-expanded="show_indicpiper_help" aria-controls="indicpiper-help" aria-label="About IndicPiper habitat indicators" @click="show_indicpiper_help = !show_indicpiper_help">
              <b-icon icon="information-outline" size="is-small" />
            </button>
          </span>
          <b-button v-if="indicpiper_scores().length > 0" tag="a" type="is-info" size="is-small" :href="indicpiper_csv_link()">Download Run Specific CSV</b-button>
        </h3>
        <p class="section-note">
          Bulk download for all IndicPiper habitat results found in this database is available on the <router-link to="/about#bulk-download">About page</router-link>.
        </p>
        <div v-if="show_indicpiper_help" id="indicpiper-help" class="content metalog-help">
          <p>
            <a href="https://github.com/cliffbueno/IndicPiper" target="_blank" rel="noopener">IndicPiper</a>
            identifies genera that are strong and specific indicators of particular habitats using <b>Indicspecies::Multipatt</b> IndVal analysis.
            Sandpiper uses IndicPiper's curated, published indicator database as provided, rather than regenerating it from Sandpiper's data, and compares the genus composition of each run against this database. 
            Each habitat percentage represents the summed relative abundance of its indicator genera in this sample. IndicPiper’s reference database covers 13 habitats. Samples may exhibit microbial signals associated with multiple habitats; these associations do not establish the sample’s environment of origin. Percentages describe abundance, not confidence in a habitat assignment.
          </p>
          <p>
            Runs with an IndicPiper score of zero either contain no genus-level classifications or contain classified genera that are not included in IndicPiper's curated indicator database.  
          </p>
          <p>
            Values shown as <b>&lt;0.01%</b> represent nonzero abundances below the displayed precision.
          </p>
        </div>
        <div v-if="indicpiper_uncovered_organism" class="notification is-warning" role="status">
          <strong>Environment not covered by IndicPiper</strong>
          <p>
            This run is labelled “{{ indicpiper_uncovered_organism }}”, which was not part of the list of
            environments used in the IndVal analysis. IndicPiper’s reference database is limited to
            13 habitats, so the habitat percentages below should be interpreted with caution.
          </p>
        </div>
        <div v-if="indicpiper_mismatch" class="notification is-warning" role="status">
          <strong>IndicPiper habitat discrepancy</strong>
          <p>
            The recorded organism is “{{ indicpiper_mismatch.organism }}”, associated with
            {{ indicpiper_mismatch.expectedHabitat }}, whereas the strongest IndicPiper signal is
            {{ indicpiper_mismatch.top.k }} ({{ formatIndicPiperPercent(indicpiper_mismatch.top.score) }}
            indicator abundance).
            IndicPiper’s reference database is limited to 13 habitats (Per the <a href="https://github.com/cliffbueno/IndicPiper">Setup</a>). Microbial signals associated
            with a habitat may occur in samples from other environments and do not establish the
            sample’s environment of origin. This discrepancy should be interpreted alongside the
            recorded sample metadata; it does not by itself demonstrate a potential metadata error.
          </p>
        </div>
        <div v-if="indicpiper_scores().length === 0">
          <p>No IndicPiper habitat indicators recorded for this run</p>
        </div>
        <IndicPiperHabitatChart v-else :habitats="indicpiper_scores()" />
      </section>
    </div>

  </div>
</template>

<script>

// If you need to reference 'L', such as in 'L.icon', then be sure to
// explicitly import 'leaflet' into your component
// import L from 'leaflet'
import { LMap, LTileLayer, LMarker } from '@vue-leaflet/vue-leaflet'


import { Icon, latLng } from 'leaflet'
import RunMetadataTable from '@/components/RunMetadataTable.vue'
import IndicPiperHabitatChart from '@/components/IndicPiperHabitatChart.vue'
import { indicpiperMismatch, indicpiperUncoveredOrganism, formatIndicPiperPercent } from '@/utils/indicpiper'
// Same Metalog release the About page quotes: the API value when the database
// carries one, else the recorded fallback -- so the two pages cannot disagree.
import { METALOG_LAST_UPDATE, metalogLongDate } from '@/constants/metalog'
import { api_url } from '@/api'

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

const default_zoom = 0.5

// Tick boxes above the Sample information table. The origin boxes are
// alternatives (a row is shown when it matches any ticked one), and so are the
// difference boxes; a row must satisfy one ticked box from each group. Metalog
// rows carry no is_custom flag, so the NCBI-defined test excludes them
// explicitly.
const SAMPLE_FILTERS = [
  { key: 'metalog', label: 'Metalog', test: r => r.source === 'metalog' },
  { key: 'defined', label: 'NCBI-defined attributes', test: r => r.source !== 'metalog' && !r.is_custom },
  { key: 'custom', label: 'Custom attributes', test: r => !!r.is_custom },
  { key: 'only_here', label: 'Only in this sample (field absent from other samples)', test: r => r.difference === 'only_here', difference: true },
  { key: 'differs', label: 'Differs from other samples', test: r => r.difference === 'differs', difference: true },
  { key: 'expected', label: 'Differs as expected (IDs, sizes, dates)', test: r => r.difference === 'expected', difference: true }
]

export default {
  name: 'RunMetadata',
  props: ['mdata','mdata_parsed','accession'],
  components: {
    LMap,
    LTileLayer,
    LMarker,
    RunMetadataTable,
    IndicPiperHabitatChart
  },
  data () {
    return {
      medata: this.mdata,
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
      zoom: default_zoom,
      center: latLng(0, 0),
      bounds: null,
      show_sample_help: false,
      show_metalog_help: false,
      SAMPLE_FILTERS,
      sample_filters: [],
      show_indicpiper_help: false
    }
  },
  mounted () {
    this.center = this.get_default_map_center()
  },
  computed: {
    // Sample information rows; only Metalog rows are tagged (and coloured).
    sample_rows () {
      const own = this.mdata.sample_info_metadata || []
      return own.concat(this.metalog_metadata().map(r => ({ ...r, source: 'metalog' })))
    },
    sample_filters_active () {
      return this.sample_filters.length > 0
    },
    filtered_sample_rows () {
      if (!this.sample_filters_active) return this.sample_rows
      const ticked = SAMPLE_FILTERS.filter(f => this.sample_filters.includes(f.key))
      const origins = ticked.filter(f => !f.difference)
      const differences = ticked.filter(f => f.difference)
      return this.sample_rows.filter(r =>
        (origins.length === 0 || origins.some(f => f.test(r))) &&
        (differences.length === 0 || differences.some(f => f.test(r))))
    },
    // How many Sample information rows fall in each difference group.
    difference_counts () {
      const counts = {}
      SAMPLE_FILTERS.filter(f => f.difference).forEach(f => {
        counts[f.key] = this.sample_rows.filter(f.test).length
      })
      return counts
    },
    indicpiper_uncovered_organism() {
      return indicpiperUncoveredOrganism(this.mdata_parsed?.organism)
    },
    indicpiper_version() {
      return this.mdata.indicpiper_version || null
    },
    indicpiper_mismatch() {
      return indicpiperMismatch(this.mdata_parsed?.organism, this.indicpiper_scores())
    },
    map_style: function () {
      return { height: '300px', width: '100%', maxWidth: '550px' }
    },

    // Metalog's own release date, as recorded when the data was fetched.
    // Databases built before that was captured carry no release block, so
    // fall back to the last value recorded in the front end.
    metalog_last_update: function () {
      const released = this.mdata.metalog_release?.last_metadata_update
      return metalogLongDate(released || METALOG_LAST_UPDATE)
    },
  },
  methods: {
    formatIndicPiperPercent,
    // Populated meta_ fields for this run, already filtered and sorted by the
    // API. Absent for runs indexed before the metalog merge, hence the guard.
    metalog_metadata: function () {
      return this.mdata.metalog_metadata || []
    },
    // This run's IndicPiper habitat-indicator scores, already sorted and
    // filtered to nonzero matches by the API. Absent for runs indexed before
    // this analysis was added, hence the guard.
    indicpiper_scores: function () {
      return this.mdata.indicpiper_scores || []
    },
    metalog_csv_link: function () {
      return api_url() + '/metalog_csv/' + this.accession
    },
    indicpiper_csv_link: function () {
      return api_url() + '/indicpiper_csv/' + this.accession
    },
    get_default_map_center: function () {
      const lat_lon = this.lat_lon()
      if (lat_lon !== null) {
        // Near the poles, the map is too small and so the marker can be hidden
        if (lat_lon[0] > 45) {
          return latLng(45.0, lat_lon[1])
        } else if (lat_lon[0] < -45) {
          return latLng(-45.0, lat_lon[1])
        } else {
          return latLng(0, lat_lon[1])
        }
      } else {
        return latLng(0, 0)
      }
    },
    reset_map: function () {
      // Setting the center here doesn't appear to have any effect
      this.center = this.get_default_map_center()
      // Zoom works though
      this.zoom = default_zoom
    },
    // Data to be put in the general metadata. This method is actually mostly
    // dead code now, but kept as it is used in one place
    gatherMetadata (section) {
      const toReturn = []
      Object.keys(this.mdata).forEach(key => {
        const v = this.mdata[key]
        if (section==='general') {
          if (!['biosample_attributes','study_links','parsed_sample_attributes','study_abstract','study_title'].includes(key) && v !== null) {
            toReturn.push({
              k: key,
              value: v
            })
          }
        } else if (section==='study_links' && key === 'study_links') {
          v.forEach(link => {
            if (typeof link['database'] !== 'undefined') {
              if (link['database'].toLowerCase() === 'pubmed'){
                toReturn.push({
                  k: link['database'],
                  value: '<a href="https://www.ncbi.nlm.nih.gov/pubmed?term='+link['study_id']+'">'+link['study_id']+'</a>'
                })
              } else {
                toReturn.push({
                  k: link['database'],
                  value: link['study_id']
                })
              }
            } else {
              toReturn.push({
                k: link.label,
                value: '<a href="'+link.url+'">'+link.url+'</a>'
              })
            }
          })
        } else {
          if (key === section) {
            Object.keys(v).forEach(k => {
              if (v[k] !== null) {
                toReturn.push({
                  k: k,
                  value: v[k]
                })
              }
            })
          }
        }
      })
      return toReturn
    },
    studyLinksColumns () {
      return [{ label: 'database', field: 'k' }, { label: 'id', field: 'value' }]
    },
    // Backend classification flags surfaced from parsed_sample_attributes.
    // Booleans render Yes/No; the domain_only_* flags may be null (no profile
    // loaded for that taxonomy) and render as Unknown.
    classification_metadata () {
      const p = this.mdata_parsed
      const yesNo = (v) => (v === null || typeof v === 'undefined' ? 'Unknown' : (v ? 'Yes' : 'No'))
      const rows = [
        { k: 'Non-metagenome organism (strict)', flag: p.non_metagenome_organism_strict,
          description: "True when the organism name recorded for the sample names a single, specific species rather than a metagenome or a community. Names containing the word 'metagenome' are excluded, as are community terms such as 'uncultured', 'environmental sample', 'enrichment culture', 'mixed culture', 'microbial community', 'consortium' and 'microbiome', and generic placeholder names such as 'bacterium', 'unidentified', 'archaeon', 'prokaryote', 'eukaryote', 'organism' and 'microorganism' that do not identify an actual species. What is left is samples named after a real organism, such as 'Escherichia coli' or 'Homo sapiens'." },
        { k: 'Non-metagenome organism (loose)', flag: p.non_metagenome_organism_loose,
          description: "True when the organism name recorded for the sample does not contain the word 'metagenome' and does not match a community term such as 'uncultured', 'environmental sample', 'enrichment culture', 'mixed culture', 'microbial community', 'consortium' or 'microbiome'. Generic placeholder names that do not identify an actual species, such as 'bacterium', 'unidentified', 'archaeon', 'prokaryote' or 'organism', are still counted true here." },
        { k: 'Synthetic', flag: p.synthetic,
          description: "True when the organism name recorded for the sample contains the word 'synthetic', or contains 'simulat', which catches 'simulate', 'simulated' and 'simulation', or when the sample's declared BioSample library source is recorded as 'SYNTHETIC'." },
        { k: 'RNA / non-DNA (strict)', flag: p.rna_or_non_dna_strict,
          description: "True when the sequencing library strategy recorded for the run is RNA-Seq, miRNA-Seq, FL-cDNA, ssRNA-seq, ncRNA-Seq, RIP-Seq, Ribo-seq or EST, or when the declared BioSample library source is METATRANSCRIPTOMIC, TRANSCRIPTOMIC or TRANSCRIPTOMIC SINGLE CELL." },
        { k: 'RNA / non-DNA (loose)', flag: p.rna_or_non_dna_loose,
          description: "True when the sequencing library strategy recorded for the run is RNA-Seq, miRNA-Seq, FL-cDNA, ssRNA-seq, ncRNA-Seq, RIP-Seq, Ribo-seq or EST, or when the declared BioSample library source is METATRANSCRIPTOMIC, TRANSCRIPTOMIC, TRANSCRIPTOMIC SINGLE CELL, OTHER or SYNTHETIC." },
        { k: 'Domain-only (GTDB)', flag: p.domain_only_gtdb,
          description: "True when every classification in the sample's condensed taxonomic profile under the GTDB scheme stops at the domain level, such as 'Bacteria' or 'Archaea', with none reaching phylum or deeper." },
        { k: 'Domain-only (GlobDB)', flag: p.domain_only_globdb,
          description: "True when every classification in the sample's condensed taxonomic profile under the GlobDB scheme stops at the domain level, such as 'Bacteria' or 'Archaea', with none reaching phylum or deeper." },
        { k: 'Domain-only (both)', flag: p.domain_only_both,
          description: "True when the sample's condensed taxonomic profile stops at the domain level under both the GTDB scheme and the GlobDB scheme, with no classification in either profile reaching phylum or deeper. It is left blank when one of the two profiles was never generated for the sample." }
      ]
      return rows.map(r => ({ k: r.k, v: yesNo(r.flag), is_custom: false, description: r.description }))
    },
    // Backend classification flags surfaced from parsed_sample_attributes.
    // Booleans render Yes/No; the domain_only_* flags may be null (no profile
    // loaded for that taxonomy) and render as Unknown.
    classification_metadata () {
      const p = this.mdata_parsed
      const yesNo = (v) => (v === null || typeof v === 'undefined' ? 'Unknown' : (v ? 'Yes' : 'No'))
      const rows = [
        { k: 'Non-metagenome organism (strict)', flag: p.non_metagenome_organism_strict,
          description: "TRUE when the organism is a specific single organism (not a metagenome or community term), excluding ambiguous generic names." },
        { k: 'Non-metagenome organism (loose)', flag: p.non_metagenome_organism_loose,
          description: "As strict, but including ambiguous generic names such as 'bacterium' or 'unidentified'." },
        { k: 'Synthetic', flag: p.synthetic,
          description: "TRUE for synthetic or simulated metagenomes, or a SYNTHETIC library source." },
        { k: 'RNA / non-DNA (strict)', flag: p.rna_or_non_dna_strict,
          description: "TRUE for RNA-based library strategies or transcriptomic library sources." },
        { k: 'RNA / non-DNA (loose)', flag: p.rna_or_non_dna_loose,
          description: "As strict, plus OTHER or SYNTHETIC library sources." },
        { k: 'Domain-only (GTDB)', flag: p.domain_only_gtdb,
          description: "TRUE when the GTDB profile does not resolve below domain level." },
        { k: 'Domain-only (GlobDB)', flag: p.domain_only_globdb,
          description: "TRUE when the GlobDB profile does not resolve below domain level." },
        { k: 'Domain-only (both)', flag: p.domain_only_both,
          description: "TRUE when neither GTDB nor GlobDB resolves below domain level." }
      ]
      return rows.map(r => ({ k: r.k, v: yesNo(r.flag), is_custom: false, description: r.description }))
    },
    lat_lon () {
      const parsed_data = this.mdata_parsed
      const lat = parsed_data.latitude
      const lon = parsed_data.longitude
      if (lat !== null && lon !== null) {
        return [lat, lon]
      } else {
        return null
      }
    }
  }
}
</script>

<style scoped>
/* Source links: link and visited are a step deeper than the row colour, same hue; hover and active
   go darker. */
.source-link { background-color: transparent; text-decoration: none; }
.source-link:hover, .source-link:active { text-decoration: underline; }
.source-link.src-metalog:link { color: #2e7d32; }
.source-link.src-metalog:visited { color: #2e7d32; }
.source-link.src-metalog:hover { color: #1b5e20; }
.source-link.src-metalog:active { color: #124116; }

/* Same vocabulary as the Run page's Identifiers block: quiet label,
   quiet outlined 6px chips, teal as the only accent. */
.diff-swatch {
  display: inline-block;
  width: 3px;
  height: 1.1em;
}
.diff-only_here { background: var(--color-diff-only-here); }
.diff-differs { background: var(--color-diff-differs); }
.diff-expected { background: var(--color-diff-expected); }

.sample-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2) var(--space-4);
  margin: 0 0 var(--space-3);
  padding: 0;
  border: 0;
}
.sample-filters-title {
  float: left;
  width: auto;
  padding: 0;
  margin-right: var(--space-2);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-ink-muted);
}
.sample-filter {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: hsl(0, 0%, 25%);
  cursor: pointer;
}
.sample-filter input {
  accent-color: var(--color-accent);
}
.sample-filters-clear {
  appearance: none;
  border: 0;
  padding: 0;
  background: transparent;
  font: inherit;
  font-size: 0.85rem;
  color: var(--color-accent);
  text-decoration: underline;
  cursor: pointer;
}

.metalog-info {
  appearance: none;
  border: 0;
  padding: 0.15rem;
  background: transparent;
  cursor: pointer;
  vertical-align: middle;
  color: #7a7a7a;
}
.metalog-info:hover {
  color: #363636;
}
.metalog-info:focus-visible,
.map-reset:focus-visible {
  outline: 2px solid #3273dc;
  outline-offset: 2px;
}
.map-reset {
  appearance: none;
  border: 0;
  padding: 0.4rem 0;
  background: transparent;
  color: #3273dc;
  cursor: pointer;
  font: inherit;
}
.metalog-help {
  margin-bottom: 1rem;
  overflow-wrap: anywhere;
}
.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
}
/* .section-heading is an <h3 class="title">, so its serif display font
   (app.scss's global .title rule) otherwise inherits straight down into
   the button -- fine for the heading text, wrong for a UI action label. */
.section-heading :deep(.button) {
  font-family: system-ui, -apple-system, "Segoe UI", "Ubuntu", "Cantarell", sans-serif;
}
.section-note {
  margin: 0.15rem 0 0.75rem;
  font-size: 0.85rem;
  color: hsl(0, 0%, 40%);
}
/* Replaces the blank lines that used to separate the sections. */
.metadata-section {
  margin-top: var(--space-8);
}
@media (max-width: 768px) {
  /* Metalog and IndicPiper follow each other with only blank space between,
     which ran their headings, buttons and tables together on a phone. */
  .metadata-block {
    margin-top: 1.5rem;
    padding: 1.5rem 0 0.5rem;
    border-top: 2px solid hsl(0, 0%, 88%);
  }
  .metalog-info {
    min-width: 44px;
    min-height: 44px;
  }
  .map-reset {
    min-height: 44px;
  }
  .section-heading :deep(.button) {
    min-height: 44px;
  }
  .title {
    font-size: 1.35rem;
    line-height: 1.25;
    overflow-wrap: anywhere;
  }
}
</style>
