<template>
  <div class="run-page">
    <!-- Amplicon runs (/amplicon/run/:accession): same page, amplicon data. -->
    <div v-if="is_amplicon && metadata !== null" class="amplicon-run">
      <section class="section">
        <div class="container">
          <p class="amplicon-eyebrow">{{ parsed.amplicon_marker }} amplicon · {{ parsed.amplicon_environment }}</p>
          <h1 class="title run-study-title">Run {{ accession }}</h1>

          <dl class="run-facts">
            <div class="run-fact">
              <dt>Organism</dt>
              <dd>{{ parsed.organism || 'Not recorded' }}</dd>
            </div>
            <div class="run-fact">
              <dt>Sequencing</dt>
              <dd>{{ amplicon_sequencing_summary }}</dd>
            </div>
            <div class="run-fact">
              <dt>Collected</dt>
              <dd>{{ parsed.collection_date || parsed.collection_time || 'Not recorded' }}</dd>
            </div>
            <div class="run-fact" v-if="parsed.realm || parsed.ecoregion">
              <dt>Location</dt>
              <dd>{{ [parsed.ecoregion, parsed.realm].filter(Boolean).join(' · ') }}</dd>
            </div>
          </dl>

          <div class="run-qc-flags">
            <button
              v-for="flag in amplicon_qc_flags"
              :key="flag.key"
              type="button"
              class="run-qc-flag"
              :class="flag.active ? flag.activeClass : 'run-qc-flag-clear'"
              aria-haspopup="dialog"
              :aria-expanded="qc_tooltip_key === flag.key"
              @mouseenter="showQcTooltip(flag, $event)"
              @mouseleave="hideQcTooltipDelayed"
              @focus="showQcTooltip(flag, $event)"
              @blur="hideQcTooltipDelayed"
              @keydown.esc="hideQcTooltip"
            >
              <b-icon :icon="flag.active ? flag.activeIcon : 'check-circle-outline'" size="is-small" />
              {{ flag.active ? flag.activeLabel : flag.clearLabel }}
            </button>
          </div>

          <div
            v-if="amplicon_qc_tooltip_flag"
            class="run-qc-tooltip"
            role="tooltip"
            :style="{ left: qc_tooltip_x + 'px', top: qc_tooltip_y + 'px' }"
            @mouseenter="keepQcTooltipOpen"
            @mouseleave="hideQcTooltipDelayed"
          >
            {{ qc_tooltip_text }}
            <span class="run-qc-tooltip-search">Search: {{ amplicon_qc_tooltip_flag.search }}</span>
          </div>

          <div class="run-subhead">
            <div class="run-link-pills">
              <a :href="'https://www.ncbi.nlm.nih.gov/bioproject/' + parsed.bioproject" class="run-link-pill">
                <b-icon icon="link-variant" size="is-small" /> BioProject {{ parsed.bioproject }}
              </a>
              <a :href="'https://www.ncbi.nlm.nih.gov/sra?term=' + accession" class="run-link-pill">
                <b-icon icon="link-variant" size="is-small" /> SRA {{ accession }}
              </a>
            </div>
            <div v-if="uniqueness" class="run-bioproject-similarity">
              <span
                class="unique-badge"
                role="button"
                :aria-pressed="unique_only"
                tabindex="0"
                aria-describedby="unique-tip"
                @pointerenter="onUniqueEnter"
                @pointerleave="onUniqueLeave"
                @focus="onUniqueFocus"
                @blur="hideUniqueTip"
                @keydown.esc="hideUniqueTip"
                @click="toggleUniqueOnly"
                @keydown.enter.prevent="toggleUniqueOnly"
                @keydown.space.prevent="toggleUniqueOnly">
                <span class="unique-bar" aria-hidden="true">
                  <span class="unique-bar-unique" :style="{ width: uniqueness.percent + '%' }"></span>
                  <span class="unique-bar-shared"></span>
                </span>
                {{ unique_only ? 'Showing ' : '' }}{{ uniqueness.unique }} unique {{ uniqueness.unique === 1 ? 'field' : 'fields' }}
                <b-icon v-if="unique_only" icon="close" size="is-small" aria-hidden="true" />
              </span>
              <span class="unique-badge-hint">{{ unique_only ? 'Press to show all fields' : 'Press to toggle filter to unique fields only' }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="container">
          <h3 class="title section-heading">
            <span>
              Community profile
              <button type="button" class="section-info" :aria-expanded="help_open.profile" aria-controls="profile-help" aria-label="About the community profile" @click="help_open.profile = !help_open.profile">
                <b-icon icon="information-outline" size="is-small" />
              </button>
            </span>
          </h3>
          <div v-if="help_open.profile" id="profile-help" class="content section-help">
            <p>
              The {{ parsed.amplicon_marker }} marker gene was amplified and sequenced, so each slice is the share of
              this run's <b>reads</b> assigned to a taxon, not genome coverage as on metagenome run pages.
              Click a taxon to see every amplicon run it is found in.
            </p>
            <p v-if="profiling_method">
              Profiled with Wagtail {{ profiling_method.wagtail }} against the {{ profiling_method.database }}
              reference database.
            </p>
          </div>
          <p v-if="condensed === null">Loading profile ..</p>
          <p v-else-if="condensed.no_data">No community profile is available for this run.</p>
          <template v-else>
            <Sunburst3
              :json_tree="condensed.condensed"
              :show_known_fraction="false"
              taxa_link_base="/amplicon/taxonomy/"
              coverage_label="Reads"
              :show_coverage_help="false"
              search_placeholder="Highlight taxa e.g. Ascomycota or g__Aspergillus" />
          </template>
        </div>
      </section>

      <section class="section">
        <div class="container is-large">
          <h3 class="title section-heading">
            <span>
              Sample information
              <button type="button" class="section-info" :aria-expanded="help_open.sample" aria-controls="sample-help" aria-label="About sample information" @click="help_open.sample = !help_open.sample">
                <b-icon icon="information-outline" size="is-small" />
              </button>
            </span>
          </h3>
          <div v-if="help_open.sample" id="sample-help" class="content section-help">
            <p>
              Details about the sample this run was sequenced from, such as where and when it was collected, the host or
              environment, and anything else the submitter recorded. Each row is coloured by where it came from. Links take you to each of the database's pages
            </p>
            <p>
              <b><a href="https://www.ncbi.nlm.nih.gov/sra" target="_blank" rel="noopener" class="source-link src-ncbi">NCBI</a> </b>: the US National Center for Biotechnology Information, home of the Sequence Read Archive.
            </p>
            <p>
              <b><a href="https://www.ebi.ac.uk/ena/browser/home" target="_blank" rel="noopener" class="source-link src-ena">ENA</a> </b>: the European Nucleotide Archive, run by EMBL-EBI.
            </p>
            <p>
              <b><a href="https://ddbj.nig.ac.jp/search" target="_blank" rel="noopener" class="source-link src-ddbj">DDBJ</a> </b>: the DNA Data Bank of Japan.
            </p>
            <p>
              <b><a href="https://metalog.embl.de/downloads" target="_blank" rel="noopener" class="source-link src-metalog">Metalog</a></b>: curated extra details from Metalog, added only when this sample is found there.
            </p>
            <p>
              The three archives share their data, so the colour shows the archive this run was submitted to, not who wrote each value.
            </p>
          </div>
          <div v-if="latLon !== null" class="amplicon-map">
            <l-map :zoom="2" :center="latLon" :use-global-leaflet="false" style="height: 300px; width: 100%; max-width: 550px">
              <l-tile-layer :url="tileUrl" :attribution="attribution" :options="{ referrerPolicy: 'origin' }" />
              <l-marker :lat-lng="latLon" />
            </l-map>
          </div>
          <RunMetadataTable :table_data="sample_rows" :unique_only="unique_only" />
        </div>
      </section>

      <section class="section">
        <div class="container is-large">
          <h3 class="title section-heading">
            <span>
              Derived information
              <button type="button" class="section-info" :aria-expanded="help_open.derived" aria-controls="derived-help" aria-label="About the derived information" @click="help_open.derived = !help_open.derived">
                <b-icon icon="information-outline" size="is-small" />
              </button>
            </span>
          </h3>
          <p class="section-note">Calculated for Sandpiper rather than recorded by the submitter.</p>
          <div v-if="help_open.derived" id="derived-help" class="content section-help">
            <p>
              <b>Ecoregion, realm and biome</b> come from the sample's coordinates, using the
              <a href="https://www.arcgis.com/home/item.html?id=903c3ae05b264c00a3b5e58a4561b7e6">UNEP-WCMC</a>
              marine ecoregions or
              <a href="https://data-gis.unep-wcmc.org/portal/home/item.html?id=db0b298237f544c8a08302b9908229b0">Terrestrial Ecoregions of the World</a>.
            </p>
            <p>
              <b>Latitude zone</b> comes from the latitude: tropics up to 23.5°, subtropics 23.5–35°, temperate
              35–60° and polar 60–90°, north or south of the equator. <b>Predicted season</b> comes from the
              collection month and zone, reversed in the southern hemisphere; the tropics have a dry and a wet season.
            </p>
            <p>
              <b>Depth zone</b> uses the <a href="https://www.noaa.gov/jetstream/ocean/layers-of-ocean">NOAA ocean layers</a>
              for marine samples and the <a href="https://www.nrcs.usda.gov/sites/default/files/2022-11/from-the-surface-down.pdf">USDA soil layers</a>
              for terrestrial ones.
            </p>
            <p>
              <b>Modelled temperature, pH and oxygen</b> are looked up for the sample's coordinates, depth and
              collection date. Marine samples use the <a href="https://www.ncei.noaa.gov/products/world-ocean-atlas">World Ocean Atlas</a>
              (temperature, dissolved oxygen) and <a href="https://glodap.info/">GLODAP</a> (pH). Terrestrial samples use
              <a href="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means">ERA5-Land monthly means</a> (temperature) and
              <a href="https://developers.google.com/earth-engine/datasets/catalog/OpenLandMap_SOL_SOL_PH-H2O_USDA-4C1A2A_M_v02">OpenLandMap</a> (soil pH).
            </p>
            <p>
              <b>Berger-Parker dominance</b> (<a href="https://www.statology.org/how-to-calculate-interpret-berger-parker-index/">what it measures</a>)
              <template v-if="has_derived('Inverse Simpson diversity')">and <b>inverse Simpson diversity</b> are</template><template v-else>is</template>
              calculated from the community profile at order level.
            </p>
          </div>
          <RunMetadataTable :table_data="metadata.metadata.amplicon_derived_metadata" :unique_only="unique_only" />
        </div>
      </section>

      <section class="section">
        <div class="container is-large">
          <h3 class="title section-heading">
            <span>
              Quality checks
              <button type="button" class="section-info" :aria-expanded="help_open.qc" aria-controls="qc-help" aria-label="About the quality checks" @click="help_open.qc = !help_open.qc">
                <b-icon icon="information-outline" size="is-small" />
              </button>
            </span>
          </h3>
          <p class="section-note">Quality checks are derived values calculated for additional specific information.</p>
          <div v-if="help_open.qc" id="qc-help" class="content section-help">
            <p>
              <b>Low complexity</b> means more than 95% of the reads are assigned to a single order (Berger-Parker
              index at order level above 0.95), close to the metagenome low complexity check. Runs that fail it are
              left out of the current amplicon data, so every run shown here is complex.
            </p>
            <p v-if="parsed.low_richness != null"><b>Low richness</b> means the order count is low: fewer than 20 orders were detected in the run.</p>
            <p v-if="parsed.low_effective_diversity != null">
              <b>Low effective diversity</b> means the inverse Simpson diversity, calculated at order level (shown under
              Derived information), is low: a few orders hold most of the reads even if many are present.
            </p>
          </div>
          <RunMetadataTable :table_data="metadata.metadata.qc_metadata" :unique_only="unique_only" />
        </div>
      </section>

      <section class="section">
        <div class="container is-large">
          <h3 class="title">Download</h3>
          <p>The community profile of this run can be downloaded as a <a :href="csvUrl">tab-separated file</a> with the read count and relative abundance of each taxon.</p>
        </div>
      </section>
    </div>

    <div v-else-if="metadata !== null">
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
              <dd>{{ metadata.metadata_parsed.organism }} &middot; {{ metadata.metadata_parsed.host_or_not_mature }}</dd>
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
              <div v-if="uniqueness" class="run-bioproject-similarity">
                <span
                  class="unique-badge"
                  role="button"
                  :aria-pressed="unique_only"
                  tabindex="0"
                  aria-describedby="unique-tip"
                  @pointerenter="onUniqueEnter"
                  @pointerleave="onUniqueLeave"
                  @focus="onUniqueFocus"
                  @blur="hideUniqueTip"
                  @keydown.esc="hideUniqueTip"
                  @click="toggleUniqueOnly"
                  @keydown.enter.prevent="toggleUniqueOnly"
                  @keydown.space.prevent="toggleUniqueOnly">
                  <span class="unique-bar" aria-hidden="true">
                    <span class="unique-bar-unique" :style="{ width: uniqueness.percent + '%' }"></span>
                    <span class="unique-bar-shared"></span>
                  </span>
                  {{ unique_only ? 'Showing ' : '' }}{{ uniqueness.unique }} unique {{ uniqueness.unique === 1 ? 'field' : 'fields' }}
                  <b-icon v-if="unique_only" icon="close" size="is-small" aria-hidden="true" />
                </span>
                <span class="unique-badge-hint">{{ unique_only ? 'Press to show all fields' : 'Press to toggle filter to unique fields only' }}</span>
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
          <div>
            <template v-if="condensed_tree != null">
              <Sunburst3 :json_tree="sunburst_tree" :overall_coverage="10.3" :known_species_fraction="known_species_fraction" root_label="Bacteria and Archaea" scope_note="Shows bacteria and archaea only. Viruses and eukaryotes are not profiled." />
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
          <RunMetadata :mdata="metadata.metadata" :mdata_parsed="metadata.metadata_parsed" :accession="accession" :unique_only="unique_only" />
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

          <p>Unfortunately, for now, the full SingleM OTU table of {{ accession }} (GTDB ({{ GTDB_VERSION }}) annotated) tab-separated file containing information about each OTU from each marker cannot be downloaded directly from this website.</p>
        </div>
      </section>
    </div>

    <section v-else-if="is_amplicon" class="section container amplicon-run">
      <b-message v-if="error_message !== null" title="Error" type="is-warning" :closable="false" has-icon>
        <p>{{ error_message }}</p>
      </b-message>
      <p v-else>Searching ..</p>
    </section>
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

    <!-- Hover/tap card for the "unique fields" badge; shared by both headers.
         Teleported to <body> so table cells and overflow:hidden can't clip it. -->
    <teleport to="body">
      <transition name="unique-tip">
        <div
          v-if="uniqueness"
          v-show="unique_tip_open"
          id="unique-tip"
          role="tooltip"
          class="unique-tip"
          :style="{ left: unique_tip_x + 'px', top: unique_tip_y + 'px' }">
          <p class="unique-tip-title">Metadata uniqueness</p>
          <p class="unique-tip-text">
            Fields recorded for this sample that no other sample in its BioProject has.
            A higher number means this sample carries extra context.
            {{ unique_only ? 'Click to show all fields.' : 'Click to show only these fields.' }}
          </p>
          <span class="unique-bar unique-bar-wide" aria-hidden="true">
            <span class="unique-bar-unique" :style="{ width: uniqueness.percent + '%' }"></span>
            <span class="unique-bar-shared"></span>
          </span>
          <dl class="unique-tip-list">
            <div><dt><span class="unique-dot unique-dot-unique"></span>Unique to sample</dt><dd>{{ uniqueness.unique }}</dd></div>
            <div><dt><span class="unique-dot unique-dot-shared"></span>Shared with BioProject</dt><dd>{{ uniqueness.shared }}</dd></div>
            <div class="unique-tip-total"><dt>Total fields</dt><dd>{{ uniqueness.total }}</dd></div>
          </dl>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script>

/* eslint-disable vue/no-unused-components */
import Sunburst3 from '@/components/Sunburst3.vue'
import RunMetadata from '@/components/RunMetadata.vue'
import RunMetadataTable from '@/components/RunMetadataTable.vue'
import { LMap, LTileLayer, LMarker } from '@vue-leaflet/vue-leaflet'

import { api_url, fetchRunMetadata, fetchRunCondensed } from '@/api'
import { fetchAmpliconRun, fetchAmpliconCondensed, ampliconCondensedCsvUrl } from '@/api/amplicon'
import { GTDB_VERSION, GLOBDB_VERSION } from '@/versions'
import { stopPageLoading, currentLoadingToken } from '@/store/pageLoading'
import rnaIcon from '@/assets/RNA-white.png'

// Amplicon runs: Wagtail version and reference database per marker, as reported by Rizky.
const PROFILING_METHODS = {
  '16S': { wagtail: '1.0.0', database: 'Microflora Danica v1.0.0' },
  '18S': { wagtail: '1.2.0', database: 'PR2 5.1.0' },
  ITS: { wagtail: '1.2.0', database: 'UNITE ver10_99_19.02.2025' }
}

export default {
  name: 'Run',
  title () {
    if (this.dataset === 'amplicon') return `Amplicon run ${this.accession} - Sandpiper`
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
      taxonomy_db: 'gtdb',
      qc_tooltip_key: null,
      qc_tooltip_text: '',
      qc_tooltip_x: 0,
      qc_tooltip_y: 0,
      qc_tooltip_close_timer: null,
      unique_only: false,
      unique_tip_open: false,
      unique_tip_x: 0,
      unique_tip_y: 0,
      // Amplicon runs only
      condensed: null,
      help_open: { profile: false, derived: false, qc: false, sample: false },
      tileUrl: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors'
    }
  },
  // dataset: 'amplicon' (from the /amplicon/run route) shows an amplicon run.
  props: ['accession', 'dataset'],
  components: {
    Sunburst3,
    RunMetadata,
    RunMetadataTable,
    LMap,
    LTileLayer,
    LMarker
  },
  computed: {
    is_amplicon () {
      return this.dataset === 'amplicon'
    },
    // --- Amplicon runs ---
    parsed () {
      return this.metadata.metadata_parsed
    },
    // Sample information rows tagged with where they came from: the run's
    // archive (from its accession prefix) or Metalog. Same as the metagenome page.
    sample_rows () {
      const archive = { SRR: 'ncbi', ERR: 'ena', DRR: 'ddbj' }[(this.accession || '').slice(0, 3).toUpperCase()]
      const own = (this.metadata.metadata.sample_info_metadata || []).map(r => ({ ...r, source: archive }))
      return own.concat((this.metadata.metadata.metalog_metadata || []).map(r => ({ ...r, source: 'metalog' })))
    },
    // Counts for the "unique fields" badge from the API's bioproject_similarity
    // (null for a BioProject with one run, which hides the badge).
    uniqueness () {
      const similarity = this.metadata?.metadata_parsed?.bioproject_similarity
      if (!similarity || !similarity.n_fields) return null
      const unique = similarity.unique_fields.length
      return {
        unique,
        shared: similarity.n_fields - unique,
        total: similarity.n_fields,
        percent: (unique / similarity.n_fields) * 100
      }
    },
    amplicon_sequencing_summary () {
      const parts = [this.parsed.amplicon_marker + ' amplicon']
      if (this.parsed.mbases !== null) parts.push(this.parsed.mbases + ' Mbp')
      return parts.join(' · ')
    },
    latLon () {
      const { latitude, longitude } = this.parsed
      return latitude === null || longitude === null ? null : [latitude, longitude]
    },
    profiling_method () {
      return PROFILING_METHODS[this.parsed.amplicon_marker] || null
    },
    csvUrl () {
      return ampliconCondensedCsvUrl(this.accession)
    },
    // Amplicon is a fact about the run, not a pass/fail verdict, so it uses
    // the categorical styling; the QC checks use red/green and the same
    // names as metagenome runs. Flags whose column isn't in the loaded data
    // come back as null and are hidden rather than shown as a passing check.
    amplicon_qc_flags () {
      const p = this.parsed
      const amplicon = `This run is amplicon sequencing data: one marker gene (${p.amplicon_marker}) was amplified and sequenced.`
      return [
        { key: 'amplicon', active: true, activeLabel: 'Amplicon', activeIcon: 'source-branch', activeClass: 'run-qc-flag-amplicon',
          activeHint: amplicon, clearHint: amplicon, search: `marker:${p.amplicon_marker}` },
        { key: 'low_complexity', active: p.low_complexity, activeLabel: 'Low complexity', clearLabel: 'Complex', activeIcon: 'flag-variant', activeClass: 'run-qc-flag-active',
          activeHint: 'More than 95% of this sample’s reads are assigned to a single order, so it is flagged as low complexity.',
          clearHint: 'No single order holds more than 95% of this sample’s reads.',
          search: 'low_complexity:yes / low_complexity:no' },
        { key: 'low_richness', active: p.low_richness, activeLabel: 'Low richness', clearLabel: 'High richness', activeIcon: 'flag-variant', activeClass: 'run-qc-flag-active',
          activeHint: 'Order count: low. Fewer than 20 orders were detected in this sample.',
          clearHint: 'Order count: high. 20 or more orders were detected in this sample.',
          search: 'low_richness:yes / low_richness:no' },
        { key: 'low_effective_diversity', active: p.low_effective_diversity, activeLabel: 'Low effective diversity', clearLabel: 'High effective diversity', activeIcon: 'flag-variant', activeClass: 'run-qc-flag-active',
          activeHint: 'This sample’s inverse Simpson diversity, calculated at order level, is low: a few orders hold most of the reads.',
          clearHint: 'This sample’s inverse Simpson diversity, calculated at order level, is not low.',
          search: 'low_effective_diversity:yes / low_effective_diversity:no' }
      ].filter(flag => flag.active != null)
    },
    amplicon_qc_tooltip_flag () {
      return this.qc_tooltip_key ? this.amplicon_qc_flags.find(f => f.key === this.qc_tooltip_key) || null : null
    },
    // --- end amplicon runs ---
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
  beforeUnmount () {
    this.hideUniqueTip()
  },
  created () {
    // fetch the data when the view is created and the data is
    // already being observed
    this.fetchData()
  },
  methods: {
    // "Unique fields" badge tooltip: below the badge, right edges aligned.
    // Hover and keyboard focus open it; Escape, a tap elsewhere or
    // scrolling closes it. Clicking the badge filters the tables instead.
    showUniqueTip (badge) {
      const rect = badge.getBoundingClientRect()
      const tooltipW = 260
      this.unique_tip_x = Math.max(10, Math.min(rect.right - tooltipW, window.innerWidth - tooltipW - 10))
      this.unique_tip_y = rect.bottom + 8
      this.unique_tip_open = true
      document.addEventListener('pointerdown', this.onUniqueOutside)
      window.addEventListener('scroll', this.hideUniqueTip, true)
    },
    hideUniqueTip () {
      this.unique_tip_open = false
      document.removeEventListener('pointerdown', this.onUniqueOutside)
      window.removeEventListener('scroll', this.hideUniqueTip, true)
    },
    onUniqueEnter (event) {
      if (event.pointerType !== 'touch') this.showUniqueTip(event.currentTarget)
    },
    onUniqueLeave (event) {
      if (event.pointerType !== 'touch') this.hideUniqueTip()
    },
    // A tap or click also focuses the badge, so only keyboard focus opens it here.
    onUniqueFocus (event) {
      if (event.target.matches(':focus-visible')) this.showUniqueTip(event.currentTarget)
    },
    toggleUniqueOnly () {
      this.unique_only = !this.unique_only
    },
    onUniqueOutside (event) {
      if (!event.target.closest('.unique-badge, .unique-tip')) this.hideUniqueTip()
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
      this.unique_only = false
      if (this.is_amplicon) return this.fetchAmpliconData()
      const accession = this.accession
      // Coming straight from an amplicon run (same page instance): don't let
      // the metagenome layout render the amplicon run's metadata meanwhile.
      if (this.metadata?.metadata_parsed?.amplicon) this.metadata = null

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
    has_derived (label) {
      return this.metadata.metadata.amplicon_derived_metadata.some(row => row.k === label)
    },
    async fetchAmpliconData () {
      this.metadata = null
      this.condensed = null
      this.error_message = null
      // Clear App.vue's loading backdrop once the gating metadata fetch
      // settles, success or failure.
      const loadingToken = currentLoadingToken()
      try {
        const res = await fetchAmpliconRun(this.accession)
        this.metadata = res.data
      } catch (err) {
        this.error_message = err.response?.data?.error || `Could not load amplicon run ${this.accession}.`
        return
      } finally {
        stopPageLoading(loadingToken)
      }
      try {
        const res = await fetchAmpliconCondensed(this.accession)
        this.condensed = res.data
      } catch (err) {
        this.condensed = { no_data: true }
        console.error('Amplicon profile request failed', err)
      }
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
    taxonomy_db: 'fetchCondensed'
  }
}
</script>

<style scoped>
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
/* On its own line, below the identifiers (sample id / BioProject and SRA
   pills) rather than beside them. */
.run-bioproject-similarity {
  flex: 1 1 100%;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.25rem 0.6rem;
}
.unique-badge-hint {
  color: #888;
  font-size: 0.8rem;
  font-style: italic;
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
/* "Unique fields" badge: the Run page chip style (solid marsh-teal fill, white
   text, darkens on hover) and the QC flags' dark popover. The tooltip is
   teleported to <body>, so the colours are set on both. */
.unique-badge,
.unique-tip {
  --unique-fill: hsl(174, 62%, 28%);
  --unique-fill-hover: hsl(174, 62%, 21%);
  --unique-bar: hsl(174, 55%, 78%);
  --unique-bar-rest: rgba(255, 255, 255, 0.3);
}
.unique-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  background: var(--unique-fill);
  color: hsl(0, 0%, 100%);
  font-size: 0.8rem;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color 0.15s;
}
.unique-badge:hover,
.unique-badge[aria-pressed="true"] {
  background: var(--unique-fill-hover);
}
.unique-badge[aria-pressed="true"] {
  box-shadow: 0 0 0 2px var(--unique-bar);
}
.unique-badge:focus-visible {
  outline: 2px solid #3273dc;
  outline-offset: 2px;
}
/* Split bar: light mint for unique, a faint remainder, 1px apart. */
.unique-bar {
  display: flex;
  gap: 1px;
  width: 38px;
  height: 6px;
  border-radius: 3px;
  overflow: hidden;
}
.unique-bar-unique {
  background: var(--unique-bar);
}
.unique-bar-shared {
  flex: 1;
  background: var(--unique-bar-rest);
}
.unique-bar-wide {
  width: 100%;
  margin: 0.6rem 0;
}
.unique-tip {
  position: fixed;
  z-index: var(--z-tooltip);
  width: 260px;
  padding: 0.6rem 0.8rem;
  border-radius: 8px;
  background: rgba(25, 25, 35, 0.97);
  color: #fff;
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.5);
  font-size: 0.78rem;
  line-height: 1.5;
}
.unique-tip-title {
  margin: 0 0 0.2rem;
  font-weight: 700;
}
.unique-tip-text {
  margin: 0;
  color: rgba(255, 255, 255, 0.6);
}
.unique-tip-list div {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 0.3rem;
}
.unique-tip-list dt {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.unique-tip-list dd {
  margin: 0;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.unique-tip-total {
  padding-top: 0.35rem;
  border-top: 1px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.6);
}
.unique-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.unique-dot-unique {
  background: var(--unique-bar);
}
.unique-dot-shared {
  background: var(--unique-bar-rest);
}
.unique-tip-enter-active,
.unique-tip-leave-active {
  transition: opacity 150ms ease-out, transform 150ms ease-out;
}
.unique-tip-enter-from,
.unique-tip-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
@media (prefers-reduced-motion: reduce) {
  .unique-badge,
  .unique-tip-enter-active,
  .unique-tip-leave-active {
    transition: none;
  }
}
/* Under the pills in the Identifiers block. */
.run-links-section .run-bioproject-similarity {
  margin-top: var(--space-3);
}
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
  background: hsl(271, 55%, 48%);
  color: hsl(0, 0%, 100%);
  font-size: 0.85rem;
  white-space: nowrap;
  transition: background-color 0.15s;
}
.run-related-pill:hover {
  background: hsl(271, 55%, 40%);
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
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: hsl(0, 0%, 50%);
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
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: hsl(0, 0%, 50%);
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
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: hsl(0, 0%, 50%);
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

/* Amplicon runs: the amplicon run page's own styles, scoped to its block. */
.run-page .amplicon-run,
.run-page .amplicon-run a,
.amplicon-run .run-study-title {
  overflow-wrap: anywhere;
}
.amplicon-run .amplicon-eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: hsl(205, 60%, 38%);
  margin-bottom: 0.35rem;
}
.amplicon-run .run-facts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-8) 2.2rem;
  margin: 0 0 1.65rem;
  padding-bottom: 1.65rem;
  border-bottom: 1px solid hsl(0, 0%, 90%);
}
.amplicon-run .run-fact {
  min-width: 0;
}
.amplicon-run .run-fact dt {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: hsl(0, 0%, 50%);
  margin-bottom: 0.2rem;
}
.amplicon-run .run-fact dd {
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}
.amplicon-run .run-qc-flags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) 0.9rem;
  margin-bottom: var(--space-6);
}
.amplicon-run .run-qc-flag {
  appearance: none;
  border: 0;
  font-family: inherit;
  cursor: help;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  font-size: 0.8rem;
  white-space: nowrap;
}
.amplicon-run .run-qc-flag-clear {
  background: hsl(141, 60%, 34%);
  color: hsl(0, 0%, 100%);
}
.amplicon-run .run-qc-flag-active {
  background: hsl(348, 75%, 42%);
  color: hsl(0, 0%, 100%);
}
.amplicon-run .run-qc-flag-amplicon {
  background: hsl(185, 55%, 32%);
  color: hsl(0, 0%, 100%);
}
.amplicon-run .run-link-pills {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.amplicon-run .run-link-pill {
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
.amplicon-run .run-link-pill:hover,
.amplicon-run .run-link-pill:focus-visible {
  border-color: hsl(271, 55%, 55%);
  background: hsl(271, 45%, 97%);
}
.amplicon-run .run-qc-tooltip {
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
.amplicon-run .run-qc-tooltip-search {
  display: block;
  margin-top: 0.4rem;
  font-family: "SF Mono", "Cascadia Code", Consolas, monospace;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.6);
}
.amplicon-run .section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
}
.amplicon-run .section-info {
  appearance: none;
  border: 0;
  padding: 0.15rem;
  background: transparent;
  cursor: pointer;
  vertical-align: middle;
  color: #7a7a7a;
}
.amplicon-run .section-info:hover {
  color: #363636;
}
.amplicon-run .section-info:focus-visible,
.amplicon-run .run-qc-flag:focus-visible {
  outline: 2px solid #3273dc;
  outline-offset: 2px;
}
.amplicon-run .section-note {
  margin: 0.15rem 0 0.75rem;
  font-size: 0.85rem;
  color: hsl(0, 0%, 40%);
}
.amplicon-run .section-help {
  margin-bottom: 1rem;
  overflow-wrap: anywhere;
}
.amplicon-run .amplicon-map {
  margin-bottom: 1rem;
}

@media (max-width: 768px) {
  .run-page .amplicon-run :deep(.section) {
      padding: 1.5rem 1rem;
    }
  .amplicon-run .run-study-title {
      font-size: 1.5rem;
      line-height: 1.25;
    }
  .amplicon-run .run-facts {
      flex-direction: column;
      gap: var(--space-4);
    }
}
</style>
