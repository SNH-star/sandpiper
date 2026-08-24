<template>
  <div class="run-page">
    <div v-if="metadata !== null">
      <section class="section">
        <div class="container" v-if="metadata !== null">
          <h1 class="title run-study-title">{{ metadata.metadata_parsed.study_title }}</h1>

          <p class="subtitle">
            Sample {{ sample_name_mature }}
          </p>

          <div class="run-summary">
            {{ metadata.metadata_parsed.organism }} | 
            {{ metadata.metadata_parsed.host_or_not_mature }} |
            {{ metadata.metadata_parsed.mbases / 1000}} Gbp | 
            <span v-if="getNumReads==0">
                &lt;1 million reads
            </span>
            <span v-else>
              {{ getNumReads }} million reads
            </span>
            {{ read_length_mature }}|
            {{ metadata.metadata_parsed.instrument }} | 
            <span v-if="metadata.metadata_parsed.collection_time !== null">
              Collected {{ metadata.metadata_parsed.collection_time }}, released {{ metadata.metadata_parsed.release_month }}
            </span>
            <span v-else>
              Released {{ metadata.metadata_parsed.release_month }}
            </span>
             | 
            <span v-if="metadata.metadata_parsed.num_related_runs == 0">No related runs here.</span>
            <span v-else>
              <router-link :to="{ name: 'Project', query: { model_bioproject: metadata.metadata_parsed.bioproject }}">
                <span v-if="metadata.metadata_parsed.num_related_runs == 1">1 related run</span>
                <span v-else>
                  {{ metadata.metadata_parsed.num_related_runs }} related runs
                </span>
               </router-link>
              </span>
      <!-- {{ related_runs_short }}  -->
            <br />
            SingleM prokaryotic fraction (SPF) <span style="smf_low">{{ metadata.metadata_parsed.smf }}%</span> | Known species fraction {{ known_species_fraction }}% | Low complexity: {{ metadata.metadata_parsed.low_complexity ? 'Yes' : 'No' }} | Non-metagenome organism: {{ metadata.metadata_parsed.non_metagenome_organism_strict ? 'Yes' : 'No' }} | Synthetic: {{ metadata.metadata_parsed.synthetic ? 'Yes' : 'No' }} | RNA/non-DNA: {{ metadata.metadata_parsed.rna_or_non_dna_strict ? 'Yes' : 'No' }}
            <br />
          </div>

          <div class="has-text-justified run-abstract">
            <br />
            <p>{{ metadata.metadata_parsed.study_abstract }}</p>
          </div>

          <div class="run-external-links">
            <br />
            NCBI: <a :href="bioproject_url">{{ metadata.metadata_parsed.bioproject }}</a> | <a :href="'http://www.ncbi.nlm.nih.gov/sra?term=' + accession">{{ accession }}</a>
            <br />
            <div v-if="publications.length===0">
              <p>No linked publications recorded. A <a :href="scholar_search_url">search on Google Scholar</a> may find some.</p>
            </div>
            <div v-else>
              <ul v-for="link in publications" v-bind:key="link.study_id">
                <li v-if="link['database'].toLowerCase()==='pubmed'">PubMed <a :href="'https://www.ncbi.nlm.nih.gov/pubmed?term='+link['study_id']">{{ link['study_id'] }}</a></li>
                <li v-else-if="link['database'].toLowerCase()==='doi'">DOI <a :href="'https://doi.org/'+link['study_id']">{{ link['study_id'] }}</a></li>
                <li v-else>{{ link['database'] }} {{ link['study_id'] }}</li>
              </ul>
              A <a :href="scholar_search_url">search on Google Scholar</a> may find further publications.
            </div>
          </div>

          <div v-if="non_publication_study_links.length>0">
            <br />
            This run has links to other databases:
            <ul v-for="link in non_publication_study_links" v-bind:key="link.label">
              <li><b-icon icon="link-variant" size="is-small" /><a :href="link.url">{{link.label}}</a></li>
            </ul>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <h3 class="title">Taxonomic profile</h3>
          <b-field class="taxonomy-selector">
            <b-radio-button v-model="taxonomy_db" native-value="gtdb" @input="fetchCondensed" type="is-info">
              GTDB ({{ GTDB_VERSION }})
            </b-radio-button>
            <b-radio-button v-model="taxonomy_db" native-value="globdb" @input="fetchCondensed" type="is-warning" :disabled="db_availability.globdb === false">
              GlobDB ({{ GLOBDB_VERSION }})<span v-if="db_availability.globdb === false"> - unavailable</span>
            </b-radio-button>
          </b-field>
          <div class="sunburst run-sunburst">
            <template v-if="condensed_tree != null">
              <Sunburst3 :json_tree="sunburst_tree" :overall_coverage="10.3" :known_species_fraction="known_species_fraction" />
            </template>
          </div>
        </div>
      </section>

      <section class="section">
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
          <RunMetadata :mdata="metadata.metadata" :mdata_parsed="metadata.metadata_parsed" />
        </div>
      </section>

      <section class="section">
        <div class="container is-large">
          <h3 class="title">Download</h3>

          <p>
            The taxonomic profile of this sample can be downloaded in tab-separated "SingleM condensed with extras" format, generated with <a :href="profile_csv_with_extras_link_gtdb">GTDB ({{ GTDB_VERSION }})</a> or <a :href="profile_csv_with_extras_link_globdb">GlobDB ({{ GLOBDB_VERSION }})</a> taxonomy. This details the coverage assigned to each taxon at each taxonomic level, both <a href="https://wwood.github.io/singlem/Glossary">filled and unfilled</a>, plus the relative abundance of each taxon.</p>
          <br />

          <p>Concise "SingleM condensed" format files with three columns sample name, coverage, and taxonomy are also available for download (<a :href="profile_csv_link_gtdb">GTDB ({{ GTDB_VERSION }})</a> or <a :href="profile_csv_link_globdb">GlobDB ({{ GLOBDB_VERSION }})</a>). In this format the coverage of each lineage is the coverage assigned to that taxon and not more specifically e.g. the coverage of a species is not included in the coverage shown for its genus. These taxonomic profiles can be converted to other forms (e.g. one that gives the relative abundance instead of the coverage) using the <a href="https://wwood.github.io/singlem/tools/summarise">SingleM summarise</a> tool.</p>
          <br />

          <p>Unfortunately, for now, the <a :href="full_profile_link">full SingleM OTU table of {{ accession }}</a> (GTDB ({{ GTDB_VERSION }}) annotated) tab-separated file containing information about each OTU from each marker cannot be downloaded directly from this website.</p>
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
import Sunburst3 from '@/components/Sunburst3.vue'
import RunMetadata from '@/components/RunMetadata.vue'

