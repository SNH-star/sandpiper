<template>
  <div>
    &nbsp;
    <div class="container">
      <section>
        <h3 class="title">Submitter information</h3>
        <RunMetadataTable :table_data="this.mdata.contact_metadata"  />
      </section>
    </div>

    &nbsp;
    <div class="container">
      <section>
        <h3 class="title">Sample information</h3>
        <div v-if="lat_lon() !== null">
          <!-- I cannot get center.sync to reset when reset_map() is clicked, oh well -->
          <l-map :style="map_style" :zoom.sync="zoom" :center.sync="center">
            <l-tile-layer :url="url" :attribution="attribution" :options="tile_layer_options" />
            <l-marker :lat-lng="lat_lon()" />
          </l-map>
          <button type="button" class="map-reset" @click="reset_map()"><b-icon icon="refresh" size="is-small" /> reset zoom</button>
          <br />
        </div>
        <RunMetadataTable :table_data="this.mdata.sample_info_metadata"  />
      </section>
    </div>

    &nbsp;
    <div class="container">
      <section>
        <h3 class="title">Sequencing information</h3>
        <RunMetadataTable :table_data="this.mdata.sequencing_metadata"  />
      </section>
    </div>

    &nbsp;
    <div class="container">
      <section>
        <h3 class="title">Derived information</h3>
        <RunMetadataTable :table_data="classification_metadata()" />
      </section>
    </div>

    &nbsp;
    <div class="container">
      <section>
        <h3 class="title">Other identifiers</h3>
        <RunMetadataTable :table_data="this.mdata.identity_metadata"  />
      </section>
    </div>

    &nbsp;
    <div class="container">
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

    &nbsp;
    <div class="container">
      <section>
        <h3 class="title">
          Metalog additional information
          <button type="button" class="metalog-info" :aria-expanded="show_metalog_help" aria-controls="metalog-help" aria-label="About Metalog metadata" @click="show_metalog_help = !show_metalog_help">
            <b-icon icon="information-outline" size="is-small" />
          </button>
        </h3>
        <div v-if="show_metalog_help" id="metalog-help" class="content metalog-help">
          <p>
            Derived from
            <a href="https://metalog.embl.de/" target="_blank" rel="noopener">Metalog</a>,
            a curated collection of additional metadata for public metagenomes<span v-if="this.mdata.metalog_retrieved_date">,
            retrieved on {{ this.mdata.metalog_retrieved_date }}</span>.
            Please cite Kuhn et al.,
            <i>Metalog: curated and harmonised contextual data for global metagenomics samples</i>,
            <i>Nucleic Acids Research</i> (2025),
            <a href="https://doi.org/10.1093/nar/gkaf1118" target="_blank" rel="noopener">https://doi.org/10.1093/nar/gkaf1118</a>.
          </p>
          <p>
            Metalog records are matched to this page by run accession: the
            accession shown above is looked up in Metalog, and the fields below
            are shown only when it matches exactly one Metalog entry. Runs with
            no match, or with more than one, show nothing here.
          </p>
        </div>
        <div v-if="metalog_metadata().length === 0">
          <p>No Metalog metadata recorded for this run</p>
        </div>
        <RunMetadataTable v-else :table_data="metalog_metadata()" />
      </section>
    </div>

    &nbsp;
    <div class="container">
      <section>
        <h3 class="title">
          IndicPiper habitat indicators
          <button type="button" class="metalog-info" :aria-expanded="show_indicpiper_help" aria-controls="indicpiper-help" aria-label="About IndicPiper habitat indicators" @click="show_indicpiper_help = !show_indicpiper_help">
            <b-icon icon="information-outline" size="is-small" />
          </button>
        </h3>
        <div v-if="show_indicpiper_help" id="indicpiper-help" class="content metalog-help">
          <p>
            <a href="https://github.com/cliffbueno/IndicPiper" target="_blank" rel="noopener">IndicPiper</a>
            identifies genera that are strong, specific indicators of particular
            habitats, using <code>indicspecies::multipatt</code> IndVal analysis
            across Sandpiper's own current data (not a frozen external
            snapshot). Each score below is this run's summed relative
            abundance of the genera flagged as indicators of that habitat --
            a higher score means this sample's genus composition more closely
            matches that habitat's characteristic signature.
          </p>
          <p>
            Only habitats with a nonzero score are shown; most runs match a
            handful of habitats, not all of them. A run with no rows here
            either predates this analysis or has no genera in common with any
            indicator set.
          </p>
          <p>
            Values shown as <code>&lt;0.001</code> are real, nonzero matches
            (this run does contain some of that habitat's indicator genera).
          </p>
        </div>
        <div v-if="indicpiper_scores().length === 0">
          <p>No IndicPiper habitat indicators recorded for this run</p>
        </div>
        <RunMetadataTable v-else :table_data="indicpiper_scores()" />
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

export default {
  name: 'RunMetadata',
  props: ['mdata','mdata_parsed'],
  components: {
    LMap,
    LTileLayer,
    LMarker,
    RunMetadataTable
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
      show_metalog_help: false,
      show_indicpiper_help: false
    }
  },
  mounted () {
    this.center = this.get_default_map_center()
  },
  computed: {
    map_style: function () {
      return { height: '300px', width: '100%', maxWidth: '550px' }
    },
  },
  methods: {
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
@media (max-width: 768px) {
  .metalog-info {
    min-width: 44px;
    min-height: 44px;
  }
  .map-reset {
    min-height: 44px;
  }
  .title {
    font-size: 1.35rem;
    line-height: 1.25;
    overflow-wrap: anywhere;
  }
}
</style>