import { api_url, fetchRunMetadata, fetchRunCondensed } from '@/api'
import { GTDB_VERSION, GLOBDB_VERSION } from '@/versions'
import { stopPageLoading, currentLoadingToken } from '@/store/pageLoading'

export default {
  name: 'Run',
  title () {
    return `Run ${this.accession} - Sandpiper`
  },
  data: function () {
    return {
      GTDB_VERSION,
      GLOBDB_VERSION,
      condensed_tree: null,
      condensed_cache: {},
      db_availability: { gtdb: null, globdb: null },
      metadata: null,
      error_message: null,
      taxonomy_db: 'gtdb'
    }
  },
  props: ['accession'],
  components: {
    Sunburst3,
    RunMetadata
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
    read_length_mature: function () {
      if (this.metadata.metadata_parsed.read_length_summary === null) {
        return ''
      } else {
        return '| ' + this.metadata.metadata_parsed.read_length_summary + ' '
      }      
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
    }
  },
  created () {
    // fetch the data when the view is created and the data is
    // already being observed
    this.fetchData()
  },
  methods: {
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
    study_toplink (link) {
      if (link['database'].toLowerCase()==='pubmed') {
        return '<a href="https://www.ncbi.nlm.nih.gov/pubmed?term='+link['study_id']+'">'+link['study_id']+'</a>'
      } else {
        return link['database'] + ': ' + link['study_id']
      }
    }
  },
  watch: {
    // call again the method if the route changes
    $route: 'fetchData',
    taxonomy_db: 'fetchCondensed'
  }
}
</script>

<style scoped>
.run-page,
.run-page a,
.run-study-title,
.run-summary,
.run-external-links {
  overflow-wrap: anywhere;
}
.run-summary {
  line-height: 1.7;
}
.run-sunburst {
  max-width: 100%;
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
  .run-abstract {
    text-align: left !important;
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
