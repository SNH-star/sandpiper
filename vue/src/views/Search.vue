<template>
  <section class="section container">

    <section class="section">
      <p class="title is-4">Search for public metagenomes by taxonomy</p>
      <b-field>
        <div class="search-bar-row">
        <div class="search-autocomplete-wrap">
        <b-autocomplete id="taxonomy-search-input" name="taxonomy-search" :compat-fallthrough="false" v-model="taxonomy" rounded
          max-height="600px"
          icon="magnify"
          :data="autocomplete_taxons"
          :loading="isFetching"
          @keyup.enter="search_by_taxonomy"
          @typing="getAsyncData">
          <template #empty>No results found</template>
        </b-autocomplete>
        </div>
        </div>
      </b-field>
      <p class="help">
        Suggestions include <a href='http://gtdb.ecogenomic.org'>Genome Taxonomy Database (GTDB)</a> ({{ GTDB_VERSION }})
        and <a href='http://globdb.org'>GlobDB</a> ({{ GLOBDB_VERSION }}) taxonomies.
      </p>
      <br /><b-button type="is-primary" @click="search_by_taxonomy">Search</b-button>
    </section>

    <section class="section">
      <p class="title is-4">Search for run/sample/project accession</p>
      <b-field>
        <b-input id="accession-search-input" name="accession-search" :compat-fallthrough="false" v-model="accession" @keyup.enter="search_by_accession"></b-input>
      </b-field>
      <br /><b-button type="is-primary" @click="search_by_accession">Search</b-button>
    </section>

    <section class="section advanced-search-section">
      <div class="advanced-search-header">
        <p class="title is-4">Advanced search</p>
        <b-button type="is-text" size="is-small" icon-left="shuffle-variant" class="random-search-button" @click="search_by_random">Random Search</b-button>
      </div>
      <b-field label="Search query" label-for="advanced-search-query">
        <div class="search-bar-row">
        <div class="search-autocomplete-wrap">
          <b-input id="advanced-search-query" :compat-fallthrough="false" v-model="universal_query" placeholder="e.g. country: Australia, year: 2010-2015" icon="magnify" :loading="universal_loading" expanded
            @input="on_universal_input" @keydown="on_universal_keydown"></b-input>
          <div v-if="ghost_suffix" ref="universalGhost" class="search-ghost-overlay" aria-hidden="true">
            <span class="search-ghost-typed">{{ universal_query }}</span><span class="search-ghost-suffix">{{ ghost_suffix }}</span>
          </div>
          <ul v-if="ac_suggestions.length" class="search-suggest-dropdown" role="listbox">
            <li v-for="(s, i) in ac_suggestions" :key="s.kind + s.label" role="option" :aria-selected="i === ac_active_index"
              :class="{ 'is-active': i === ac_active_index }" @mousedown.prevent="on_universal_click_suggestion(s)">
              {{ s.label }}
            </li>
          </ul>
        </div>
        </div>
      </b-field>
      <p class="help">
        Key: value, comma-separated for multiple (e.g. "country: Australia, year: 2020").
        <button type="button" class="inline-toggle" :class="{ 'is-open': keys_open }" :aria-expanded="keys_open" aria-controls="advanced-search-keys" @click="toggle_keys()">
          List of keys
          <span class="disclosure-chevron" aria-hidden="true">
            <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </button>
        <InfoTooltipButton controls="advanced-search-popover" label="Show search syntax help" :expanded="active_tooltip === 'keys_info'" @open="showTooltip('keys_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" />
      </p>

      <div id="advanced-search-keys" class="keys-panel"
        :class="{ 'is-open': keys_open, 'is-settled': keys_settled }">
        <div class="keys-box">
          <div class="keys-columns">

            <div class="keys-group">
              <p class="keys-group-title">Keywords</p>
              <div class="keys-item"><code>keywords</code><span class="keys-example">e.g. "sponge reef, coral"</span></div>
            </div>

            <div class="keys-group">
              <p class="keys-group-title">Location</p>
              <div class="keys-item"><code>country</code><span class="keys-example">e.g. Australia</span></div>
              <div class="keys-item"><code>location</code><span class="keys-example">e.g. Pacific Ocean</span></div>
              <div class="keys-item"><code>latitude</code><span class="keys-example">e.g. -33.8 or -40-30</span></div>
              <div class="keys-item"><code>longitude</code><span class="keys-example">e.g. 151.2 or 140-160</span></div>
              <div class="keys-item"><code>grid</code><span class="keys-example">e.g. 10/-60;15/-60</span></div>
            </div>

            <div class="keys-group">
              <p class="keys-group-title">Sample</p>
              <div class="keys-item"><code>year</code><span class="keys-example">e.g. 2010 or 2010-2015</span></div>
              <div class="keys-item"><code>release_year</code><span class="keys-example">e.g. 2018 or 2015-2020</span></div>
              <div class="keys-item"><code>temperature</code><span class="keys-example">e.g. 25 or 20-30</span></div>
              <div class="keys-item"><code>depth</code><span class="keys-example">e.g. 100 or 0-200</span></div>
              <div class="keys-item"><code>environment</code><span class="keys-example">host or ecological</span></div>
              <div class="keys-item"><code>low_complexity</code><span class="keys-example">yes or no</span></div>
              <div class="keys-item"><code>synthetic</code><span class="keys-example">yes or no</span></div>
              <div class="keys-item"><code>non_metagenome_organism</code><span class="keys-example">yes or no</span></div>
              <div class="keys-item"><code>rna_or_non_dna</code><span class="keys-example">yes or no</span></div>
              <div class="keys-item">
                <code class="keys-item-label">age <InfoTooltipButton controls="advanced-search-popover" label="Show age search help" :expanded="active_tooltip === 'age_info'" @open="showTooltip('age_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" /></code>
                <span class="keys-example">e.g. 25 or 20-30</span>
              </div>
              <div class="keys-item">
                <code class="keys-item-label">habitat <InfoTooltipButton controls="advanced-search-popover" label="Show IndicPiper habitat values" :expanded="active_tooltip === 'habitat_info'" @open="showTooltip('habitat_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" /></code>
                <span class="keys-example">e.g. soil or soil&gt;=0.1</span>
              </div>
            </div>

            <div class="keys-group">
              <p class="keys-group-title">Quality / Size</p>
              <div class="keys-item"><code>spf</code><span class="keys-example">e.g. 50-100 or >50</span></div>
              <div class="keys-item"><code>ksf</code><span class="keys-example">e.g. 70-100 or >70</span></div>
              <div class="keys-item"><code>gbp</code><span class="keys-example">e.g. 2-10 or >2</span></div>
              <div class="keys-item"><code>reads</code><span class="keys-example">e.g. 10-100 or >10</span></div>
              <div class="keys-item"><code>read_length</code><span class="keys-example">e.g. 100-250 or >100</span></div>
            </div>

            <div class="keys-group">
              <p class="keys-group-title">Sequencing</p>
              <div class="keys-item">
                <code class="keys-item-label">platform <InfoTooltipButton controls="advanced-search-popover" label="Show platform search help" :expanded="active_tooltip === 'platform_info'" @open="showTooltip('platform_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" /></code>
                <span class="keys-example">e.g. Illumina</span>
              </div>
              <div class="keys-item">
                <code class="keys-item-label">instrument <InfoTooltipButton controls="advanced-search-popover" label="Show instrument search help" :expanded="active_tooltip === 'instrument_info'" @open="showTooltip('instrument_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" /></code>
                <span class="keys-example">e.g. HiSeq 2500</span>
              </div>
              <div class="keys-item">
                <code class="keys-item-label">library_strategy <InfoTooltipButton controls="advanced-search-popover" label="Show library strategy search help" :expanded="active_tooltip === 'library_info'" @open="showTooltip('library_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" /></code>
                <span class="keys-example">e.g. WGS</span>
              </div>
              <p class="keys-group-title" style="margin-top: 1rem;">Taxonomy</p>
              <div class="keys-item">
                <code class="keys-item-label">organism <InfoTooltipButton controls="advanced-search-popover" label="Show organism search help" :expanded="active_tooltip === 'organism_info'" @open="showTooltip('organism_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" /></code>
                <span class="keys-example">e.g. marine metagenome</span>
              </div>
              <div class="keys-item">
                <code class="keys-item-label">taxonomy <InfoTooltipButton controls="advanced-search-popover" label="Show taxonomy search help" :expanded="active_tooltip === 'taxonomy_info'" @open="showTooltip('taxonomy_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" /></code>
                <span class="keys-example">e.g. s__Prochlorococcus</span>
              </div>
            </div>

            <div class="keys-group">
              <p class="keys-group-title">Study</p>
              <div class="keys-item"><code>study</code><span class="keys-example">e.g. Tara Oceans</span></div>
              <div class="keys-item"><code>abstract</code><span class="keys-example">e.g. coral reef</span></div>
              <div class="keys-item"><code>bioproject</code><span class="keys-example">e.g. PRJNA12345</span></div>
              <p class="keys-group-title" style="margin-top: 1rem;">Identifiers</p>
              <div class="keys-item"><code>sra_study</code><span class="keys-example">e.g. SRP012345</span></div>
              <div class="keys-item"><code>experiment</code><span class="keys-example">e.g. SRX012345</span></div>
              <div class="keys-item"><code>sample_acc</code><span class="keys-example">e.g. SRS012345</span></div>
              <div class="keys-item"><code>biosample</code><span class="keys-example">e.g. SAMN12345</span></div>
              <p class="keys-group-title" style="margin-top: 1rem;">Submitter</p>
              <div class="keys-item"><code>organisation</code><span class="keys-example">e.g. MIT or Woods Hole</span></div>
              <p class="keys-group-title" style="margin-top: 1rem;">Metadata</p>
              <div class="keys-item">
                <code class="keys-item-label">metadata <InfoTooltipButton controls="advanced-search-popover" label="Show BioSample metadata search help" :expanded="active_tooltip === 'metadata_info'" @open="showTooltip('metadata_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" /></code>
                <span class="keys-example">e.g. sex=male or body_site=arm</span>
              </div>
              <div class="keys-item">
                <code class="keys-item-label">metalog <InfoTooltipButton controls="advanced-search-popover" label="Show Metalog metadata search help" :expanded="active_tooltip === 'metalog_info'" @open="showTooltip('metalog_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" /></code>
                <span class="keys-example">e.g. host=Sus scrofa or diabetes</span>
              </div>
            </div>

          </div>
          <div class="keys-syntax-row">
            <span class="keys-syntax-title">Query Syntax</span>
            <div class="keys-syntax-items">
              <span class="keys-syntax-item"><code>2-10</code> range</span>
              <span class="keys-syntax-item"><code>&gt;10</code> greater than</span>
              <span class="keys-syntax-item"><code>&gt;=10</code> at least</span>
              <span class="keys-syntax-item"><code>&lt;10</code> less than</span>
              <span class="keys-syntax-item"><code>&lt;=10</code> at most</span>
              <span class="keys-syntax-item"><code>10</code> exact / approx</span>
              <span class="keys-syntax-item"><code>(empty)</code> present, any value e.g. "age:"</span>
              <span class="keys-syntax-item"><code>"Oahu, Kaneohe Bay"</code> quotes keep a comma inside one value</span>
            </div>
          </div>
          <div class="keys-example-row">
            <span class="keys-example-label">Example:</span>
            <code class="keys-example-query">year: 2015-2020, metadata: sex=male</code>
            <b-button size="is-small" type="is-primary" @click="try_universal_example">Try it</b-button>
          </div>
        </div>
      </div>

      <div class="disclosure-row disclosure-row-standalone">
        <button type="button" class="disclosure-toggle" :class="{ 'is-open': advanced_open }" :aria-expanded="advanced_open" aria-controls="advanced-search-options" @click="toggle_advanced">
          Advanced options
          <span class="disclosure-chevron" aria-hidden="true">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </button>
      </div>

      <div id="advanced-search-options" class="advanced-panel"
        :class="{ 'is-open': advanced_open, 'is-settled': advanced_settled }">
        <div class="advanced-panel-clip">
        <div class="adv-box">
          <section class="adv-group" :class="{ 'is-open': adv_groups.keywords }">
            <button type="button" class="adv-group-toggle" :aria-expanded="adv_groups.keywords" aria-controls="adv-group-keywords" @click="toggle_adv_group('keywords')">
              <span class="adv-group-title">Keywords</span>
              <span class="adv-group-chevron" aria-hidden="true"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></span>
              <span class="adv-group-hint">{{ adv_group_hint('keywords') }}</span>
            </button>
            <div class="adv-group-collapse"
              :class="{ 'is-open': adv_groups.keywords, 'is-settled': adv_group_settled.keywords }"
              :inert="!adv_groups.keywords">
              <div id="adv-group-keywords" class="adv-group-body">
                <p class="adv-group-note">{{ KEYWORDS_NOTE }}</p>
                <b-field grouped group-multiline class="adv-group-row">
                  <b-field class="adv-field adv-field-keywords" label="Keywords" label-for="adv-keywords">
                    <b-input id="adv-keywords" name="adv-keywords" :compat-fallthrough="false" v-model="adv.keywords" placeholder="e.g. sponge reef, coral" icon="magnify" expanded />
                  </b-field>
                </b-field>
              </div>
            </div>
          </section>

          <section class="adv-group" :class="{ 'is-open': adv_groups.location }">
            <button type="button" class="adv-group-toggle" :aria-expanded="adv_groups.location" aria-controls="adv-group-location" @click="toggle_adv_group('location')">
              <span class="adv-group-title">Location<span class="adv-group-subtitle">Search by map included</span></span>
              <span class="adv-group-chevron" aria-hidden="true"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></span>
              <span class="adv-group-hint">{{ adv_group_hint('location') }}</span>
            </button>
            <div class="adv-group-collapse"
              :class="{ 'is-open': adv_groups.location, 'is-settled': adv_group_settled.location }"
              :inert="!adv_groups.location">
              <div id="adv-group-location" class="adv-group-body">
                <b-field grouped group-multiline class="adv-group-row">
                  <PresenceField class="adv-field" label="Country" v-model="adv.country" v-model:present="adv_present.country" placeholder="e.g. Australia" search-field="country" />
                  <PresenceField class="adv-field" label="Location" v-model="adv.location" v-model:present="adv_present.location" placeholder="e.g. Pacific Ocean" search-field="location" />
                  <PresenceField class="adv-field" label="Latitude" v-model="adv.latitude" v-model:present="adv_present.latitude" placeholder="e.g. -33.8 or -40-30" :error-message="adv_errors.latitude" @input="on_adv_field_input('latitude')" />
                  <PresenceField class="adv-field" label="Longitude" v-model="adv.longitude" v-model:present="adv_present.longitude" placeholder="e.g. 151.2 or 140-160" :error-message="adv_errors.longitude" @input="on_adv_field_input('longitude')" />
                  <SearchGridField :model-value="adv.grid" @change="on_grid_change">
                    <template #label-suffix>
                      <InfoTooltipButton controls="advanced-search-popover" label="Show graph search help" :expanded="active_tooltip === 'grid_info'" @open="showTooltip('grid_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" />
                    </template>
                  </SearchGridField>
                </b-field>
              </div>
            </div>
          </section>

          <section class="adv-group" :class="{ 'is-open': adv_groups.sample }">
            <button type="button" class="adv-group-toggle" :aria-expanded="adv_groups.sample" aria-controls="adv-group-sample" @click="toggle_adv_group('sample')">
              <span class="adv-group-title">Sample</span>
              <span class="adv-group-chevron" aria-hidden="true"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></span>
              <span class="adv-group-hint">{{ adv_group_hint('sample') }}</span>
            </button>
            <div class="adv-group-collapse"
              :class="{ 'is-open': adv_groups.sample, 'is-settled': adv_group_settled.sample }"
              :inert="!adv_groups.sample">
              <div id="adv-group-sample" class="adv-group-body">
                <b-field grouped group-multiline class="sample-group-field adv-group-row">
                  <PresenceField class="adv-field" label="Collection year" v-model="adv.year" v-model:present="adv_present.year" placeholder="e.g. 2010 or 2010-2015" :error-message="adv_errors.year" @input="on_adv_field_input('year')" />
                  <PresenceField class="adv-field" label="Release year" v-model="adv.release_year" v-model:present="adv_present.release_year" placeholder="e.g. 2018 or 2015-2020" :error-message="adv_errors.release_year" @input="on_adv_field_input('release_year')" />
                  <PresenceField class="adv-field" label="Temperature (°C)" v-model="adv.temperature" v-model:present="adv_present.temperature" placeholder="e.g. 25 or 20-30" :error-message="adv_errors.temperature" @input="on_adv_field_input('temperature')" />
                  <PresenceField class="adv-field" label="Depth (m)" v-model="adv.depth" v-model:present="adv_present.depth" placeholder="e.g. 100 or 0-200" :error-message="adv_errors.depth" @input="on_adv_field_input('depth')" />
                  <PresenceField class="adv-field" label="Age" v-model="adv.age" v-model:present="adv_present.age" placeholder="e.g. 25 or 20-30" :error-message="adv_errors.age" @input="on_adv_field_input('age')">
                    <template #label-suffix>
                      <InfoTooltipButton controls="advanced-search-popover" label="Show age search help" :expanded="active_tooltip === 'age_info'" @open="showTooltip('age_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" />
                    </template>
                  </PresenceField>
                  <div class="field is-floating-label adv-field">
                    <span class="label">Environment</span>
                    <div class="buttons has-addons" role="group" aria-label="Environment">
                      <b-button size="is-small" :type="adv.environment === 'host' ? 'is-primary' : ''" :aria-pressed="adv.environment === 'host'" @click="toggle_env('host')">Host</b-button>
                      <b-button size="is-small" :type="adv.environment === 'ecological' ? 'is-primary' : ''" :aria-pressed="adv.environment === 'ecological'" @click="toggle_env('ecological')">Ecological</b-button>
                      <b-button size="is-small" :type="adv_present.environment ? 'is-primary' : ''" :aria-pressed="adv_present.environment" title="Match any run with an environment classification" @click="toggle_environment_present">Any</b-button>
                    </div>
                  </div>
                  <div class="field is-floating-label low-complexity-field adv-field">
                    <span class="label">Synthetic <b-icon v-if="universal_loading" icon="loading" custom-class="mdi-spin" size="is-small" /><InfoTooltipButton v-else controls="advanced-search-popover" label="Show synthetic search help" :expanded="active_tooltip === 'synthetic_info'" @open="showTooltip('synthetic_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" /></span>
                    <div class="buttons has-addons" role="group" aria-label="Synthetic">
                      <b-button size="is-small" style="width: 82px;" :type="adv.synthetic === 'yes' ? 'is-primary' : ''" :aria-pressed="adv.synthetic === 'yes'" @click="toggle_synthetic('yes')">Yes</b-button>
                      <b-button size="is-small" style="width: 82px;" :type="adv.synthetic === 'no' ? 'is-primary' : ''" :aria-pressed="adv.synthetic === 'no'" @click="toggle_synthetic('no')">No</b-button>
                      <b-button size="is-small" :type="adv_present.synthetic ? 'is-primary' : ''" :aria-pressed="adv_present.synthetic" title="Match any run with a synthetic classification" @click="toggle_synthetic_present">Any</b-button>
                    </div>
                  </div>
                  <div class="field is-floating-label low-complexity-field adv-field">
                    <span class="label">Non-metagenome organism <b-icon v-if="universal_loading" icon="loading" custom-class="mdi-spin" size="is-small" /><InfoTooltipButton v-else controls="advanced-search-popover" label="Show non-metagenome organism search help" :expanded="active_tooltip === 'non_metagenome_organism_info'" @open="showTooltip('non_metagenome_organism_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" /></span>
                    <div class="buttons has-addons" role="group" aria-label="Non-metagenome organism">
                      <b-button size="is-small" style="width: 82px;" :type="adv.non_metagenome_organism === 'yes' ? 'is-primary' : ''" :aria-pressed="adv.non_metagenome_organism === 'yes'" @click="toggle_non_metagenome_organism('yes')">Yes</b-button>
                      <b-button size="is-small" style="width: 82px;" :type="adv.non_metagenome_organism === 'no' ? 'is-primary' : ''" :aria-pressed="adv.non_metagenome_organism === 'no'" @click="toggle_non_metagenome_organism('no')">No</b-button>
                      <b-button size="is-small" :type="adv_present.non_metagenome_organism ? 'is-primary' : ''" :aria-pressed="adv_present.non_metagenome_organism" title="Match any run with a non-metagenome-organism classification" @click="toggle_non_metagenome_organism_present">Any</b-button>
                    </div>
                  </div>
                  <div class="field is-floating-label low-complexity-field adv-field">
                    <span class="label">RNA/non-DNA <b-icon v-if="universal_loading" icon="loading" custom-class="mdi-spin" size="is-small" /><InfoTooltipButton v-else controls="advanced-search-popover" label="Show RNA/non-DNA search help" :expanded="active_tooltip === 'rna_or_non_dna_info'" @open="showTooltip('rna_or_non_dna_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" /></span>
                    <div class="buttons has-addons" role="group" aria-label="RNA/non-DNA">
                      <b-button size="is-small" style="width: 82px;" :type="adv.rna_or_non_dna === 'yes' ? 'is-primary' : ''" :aria-pressed="adv.rna_or_non_dna === 'yes'" @click="toggle_rna_or_non_dna('yes')">Yes</b-button>
                      <b-button size="is-small" style="width: 82px;" :type="adv.rna_or_non_dna === 'no' ? 'is-primary' : ''" :aria-pressed="adv.rna_or_non_dna === 'no'" @click="toggle_rna_or_non_dna('no')">No</b-button>
                      <b-button size="is-small" :type="adv_present.rna_or_non_dna ? 'is-primary' : ''" :aria-pressed="adv_present.rna_or_non_dna" title="Match any run with an RNA/non-DNA classification" @click="toggle_rna_or_non_dna_present">Any</b-button>
                    </div>
                  </div>
                  <b-field grouped class="low-complexity-habitat-group">
                    <div class="field is-floating-label low-complexity-field adv-field">
                      <span class="label">Low complexity <b-icon v-if="universal_loading" icon="loading" custom-class="mdi-spin" size="is-small" /><InfoTooltipButton v-else controls="advanced-search-popover" label="Show low complexity search help" :expanded="active_tooltip === 'low_complexity_info'" @open="showTooltip('low_complexity_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" /></span>
                      <div class="buttons has-addons" role="group" aria-label="Low complexity">
                        <b-button size="is-small" style="width: 82px;" :type="adv.low_complexity === 'yes' ? 'is-primary' : ''" :aria-pressed="adv.low_complexity === 'yes'" @click="toggle_low_complexity('yes')">Yes</b-button>
                        <b-button size="is-small" style="width: 82px;" :type="adv.low_complexity === 'no' ? 'is-primary' : ''" :aria-pressed="adv.low_complexity === 'no'" @click="toggle_low_complexity('no')">No</b-button>
                        <b-button size="is-small" :type="adv_present.low_complexity ? 'is-primary' : ''" :aria-pressed="adv_present.low_complexity" title="Match any run with a low-complexity classification" @click="toggle_low_complexity_present">Any</b-button>
                      </div>
                    </div>
                    <PresenceField class="adv-field" label="IndicPiper habitat" v-model="adv.habitat" v-model:present="adv_present.habitat" placeholder="e.g. soil or soil>=0.1" search-field="habitat">
                      <template #label-suffix>
                        <InfoTooltipButton controls="advanced-search-popover" label="Show IndicPiper habitat values" :expanded="active_tooltip === 'habitat_info'" @open="showTooltip('habitat_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" />
                      </template>
                    </PresenceField>
                  </b-field>
                </b-field>
              </div>
            </div>
          </section>

          <section class="adv-group" :class="{ 'is-open': adv_groups.quality }">
            <button type="button" class="adv-group-toggle" :aria-expanded="adv_groups.quality" aria-controls="adv-group-quality" @click="toggle_adv_group('quality')">
              <span class="adv-group-title">Quality / Size</span>
              <span class="adv-group-chevron" aria-hidden="true"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></span>
              <span class="adv-group-hint">{{ adv_group_hint('quality') }}</span>
            </button>
            <div class="adv-group-collapse"
              :class="{ 'is-open': adv_groups.quality, 'is-settled': adv_group_settled.quality }"
              :inert="!adv_groups.quality">
              <div id="adv-group-quality" class="adv-group-body">
                <b-field grouped group-multiline class="adv-group-row">
                  <PresenceField class="adv-field" label="SPF %" v-model="adv.spf" v-model:present="adv_present.spf" placeholder="e.g. 80 or 50-100" :error-message="adv_errors.spf" @input="on_adv_field_input('spf')" />
                  <PresenceField class="adv-field" label="Known species fraction %" v-model="adv.ksf" v-model:present="adv_present.ksf" placeholder="e.g. 90 or 70-100" :error-message="adv_errors.ksf" @input="on_adv_field_input('ksf')" />
                  <PresenceField class="adv-field" label="Size (Gbp)" v-model="adv.gbp" v-model:present="adv_present.gbp" placeholder="e.g. 5 or 2-10" :error-message="adv_errors.gbp" @input="on_adv_field_input('gbp')" />
                  <PresenceField class="adv-field" label="Reads (millions)" v-model="adv.reads" v-model:present="adv_present.reads" placeholder="e.g. 50 or 10-100" :error-message="adv_errors.reads" @input="on_adv_field_input('reads')" />
                  <PresenceField class="adv-field" label="Read length (bp)" v-model="adv.read_length" v-model:present="adv_present.read_length" placeholder="e.g. 150 or 100-250" :error-message="adv_errors.read_length" @input="on_adv_field_input('read_length')" />
                </b-field>
              </div>
            </div>
          </section>

          <section class="adv-group" :class="{ 'is-open': adv_groups.sequencing }">
            <button type="button" class="adv-group-toggle" :aria-expanded="adv_groups.sequencing" aria-controls="adv-group-sequencing" @click="toggle_adv_group('sequencing')">
              <span class="adv-group-title">Sequencing</span>
              <span class="adv-group-chevron" aria-hidden="true"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></span>
              <span class="adv-group-hint">{{ adv_group_hint('sequencing') }}</span>
            </button>
            <div class="adv-group-collapse"
              :class="{ 'is-open': adv_groups.sequencing, 'is-settled': adv_group_settled.sequencing }"
              :inert="!adv_groups.sequencing">
              <div id="adv-group-sequencing" class="adv-group-body">
                <b-field grouped group-multiline class="adv-group-row">
                  <PresenceField class="adv-field" label="Platform" v-model="adv.platform" v-model:present="adv_present.platform" placeholder="e.g. Illumina" search-field="platform">
                    <template #label-suffix>
                      <InfoTooltipButton controls="advanced-search-popover" label="Choose a platform value" :expanded="active_tooltip === 'platform'" @open="showTooltip('platform', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" />
                    </template>
                  </PresenceField>
                  <PresenceField class="adv-field" label="Instrument" v-model="adv.instrument" v-model:present="adv_present.instrument" placeholder="e.g. HiSeq 2500" search-field="instrument">
                    <template #label-suffix>
                      <InfoTooltipButton controls="advanced-search-popover" label="Choose an instrument value" :expanded="active_tooltip === 'instrument'" @open="showTooltip('instrument', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" />
                    </template>
                  </PresenceField>
                  <PresenceField class="adv-field" label="Library strategy" v-model="adv.library_strategy" v-model:present="adv_present.library_strategy" placeholder="e.g. WGS" search-field="library_strategy">
                    <template #label-suffix>
                      <InfoTooltipButton controls="advanced-search-popover" label="Choose a library strategy value" :expanded="active_tooltip === 'library'" @open="showTooltip('library', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" />
                    </template>
                  </PresenceField>
                </b-field>
              </div>
            </div>
          </section>

          <teleport to="body">
            <div v-if="active_tooltip" id="advanced-search-popover" class="info-tooltip-box" :class="{ 'is-scroll-list': active_tooltip === 'metalog_info' }" :style="{ left: tooltip_x + 'px', top: tooltip_y + 'px' }" role="dialog" aria-label="Search field help" @mouseenter="keepTooltipOpen" @mouseleave="hideTooltipDelayed" @focusin="keepTooltipOpen" @focusout="hideTooltipDelayed" @keydown.esc="hideTooltip">
              <template v-if="active_tooltip === 'organism_info'">
                <p class="info-tooltip-title">Organism</p>
                <p style="color: rgba(255,255,255,0.85); font-size: 0.78rem;">
                  Searches the NCBI taxon assigned to the run. Covers both single-organism identifications
                  (e.g. <em>Homo sapiens</em>, <em>Vibrio cholerae</em>) and NCBI's metagenome pseudo-taxa
                  (e.g. <em>soil metagenome</em>, <em>human gut metagenome</em>) — use this field for
                  metagenome searches too.
                </p>
              </template>
              <template v-if="active_tooltip === 'taxonomy_info'">
                <p class="info-tooltip-title">Taxonomy — detected presence only</p>
                <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.85); font-size: 0.78rem;">
                  Filters runs where a taxon was <strong style="color:#fff">detected</strong> by SingleM — not that the sample is primarily composed of it.
                </p>
                <p style="color: rgba(255,255,255,0.65); font-size: 0.78rem; margin-bottom: 0.4rem;">
                  SingleM analyses reads aligning to conserved single-copy marker genes, so a run labelled "marine metagenome" can still match <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">taxonomy: s__Prochlorococcus</code> if that organism was present in the community.
                </p>
                <p style="color: rgba(255,255,255,0.45); font-size: 0.72rem;">Use GTDB taxonomy strings, e.g. d__, p__, c__, o__, f__, g__, s__</p>
              </template>
              <template v-if="active_tooltip === 'platform_info'">
                <p class="info-tooltip-title">Platform — all values <span class="tooltip-hint">(click to use)</span></p>
                <div class="info-tooltip-grid">
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ILLUMINA')">ILLUMINA</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina')">Illumina</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Metagenomic')">Metagenomic</button>
                </div>
              </template>
              <template v-if="active_tooltip === 'instrument_info'">
                <p class="info-tooltip-title">Instrument — all values <span class="tooltip-hint">(click to use)</span></p>
                <div class="info-tooltip-grid">
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina NovaSeq 6000')">Illumina NovaSeq 6000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 2500')">Illumina HiSeq 2500</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 4000')">Illumina HiSeq 4000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('NextSeq 500')">NextSeq 500</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 2000')">Illumina HiSeq 2000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina MiSeq')">Illumina MiSeq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('HiSeq X Ten')">HiSeq X Ten</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina NovaSeq X')">Illumina NovaSeq X</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('NextSeq 2000')">NextSeq 2000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('NextSeq 550')">NextSeq 550</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 3000')">Illumina HiSeq 3000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina NovaSeq X Plus')">Illumina NovaSeq X Plus</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq X')">Illumina HiSeq X</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 1000')">Illumina HiSeq 1000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 1500')">Illumina HiSeq 1500</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('NextSeq 1000')">NextSeq 1000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina MiniSeq')">Illumina MiniSeq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina Genome Analyzer IIx')">Illumina Genome Analyzer IIx</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina Genome Analyzer II')">Illumina Genome Analyzer II</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina Genome Analyzer')">Illumina Genome Analyzer</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq X Ten')">Illumina HiSeq X Ten</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('HiSeq X Five')">HiSeq X Five</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiScanSQ')">Illumina HiScanSQ</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina iSeq 100')">Illumina iSeq 100</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Nova seq')">Nova seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('MiSeq i100')">MiSeq i100</button>
                </div>
              </template>
              <template v-if="active_tooltip === 'library_info'">
                <p class="info-tooltip-title">Library strategy — all values <span class="tooltip-hint">(click to use)</span></p>
                <div class="info-tooltip-grid">
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('WGS')">WGS</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('OTHER')">OTHER</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('AMPLICON')">AMPLICON</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('WGA')">WGA</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('RNA-Seq')">RNA-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Targeted-Capture')">Targeted-Capture</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('POOLCLONE')">POOLCLONE</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('WXS')">WXS</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('WCS')">WCS</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Hi-C')">Hi-C</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('CLONE')">CLONE</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ChIP-Seq')">ChIP-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Bisulfite-Seq')">Bisulfite-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Synthetic-Long-Read')">Synthetic-Long-Read</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('RAD-Seq')">RAD-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ATAC-seq')">ATAC-seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('CLONEEND')">CLONEEND</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Tn-Seq')">Tn-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('shotgun sequencing')">shotgun sequencing</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('FAIRE-seq')">FAIRE-seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('miRNA-Seq')">miRNA-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('FL-cDNA')">FL-cDNA</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('DNase-Hypersensitivity')">DNase-Hypersensitivity</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('CTS')">CTS</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('MRE-Seq')">MRE-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('FINISHING')">FINISHING</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ssRNA-seq')">ssRNA-seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('EST')">EST</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('GBS')">GBS</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('RIP-Seq')">RIP-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ncRNA-Seq')">ncRNA-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Ribo-seq')">Ribo-seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Tethered Chromatin Conformation Capture')">Tethered Chromatin Conformation Capture</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('NOMe-Seq')">NOMe-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('MBD-Seq')">MBD-Seq</button>
                </div>
              </template>
              <template v-if="active_tooltip === 'habitat_info'">
                <p class="info-tooltip-title">IndicPiper habitat — all values <span class="tooltip-hint">(click to use)</span></p>
                <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.8); font-size: 0.78rem;">
                  Matches runs whose genus composition includes indicator genera for this habitat
                  (<a href="https://github.com/cliffbueno/IndicPiper" target="_blank" rel="noopener" style="color:#8ecbff;">IndicPiper</a>
                  analysis). See the run page's "IndicPiper habitat indicators" section for per-run scores.
                  Add <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">&gt;=</code>, <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">&gt;</code>, <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">&lt;=</code> or <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">&lt;</code> plus a number to threshold on that habitat's score, e.g. <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">soil&gt;=0.1</code>. Leave the name off and just give a comparison, e.g. <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">&gt;0.5</code>, to match runs whose strongest habitat match (whichever habitat that is) exceeds it.
                </p>
                <div class="info-tooltip-grid">
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('human oral')">human oral</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('mammalian gut')">mammalian gut</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('human vaginal')">human vaginal</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('wastewater')">wastewater</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('soil')">soil</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('phyllosphere')">phyllosphere</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('human skin')">human skin</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('freshwater sediment')">freshwater sediment</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('freshwater water')">freshwater water</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('glacier')">glacier</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('marine sediment')">marine sediment</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('marine water')">marine water</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('hydrothermal vent')">hydrothermal vent</button>
                </div>
              </template>
              <template v-if="active_tooltip === 'grid_info'">
                <p class="info-tooltip-title">Graph — pick places on a map</p>
                <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.85); font-size: 0.78rem;">
                  An interactive world map of the runs that have coordinates, grouped into 5° squares. Each circle is one square and its
                  area shows how many runs it holds. Hover a circle to see its counts.
                </p>
                <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.85); font-size: 0.78rem;">
                  The switch above the map chooses which runs are drawn: <strong style="color: var(--color-sample-host);">host-associated</strong> (purple, e.g. gut or skin samples)
                  or <strong style="color: var(--color-sample-ecological);">ecological</strong> (green, e.g. soil or ocean). Both types share one circle scale, so the two views can be compared.
                </p>
                <p style="color: rgba(255,255,255,0.55); font-size: 0.75rem;">
                  Click a circle to pick its square under the sample type shown; you can pick as many as you like, mixing host-associated and
                  ecological squares, and click again to drop one. The search uses only the picked squares and leaves Latitude and
                  Longitude alone. Clear all drops every square.
                </p>
              </template>
              <template v-if="active_tooltip === 'age_info'">
                <p class="info-tooltip-title">Age</p>
                <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.85); font-size: 0.78rem;">
                  Searches <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">age</code> and <code style="background:rgba(255,255,255,0.15); padding: 0.1rem 0.3rem; border-radius:3px;">host_age</code> BioSample attributes by their numeric value.
                </p>
                <p style="color: rgba(255,255,255,0.55); font-size: 0.75rem;">
                  Age is reported at face value — the relevant scale depends on the organism and study. Could be years for a human cohort, weeks for neonates, or centuries for a tree.
                </p>
              </template>
              <template v-if="active_tooltip === 'low_complexity_info'">
                <p class="info-tooltip-title">Low complexity</p>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.85); font-size: 0.78rem;">
                  Flags samples where ≥95% of the community is assigned to a single taxonomic order — usually a sign of a heavily dominated or degraded community rather than a typical diverse metagenome.
                </p>
                <p style="color: rgba(255,255,255,0.55); font-size: 0.75rem;">
                  Yes = sample primarily dominated by 1 order (&gt;95%)<br />
                  No = community spread across multiple orders
                </p>
              </template>
              <template v-if="active_tooltip === 'synthetic_info'">
                <p class="info-tooltip-title">Synthetic</p>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.85); font-size: 0.78rem;">
                  Flags samples whose reads appear synthetic — e.g. simulated data or a mock community — rather than a real environmental sample.
                </p>
                <p style="color: rgba(255,255,255,0.55); font-size: 0.75rem;">
                  Yes = simulated reads or a mock/synthetic community standard<br />
                  No = a real environmental or host-associated sample
                </p>
              </template>
              <template v-if="active_tooltip === 'non_metagenome_organism_info'">
                <p class="info-tooltip-title">Non-metagenome organism</p>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.85); font-size: 0.78rem;">
                  Flags samples that appear to be a single cultured organism rather than a genuine mixed-community metagenome.
                </p>
                <p style="color: rgba(255,255,255,0.55); font-size: 0.75rem;">
                  Yes = sequencing of one cultured/isolated organism<br />
                  No = a genuine mixed-community metagenome
                </p>
              </template>
              <template v-if="active_tooltip === 'rna_or_non_dna_info'">
                <p class="info-tooltip-title">RNA/non-DNA</p>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.85); font-size: 0.78rem;">
                  Flags samples whose reads appear to be RNA (e.g. metatranscriptomic) or otherwise non-DNA sequencing, rather than standard DNA sequencing.
                </p>
                <p style="color: rgba(255,255,255,0.55); font-size: 0.75rem;">
                  Yes = RNA (e.g. metatranscriptomic) or other non-DNA sequencing<br />
                  No = standard DNA sequencing
                </p>
              </template>
              <template v-if="active_tooltip === 'metadata_info'">
                <p class="info-tooltip-title">Metadata <span class="tooltip-hint">(click to use)</span></p>
                <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.8); font-size: 0.78rem;">
                  Searches all free-form BioSample attributes submitted to NCBI — any extra metadata not covered by the structured fields above.
                </p>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.5); font-size: 0.72rem;">Two formats</p>
                <div class="info-tooltip-grid" style="margin-bottom: 0.5rem;">
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('metadata: Sus scrofa')">metadata: Sus scrofa — matches any attribute containing this value</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('metadata: host=Sus scrofa')">metadata: host=Sus scrofa — matches only the "host" attribute</button>
                </div>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.5); font-size: 0.72rem;">Example attributes</p>
                <div class="info-tooltip-grid">
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('host')">host</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('tissue')">tissue</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('disease')">disease</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('treatment')">treatment</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('isolation_source')">isolation_source</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('env_biome')">env_biome</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('body_site')">body_site</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('age')">age</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sex')">sex</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('phenotype')">phenotype</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('genotype')">genotype</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('strain')">strain</button>
                </div>
              </template>
              <template v-if="active_tooltip === 'metalog_info'">
                <p class="info-tooltip-title">Metalog metadata — click a field to select</p>
                <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.8); font-size: 0.78rem;">
                  Searches Metalog's curated/harmonised fields for this run (host, sex, age, diet,
                  environment, chemistry measurements, and more) -- distinct from "Metadata" above,
                  which searches the raw BioSample attributes as originally submitted to NCBI. Not
                  every run has a Metalog match; only a handful of these fields are populated for
                  any given sample.
                </p>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.5); font-size: 0.72rem;">Two formats</p>
                <div class="info-tooltip-grid" style="margin-bottom: 0.5rem;">
                  <span>metalog: diabetes — matches any field containing this value</span>
                  <span>metalog: host=Sus scrofa — matches only the "host" field</span>
                </div>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.5); font-size: 0.72rem;">All fields (200)</p>
                <div class="info-tooltip-grid metalog-fields-scroll">
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('acetate_um')">acetate_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('added_matter')">added_matter</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('age_category')">age_category</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('age_days')">age_days</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('age_months')">age_months</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('age_range')">age_range</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('age_years')">age_years</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('alkalinity')">alkalinity</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ammonium_mg_l')">ammonium_mg_l</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ammonium_um')">ammonium_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('amy1cn')">amy1cn</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('antibiotic')">antibiotic</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('antibiotic_dosage')">antibiotic_dosage</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('artificial')">artificial</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('available_info')">available_info</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('birth_country')">birth_country</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('birth_gestational_age_weeks')">birth_gestational_age_weeks</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('birth_mode')">birth_mode</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('birth_term_status')">birth_term_status</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('birth_weight_kg')">birth_weight_kg</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('blood_group')">blood_group</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('bmi')">bmi</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('bmi_range')">bmi_range</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('bristol_stool_scale')">bristol_stool_scale</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('butyrate_um')">butyrate_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('calcium_mg_l')">calcium_mg_l</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('captivity_status')">captivity_status</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('captivity_status_full')">captivity_status_full</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('carbon_dioxide_um')">carbon_dioxide_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('cause_of_death')">cause_of_death</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('chloride_mg_l')">chloride_mg_l</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('climatic_zone')">climatic_zone</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('cohort')">cohort</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('collection_date')">collection_date</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('collection_date_end')">collection_date_end</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('common_timepoint')">common_timepoint</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('comorbidities')">comorbidities</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('couple_id')">couple_id</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('couple_timepoint')">couple_timepoint</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('cultivation_condition')">cultivation_condition</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('cultivation_duration')">cultivation_duration</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('days_since_antibiotics')">days_since_antibiotics</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('days_since_fmt')">days_since_fmt</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('depth_meters')">depth_meters</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('description')">description</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('diet')">diet</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('diet_full')">diet_full</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('dissolved_organic_carbon_um')">dissolved_organic_carbon_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('dissolved_oxygen_um')">dissolved_oxygen_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('doi')">doi</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('dol_range')">dol_range</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('donor_d0')">donor_d0</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('donor_d28')">donor_d28</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('drug_antibiotic_last3y')">drug_antibiotic_last3y</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('elevation_meters')">elevation_meters</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('enriched_soil')">enriched_soil</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('environment_biome')">environment_biome</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('environment_feature')">environment_feature</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('environment_material')">environment_material</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('environmental_package')">environmental_package</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ethnicity')">ethnicity</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('family')">family</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ferric_iron_um')">ferric_iron_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ferrous_iron_um')">ferrous_iron_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ferrous_um')">ferrous_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('field_nominal_c')">field_nominal_c</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('filtration_lower_threshold')">filtration_lower_threshold</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('filtration_lower_threshold_kda')">filtration_lower_threshold_kda</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('filtration_lower_threshold_um')">filtration_lower_threshold_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('filtration_upper_threshold_um')">filtration_upper_threshold_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('fmt_donor')">fmt_donor</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('food_name')">food_name</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('formate_um')">formate_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('full_description')">full_description</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('geographic_location')">geographic_location</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('gestational_age_weeks')">gestational_age_weeks</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('gestational_state')">gestational_state</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('group')">group</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('height_cm')">height_cm</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('hip_cm')">hip_cm</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('host')">host</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('host_common_name')">host_common_name</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('host_scientific_name')">host_scientific_name</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('host_tax_id')">host_tax_id</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('host_tax_scientific_name')">host_tax_scientific_name</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('housing_lab')">housing_lab</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('hydrosulfide_um')">hydrosulfide_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('infant_id')">infant_id</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('intervention')">intervention</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('intervention_full')">intervention_full</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('iron_mg_l')">iron_mg_l</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('iron_um')">iron_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('isolation_source')">isolation_source</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('land_use_category')">land_use_category</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('land_use_full')">land_use_full</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('last_change')">last_change</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('latitude')">latitude</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('lifestyle')">lifestyle</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('linked_to')">linked_to</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('location')">location</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('location_name')">location_name</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('location_resolution')">location_resolution</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('longitude')">longitude</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('magnesium_mg_l')">magnesium_mg_l</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('manganese_um')">manganese_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('mean_annual_precipitation_mm')">mean_annual_precipitation_mm</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('mean_annual_temperature')">mean_annual_temperature</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('medical_history_notduringstudy')">medical_history_notduringstudy</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('medical_operation')">medical_operation</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('medication')">medication</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('medication_full')">medication_full</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('medication_with_parents')">medication_with_parents</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('medicinal_plant')">medicinal_plant</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('menopausal_status')">menopausal_status</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('methane_um')">methane_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('nitrate_mg_l')">nitrate_mg_l</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('nitrate_nitrite_um')">nitrate_nitrite_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('nitrate_um')">nitrate_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('nitrite_mg_l')">nitrite_mg_l</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('nitrite_um')">nitrite_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('nitrogen_dioxide_um')">nitrogen_dioxide_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('nitrogen_percent')">nitrogen_percent</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('note')">note</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('original_sample_name')">original_sample_name</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('original_timepoint')">original_timepoint</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('other_meds')">other_meds</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('oxygen_um')">oxygen_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ph')">ph</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ph_range')">ph_range</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('phenotypic_information')">phenotypic_information</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('phosphate_um')">phosphate_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('phosphorus_mg_l')">phosphorus_mg_l</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('phosphorus_um')">phosphorus_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('plant')">plant</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('pmid')">pmid</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('pooled_individuals')">pooled_individuals</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('potassium_mg_l')">potassium_mg_l</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('pregnancy_week')">pregnancy_week</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('pregnant')">pregnant</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('probiotic')">probiotic</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('propionate_um')">propionate_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('protocol_label')">protocol_label</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('provider')">provider</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('range_days_since_abxs')">range_days_since_abxs</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('range_days_since_antibiotics')">range_days_since_antibiotics</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('range_days_since_medication')">range_days_since_medication</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('recipient_donor')">recipient_donor</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('salinity')">salinity</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('salinity_ppm')">salinity_ppm</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('salinity_ppt')">salinity_ppt</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sample_alias')">sample_alias</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sample_collection_timepoint')">sample_collection_timepoint</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sample_description')">sample_description</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sample_title')">sample_title</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sampling_campaign')">sampling_campaign</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sampling_platform')">sampling_platform</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sampling_site')">sampling_site</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sampling_station')">sampling_station</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sex')">sex</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('silicate_um')">silicate_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('site_description')">site_description</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('skin_site_type')">skin_site_type</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('smoker')">smoker</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sodium_mg_l')">sodium_mg_l</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('specific_material')">specific_material</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('stool_consistency')">stool_consistency</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('strain')">strain</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('study_accession')">study_accession</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('study_code')">study_code</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('subject_disease_status')">subject_disease_status</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('subject_disease_status_full')">subject_disease_status_full</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('subject_id')">subject_id</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sulfate_mg_l')">sulfate_mg_l</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sulfate_um')">sulfate_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('sulfide_um')">sulfide_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('synbiotic')">synbiotic</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('tax_id')">tax_id</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('temperature')">temperature</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('temperature_range')">temperature_range</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('time_period')">time_period</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('timepoint')">timepoint</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('timepoint_note')">timepoint_note</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('timeseries_available')">timeseries_available</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('timeseries_count')">timeseries_count</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('timeseries_duration')">timeseries_duration</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('tissue_type')">tissue_type</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('total_dissolved_nitrogen_um')">total_dissolved_nitrogen_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('total_iron_um')">total_iron_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('total_manganese_um')">total_manganese_um</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('total_nitrate')">total_nitrate</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('total_organic_carbon')">total_organic_carbon</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('type_of_birth')">type_of_birth</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('vaccine_name')">vaccine_name</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('vaginal_ph')">vaginal_ph</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('vegetation')">vegetation</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('vegetation_full')">vegetation_full</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('village')">village</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('waist_cm')">waist_cm</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('water_depth_meters')">water_depth_meters</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('weight_kg')">weight_kg</button>
                </div>
              </template>
              <template v-if="active_tooltip === 'platform'">
                <p class="info-tooltip-title">Platform values — click to select</p>
                <div class="info-tooltip-grid">
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ILLUMINA')">ILLUMINA</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina')">Illumina</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Metagenomic')">Metagenomic</button>
                </div>
              </template>
              <template v-if="active_tooltip === 'instrument'">
                <p class="info-tooltip-title">Instrument values — click to select</p>
                <div class="info-tooltip-grid">
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina NovaSeq 6000')">Illumina NovaSeq 6000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 2500')">Illumina HiSeq 2500</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 4000')">Illumina HiSeq 4000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('NextSeq 500')">NextSeq 500</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 2000')">Illumina HiSeq 2000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina MiSeq')">Illumina MiSeq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('HiSeq X Ten')">HiSeq X Ten</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina NovaSeq X')">Illumina NovaSeq X</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('NextSeq 2000')">NextSeq 2000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('NextSeq 550')">NextSeq 550</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 3000')">Illumina HiSeq 3000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina NovaSeq X Plus')">Illumina NovaSeq X Plus</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq X')">Illumina HiSeq X</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 1000')">Illumina HiSeq 1000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 1500')">Illumina HiSeq 1500</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('NextSeq 1000')">NextSeq 1000</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina MiniSeq')">Illumina MiniSeq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina Genome Analyzer IIx')">Illumina Genome Analyzer IIx</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina Genome Analyzer II')">Illumina Genome Analyzer II</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina Genome Analyzer')">Illumina Genome Analyzer</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq X Ten')">Illumina HiSeq X Ten</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('HiSeq X Five')">HiSeq X Five</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina HiScanSQ')">Illumina HiScanSQ</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Illumina iSeq 100')">Illumina iSeq 100</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Nova seq')">Nova seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('MiSeq i100')">MiSeq i100</button>
                </div>
              </template>
              <template v-if="active_tooltip === 'metadata'">
                <p class="info-tooltip-title">Metadata</p>
                <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.8); font-size: 0.78rem;">
                  Searches all free-form BioSample attributes submitted to NCBI — any extra metadata not covered by the structured fields above.
                </p>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.5); font-size: 0.72rem;">Two formats</p>
                <div class="info-tooltip-grid" style="margin-bottom: 0.5rem;">
                  <span>metadata: Sus scrofa — matches any attribute containing this value</span>
                  <span>metadata: host=Sus scrofa — matches only the "host" attribute</span>
                </div>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.5); font-size: 0.72rem;">Example attributes</p>
                <div class="info-tooltip-grid">
                  <span>host</span><span>tissue</span><span>disease</span><span>treatment</span>
                  <span>isolation_source</span><span>env_biome</span><span>body_site</span><span>age</span>
                  <span>sex</span><span>phenotype</span><span>genotype</span><span>strain</span>
                </div>
              </template>
              <template v-if="active_tooltip === 'keys_info'">
                <p class="info-tooltip-title">Search syntax</p>
                <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.85); font-size: 0.78rem;">
                  Filter runs using <strong style="color:#fff">key: value</strong> pairs, separated by commas.
                </p>
                <div class="info-tooltip-grid" style="margin-bottom: 0.5rem;">
                  <span>country: Australia</span>
                  <span>year: 2010-2015</span>
                  <span>gbp: 2-10</span>
                  <span>environment: ecological</span>
                  <span>taxonomy: s__Prochlorococcus</span>
                  <span>metadata: host=Sus scrofa</span>
                </div>
                <p style="color: rgba(255,255,255,0.45); font-size: 0.72rem;">Click "List of Keys" to expand all available keys.</p>
              </template>
              <template v-if="active_tooltip === 'library'">
                <p class="info-tooltip-title">Library strategy values — click to select</p>
                <div class="info-tooltip-grid">
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('WGS')">WGS</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('OTHER')">OTHER</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('AMPLICON')">AMPLICON</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('WGA')">WGA</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('RNA-Seq')">RNA-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Targeted-Capture')">Targeted-Capture</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('POOLCLONE')">POOLCLONE</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('WXS')">WXS</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('WCS')">WCS</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Hi-C')">Hi-C</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('CLONE')">CLONE</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ChIP-Seq')">ChIP-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Bisulfite-Seq')">Bisulfite-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Synthetic-Long-Read')">Synthetic-Long-Read</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('RAD-Seq')">RAD-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ATAC-seq')">ATAC-seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('CLONEEND')">CLONEEND</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Tn-Seq')">Tn-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('shotgun sequencing')">shotgun sequencing</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('FAIRE-seq')">FAIRE-seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('miRNA-Seq')">miRNA-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('FL-cDNA')">FL-cDNA</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('DNase-Hypersensitivity')">DNase-Hypersensitivity</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('CTS')">CTS</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('MRE-Seq')">MRE-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('FINISHING')">FINISHING</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ssRNA-seq')">ssRNA-seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('EST')">EST</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('GBS')">GBS</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('RIP-Seq')">RIP-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('ncRNA-Seq')">ncRNA-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Ribo-seq')">Ribo-seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('Tethered Chromatin Conformation Capture')">Tethered Chromatin Conformation Capture</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('NOMe-Seq')">NOMe-Seq</button>
                  <button type="button" class="tt-clickable" @click="selectTooltipValue('MBD-Seq')">MBD-Seq</button>
                </div>
              </template>
            </div>
          </teleport>

          <section class="adv-group" :class="{ 'is-open': adv_groups.taxonomy }">
            <button type="button" class="adv-group-toggle" :aria-expanded="adv_groups.taxonomy" aria-controls="adv-group-taxonomy" @click="toggle_adv_group('taxonomy')">
              <span class="adv-group-title">Taxonomy</span>
              <span class="adv-group-chevron" aria-hidden="true"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></span>
              <span class="adv-group-hint">{{ adv_group_hint('taxonomy') }}</span>
            </button>
            <div class="adv-group-collapse"
              :class="{ 'is-open': adv_groups.taxonomy, 'is-settled': adv_group_settled.taxonomy }"
              :inert="!adv_groups.taxonomy">
              <div id="adv-group-taxonomy" class="adv-group-body">
                <b-field grouped group-multiline class="adv-group-row">
                  <PresenceField class="adv-field" label="Organism" v-model="adv.organism" v-model:present="adv_present.organism" placeholder="e.g. marine metagenome" search-field="organism">
                    <template #label-suffix>
                      <InfoTooltipButton controls="advanced-search-popover" label="Show organism search help" :expanded="active_tooltip === 'organism_info'" @open="showTooltip('organism_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" />
                    </template>
                  </PresenceField>
                  <PresenceField class="adv-field" label="Taxonomy" v-model="adv.taxonomy" placeholder="e.g. s__Prochlorococcus" search-field="taxonomy" :allow-any="false" />
                </b-field>
              </div>
            </div>
          </section>

          <section class="adv-group" :class="{ 'is-open': adv_groups.study }">
            <button type="button" class="adv-group-toggle" :aria-expanded="adv_groups.study" aria-controls="adv-group-study" @click="toggle_adv_group('study')">
              <span class="adv-group-title">Study</span>
              <span class="adv-group-chevron" aria-hidden="true"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></span>
              <span class="adv-group-hint">{{ adv_group_hint('study') }}</span>
            </button>
            <div class="adv-group-collapse"
              :class="{ 'is-open': adv_groups.study, 'is-settled': adv_group_settled.study }"
              :inert="!adv_groups.study">
              <div id="adv-group-study" class="adv-group-body">
                <b-field grouped group-multiline class="adv-group-row">
                  <PresenceField class="adv-field" label="Study title" v-model="adv.study" v-model:present="adv_present.study" placeholder="e.g. Tara Oceans" search-field="study" />
                  <PresenceField class="adv-field" label="Abstract" v-model="adv.abstract" v-model:present="adv_present.abstract" placeholder="e.g. coral reef" />
                  <PresenceField class="adv-field" label="BioProject" v-model="adv.bioproject" placeholder="e.g. PRJNA12345" search-field="bioproject" :allow-any="false" />
                </b-field>
              </div>
            </div>
          </section>

          <section class="adv-group" :class="{ 'is-open': adv_groups.identifiers }">
            <button type="button" class="adv-group-toggle" :aria-expanded="adv_groups.identifiers" aria-controls="adv-group-identifiers" @click="toggle_adv_group('identifiers')">
              <span class="adv-group-title">Identifiers</span>
              <span class="adv-group-chevron" aria-hidden="true"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></span>
              <span class="adv-group-hint">{{ adv_group_hint('identifiers') }}</span>
            </button>
            <div class="adv-group-collapse"
              :class="{ 'is-open': adv_groups.identifiers, 'is-settled': adv_group_settled.identifiers }"
              :inert="!adv_groups.identifiers">
              <div id="adv-group-identifiers" class="adv-group-body">
                <b-field grouped group-multiline class="adv-group-row">
                  <b-field label="SRA study" label-for="adv-sra-study" label-position="on-border" class="adv-field">
                    <b-input id="adv-sra-study" :compat-fallthrough="false" v-model="adv.sra_study" placeholder="e.g. SRP012345" size="is-small"></b-input>
                  </b-field>
                  <b-field label="Experiment" label-for="adv-experiment" label-position="on-border" class="adv-field">
                    <b-input id="adv-experiment" :compat-fallthrough="false" v-model="adv.experiment" placeholder="e.g. SRX012345" size="is-small"></b-input>
                  </b-field>
                  <b-field label="Sample accession" label-for="adv-sample-acc" label-position="on-border" class="adv-field">
                    <b-input id="adv-sample-acc" :compat-fallthrough="false" v-model="adv.sample_acc" placeholder="e.g. SRS012345" size="is-small"></b-input>
                  </b-field>
                  <b-field label="BioSample" label-for="adv-biosample" label-position="on-border" class="adv-field">
                    <b-input id="adv-biosample" :compat-fallthrough="false" v-model="adv.biosample" placeholder="e.g. SAMN12345" size="is-small"></b-input>
                  </b-field>
                </b-field>
              </div>
            </div>
          </section>

          <section class="adv-group" :class="{ 'is-open': adv_groups.submitter }">
            <button type="button" class="adv-group-toggle" :aria-expanded="adv_groups.submitter" aria-controls="adv-group-submitter" @click="toggle_adv_group('submitter')">
              <span class="adv-group-title">Submitter</span>
              <span class="adv-group-chevron" aria-hidden="true"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></span>
              <span class="adv-group-hint">{{ adv_group_hint('submitter') }}</span>
            </button>
            <div class="adv-group-collapse"
              :class="{ 'is-open': adv_groups.submitter, 'is-settled': adv_group_settled.submitter }"
              :inert="!adv_groups.submitter">
              <div id="adv-group-submitter" class="adv-group-body">
                <b-field grouped group-multiline class="adv-group-row">
                  <PresenceField class="adv-field" label="Organisation" v-model="adv.organisation" v-model:present="adv_present.organisation" placeholder="e.g. MIT or Woods Hole" search-field="organisation" />
                </b-field>
              </div>
            </div>
          </section>

          <section class="adv-group" :class="{ 'is-open': adv_groups.metadata }">
            <button type="button" class="adv-group-toggle" :aria-expanded="adv_groups.metadata" aria-controls="adv-group-metadata" @click="toggle_adv_group('metadata')">
              <span class="adv-group-title">Metadata</span>
              <span class="adv-group-chevron" aria-hidden="true"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg></span>
              <span class="adv-group-hint">{{ adv_group_hint('metadata') }}</span>
            </button>
            <div class="adv-group-collapse"
              :class="{ 'is-open': adv_groups.metadata, 'is-settled': adv_group_settled.metadata }"
              :inert="!adv_groups.metadata">
              <div id="adv-group-metadata" class="adv-group-body">
                <b-field grouped group-multiline class="adv-group-row">
                  <b-field label-for="adv-attr" label-position="on-border" class="adv-field">
                    <template #label>
                      Metadata
                      <InfoTooltipButton controls="advanced-search-popover" label="Show BioSample metadata search help" :expanded="active_tooltip === 'metadata'" @open="showTooltip('metadata', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" />
                    </template>
                    <b-input id="adv-attr" :compat-fallthrough="false" v-model="adv.attr" placeholder="e.g. sex=male or age=1-2" size="is-small"></b-input>
                  </b-field>
                  <PresenceField class="adv-field" label="Metalog metadata" v-model="adv.metalog" v-model:present="adv_present.metalog" placeholder="e.g. host=Sus scrofa or diabetes">
                    <template #label-suffix>
                      <InfoTooltipButton controls="advanced-search-popover" label="Show Metalog metadata search help" :expanded="active_tooltip === 'metalog_info'" @open="showTooltip('metalog_info', $event)" @close-delayed="hideTooltipDelayed" @close="hideTooltip" />
                    </template>
                  </PresenceField>
                </b-field>
              </div>
            </div>
          </section>

        </div>
        </div>
      </div>

      <div v-if="universal_result" ref="universalResult" tabindex="-1" class="mt-4" aria-live="polite" aria-atomic="true">
        <b-message v-if="universal_result.count === 0" type="is-warning" has-icon>
          No samples found matching {{ universal_result.match_description }}.
        </b-message>
        <b-message v-else type="is-info" has-icon>
          <strong>{{ universal_result.count.toLocaleString() }}</strong> samples match {{ universal_result.match_description }}.
          <br />
          <div class="buttons mt-2">
            <b-button ref="exploreRandomButton" type="is-primary is-small" @click="explore_random_universal">{{ universal_result.count === 1 ? 'Explore the run' : 'Explore a random filtered run' }}</b-button>
            <b-button type="is-primary is-small" outlined @click="explore_tabled_universal">Explore tabled results</b-button>
          </div>
        </b-message>
      </div>
    </section>

    <section class="section">
      <p class="title is-4">Find a random run</p>
      <div class="random-run-box">
        <div class="random-run-grid">
          <div class="random-run-option"><b-switch v-model="random_choice_host" name="random-choice-host">Eukaryote host-associated</b-switch></div>
          <div class="random-run-option"><b-switch v-model="random_choice_ecological" name="random-choice-ecological">Ecological</b-switch></div>
          <div class="random-run-option"><b-switch v-model="random_choice_two_gbp" name="random-choice-two-gbp">2+ Gbp</b-switch></div>
          <div class="random-run-option"><b-switch v-model="random_choice_non_human_host" name="random-choice-non-human-host">Non-human host only</b-switch></div>
          <div class="random-run-option"><b-switch v-model="random_exclude_strict_low_complexity" name="random-exclude-strict-low-complexity">Exclude low complexity (≥95% one order)</b-switch></div>
        </div>
      </div>
      <br /><b-button type="is-primary" @click="search_by_random">Search</b-button>
    </section>

  </section>
</template>

<script>
import { fetchTaxonomySearchHints, fetchSandpiperStats, fetchUniversalSearch, fetchSearchFieldValues } from '@/api'
import { GTDB_VERSION, GLOBDB_VERSION } from '@/versions'
import { RANDOM_DEFAULTS } from '@/constants/randomRun'
import { ADVANCED_KEY_MAP, ADVANCED_GROUP_FIELDS, SEARCH_FIELDS } from '@/constants/searchFields'
import { useSearchAutocomplete, splitActiveSegment, splitQueryParts, quoteQueryValue, unquoteQueryValue } from '@/composables/useSearchAutocomplete'
import { stopPageLoading } from '@/store/pageLoading'
import debounce from 'lodash/debounce'
import InfoTooltipButton from '@/components/InfoTooltipButton.vue'
import PresenceField from '@/components/PresenceField.vue'
import SearchGridField from '@/components/SearchGridField.vue'

// Blurbs for the Keywords group. Plain prose: the search syntax itself lives in the List of keys.
const KEYWORDS_NOTE = 'Search a study\'s title, abstract, location, organism and accessions at once. Separate terms with commas: each term is matched as an exact phrase and every term must be found. A sample that matches in several places still counts once.'

const ADVANCED_KEY_RE = new RegExp(`^(${Object.keys(ADVANCED_KEY_MAP).join('|')})\\s*:`, 'i')

function queryParamToString (value) {
  if (Array.isArray(value)) {
    return value.filter(part => typeof part === 'string' && part.length > 0).join(', ')
  }
  return typeof value === 'string' ? value : ''
}

export default {
  name: 'Search',
  title: 'Search - Sandpiper',
  components: { InfoTooltipButton, PresenceField, SearchGridField },
  setup () {
    const autocomplete = useSearchAutocomplete(async (field, q, signal) => {
      if (field === 'taxonomy') {
        const { data } = await fetchTaxonomySearchHints(q, undefined, signal)
        return (data.taxonomies || []).map(name => ({ value: name, count: null }))
      }
      const { data } = await fetchSearchFieldValues(field, q, signal)
      return data.values
    }, () => SEARCH_FIELDS)
    // Returned as flat top-level refs (not nested inside one `autocomplete`
    // object) so Vue's Options API interop auto-unwraps them -- both in the
    // template and via `this.ac_suggestions` etc. in methods below, with no
    // `.value` needed either place.
    return {
      ac_suggestions: autocomplete.suggestions,
      ac_active_index: autocomplete.activeIndex,
      ac_on_input: autocomplete.onInput,
      ac_cycle_next: autocomplete.cycleNext,
      ac_apply_suggestion: autocomplete.applySuggestion,
      ac_clear: autocomplete.clear,
    }
  },
  data () {
    return {
      GTDB_VERSION,
      GLOBDB_VERSION,
      KEYWORDS_NOTE,
      gtdb_version: null,

      universal_query: '',
      universal_loading: false,
      universal_result: null,
      // The abortable preview request.
      preview_abort: null,
      universal_request_id: 0,
      debounced_universal_preview: null,
      syncing_query_to_advanced: false,
      query_generated_from_advanced: false,
      advanced_passthrough_parts: [],
      advanced_primary_state: {},
      advanced_dirty_fields: {},

      keys_open: false,
      advanced_open: false,
      // Each Advanced-options group collapses independently and starts closed
      // so the panel opens compact rather than as a wall of ~35 inputs.
      // The Keywords group is the exception: it is the main way in, so it starts open.
      adv_groups: {
        ...Object.fromEntries(Object.keys(ADVANCED_GROUP_FIELDS).map(name => [name, false])),
        keywords: true,
      },
      // True once a group's open transition has finished -- see
      // .adv-group-collapse.is-settled in the CSS for why this matters:
      // grid's own row-height estimate for a *wrapping* flex row can be
      // undersized (a Buefy quirk), so once open we drop out of grid sizing
      // back to plain block flow, which is never wrong. Cleared the instant
      // a group starts closing so it re-enters grid mode to animate shut.
      adv_group_settled: {
        ...Object.fromEntries(Object.keys(ADVANCED_GROUP_FIELDS).map(name => [name, false])),
        keywords: true,
      },
      advanced_settled: false,
      keys_settled: false,
      adv: {
        // Keywords
        keywords: '',
        // Location
        country: '', continent: '', location: '', latitude: '', longitude: '', grid: '',
        // Sample
        year: '', release_year: '', temperature: '', depth: '', environment: '', low_complexity: '',
        synthetic: '', non_metagenome_organism: '', rna_or_non_dna: '',
        // Quality / size
        spf: '', ksf: '', gbp: '', reads: '', read_length: '',
        // Sequencing
        platform: '', instrument: '', library_strategy: '',
        // Taxonomy
        organism: '', taxonomy: '',
        // Study
        study: '', abstract: '', bioproject: '',
        // Identifiers
        sra_study: '', experiment: '', sample_acc: '', biosample: '',
        // Submitter
        organisation: '',
        // Age
        age: '',
        // BioSample attributes
        attr: '',
        // Metalog (curated/harmonised) metadata
        metalog: '',
        // IndicPiper habitat indicator
        habitat: '',
      },
      // Per-field "present, any value" toggle -- mirrors the keys of `adv`
      // that support it. When true for a field, build_query() sends "key: "
      // (empty value) instead of the text input's value, which the backend
      // reads as "field is populated" rather than a specific match. Useful
      // for sparsely-populated fields like age, temperature, or depth where
      // asking the user for an exact value isn't practical.
      adv_present: {
        country: false, continent: false, location: false, latitude: false, longitude: false,
        year: false, release_year: false, temperature: false, depth: false, age: false,
        environment: false, low_complexity: false,
        synthetic: false, non_metagenome_organism: false, rna_or_non_dna: false,
        spf: false, ksf: false, gbp: false, reads: false, read_length: false,
        platform: false, instrument: false, library_strategy: false,
        organism: false, taxonomy: false,
        study: false, abstract: false, bioproject: false,
        sra_study: false, experiment: false, sample_acc: false, biosample: false,
        organisation: false,
        attr: false, metalog: false,
        habitat: false,
      },
      adv_errors: {},
      adv_error_timers: {},
      active_tooltip: null,
      tooltip_trigger: null,
      tooltip_x: 0,
      tooltip_y: 0,
      tooltip_close_timer: null,

      taxonomy: 'c__Bog-38',
      autocomplete_taxons: [],
      selected: null,
      isFetching: false,
      accession: 'ERR1914274',

      random_choice_host: RANDOM_DEFAULTS.host,
      random_choice_non_human_host: RANDOM_DEFAULTS.non_human_host,
      random_choice_ecological: RANDOM_DEFAULTS.ecological,
      random_choice_two_gbp: RANDOM_DEFAULTS.two_gbp,
      random_exclude_strict_low_complexity: RANDOM_DEFAULTS.exclude_strict_low_complexity
    }
  },

  created () {
    // The template has no data gate -- the search form renders immediately.
    stopPageLoading()
    // Vue binds functions declared in `methods`, which drops Lodash's custom
    // `.cancel()` property. Keep the debouncer as per-instance state instead.
    this.debounced_universal_preview = debounce(this.fetch_universal_preview, 450)
    if (this.$route.query.q) {
      // e.g. "Edit search" on the search results page: keep the query in the
      // search bar and show its match count (and buttons) again.
      this.universal_query = queryParamToString(this.$route.query.q)
      this.parse_query_to_advanced()
      this.refresh_universal_state()
    }
    this.fetchData()
  },

  mounted () {
    // Ghost-text overlay needs to sit pixel-for-pixel over the real input's
    // text (padding/font/line-height), which is Buefy/Bulma's to define, not
    // ours -- copy the rendered input's computed style instead of guessing
    // Bulma's padding constants by hand, so it stays correct across Buefy
    // versions or theme tweaks.
    this.sync_ghost_overlay_style()
  },

  beforeUnmount () {
    this.universal_request_id += 1
    this.debounced_universal_preview.cancel()
    for (const timer of Object.values(this.adv_error_timers)) clearTimeout(timer)
    clearTimeout(this.tooltip_close_timer)
  },

  watch: {
    '$route.query.q': 'on_route_query_change',
    // The overlay is v-if'd (only exists in the DOM while a suggestion is
    // showing), so its computed-style copy has to be redone each time it's
    // freshly inserted, not just once in mounted().
    ghost_suffix (value) {
      if (value) this.$nextTick(this.sync_ghost_overlay_style)
    },
    adv: {
      deep: true,
      handler: 'on_advanced_change',
    },
    adv_present: {
      deep: true,
      handler: 'on_advanced_change',
    },
    // Ensure that at least one of host/ecological is on
    random_choice_host: function() {
      if (!this.random_choice_host) {
        this.random_choice_ecological = true
      }
    },
    random_choice_ecological: function() {
      if (!this.random_choice_ecological) {
        this.random_choice_host = true
      }
    }
  },

  computed: {
    // Only rendered when the active suggestion's underlying value actually
    // starts with what's typed (case-insensitive) -- the dropdown itself
    // allows substring matches (e.g. typing "seq" can suggest "Illumina
    // NovaSeq 6000"), but grey inline completion only makes visual sense as
    // a literal continuation of what's already on screen.
    ghost_suffix () {
      const s = this.ac_suggestions[this.ac_active_index]
      if (!s) return ''
      const target = s.kind === 'key' ? s.insertKey : s.insertValue
      if (!target) return ''
      const el = document.getElementById('advanced-search-query')
      const caret = el ? el.selectionStart : this.universal_query.length
      const seg = splitActiveSegment(this.universal_query, caret)
      if (!target.toLowerCase().startsWith(seg.value.toLowerCase())) return ''
      return target.slice(seg.value.length)
    },
  },

  methods: {
    // Pieces shared by the preview, Enter and "Explore" paths.
    fetch_matches (query, exclude, signal) {
      return fetchUniversalSearch(query, exclude, signal)
    },

    // Start a new match request, dropping the one it replaces: a query the user
    // has already typed past is not worth waiting on.
    fetch_matches_latest (query) {
      this.preview_abort?.abort()
      this.preview_abort = new AbortController()
      return this.fetch_matches(query, undefined, this.preview_abort.signal)
    },

    async current_preview_or_fetch (query) {
      const preview = this.current_preview(query)
      return preview ? { data: preview } : this.fetch_matches_latest(query)
    },

    // The preview result on screen, if it answers exactly this query -- so
    // Enter does not repeat the request the preview just made.
    current_preview (query) {
      const result = this.universal_result
      return result && result.query === query ? result : null
    },

    run_route (accession, query) {
      return { name: 'Run', params: { accession }, query: query ? { q: query } : undefined }
    },

    search_route_query (query) {
      return { q: query }
    },

    sync_advanced_from_query () {
      this.parse_query_to_advanced()
    },

    // Grid-row collapse (see the CSS comment above .adv-group-collapse) is
    // only trusted for the ~300ms it's actually mid-transition -- past that,
    // `is-settled` drops the group back to plain block layout for its real,
    // always-correct height. A fixed timeout matching the CSS duration
    // (rather than a `transitionend` listener) so this still resolves under
    // prefers-reduced-motion, where the CSS sets `transition: none` and
    // transitionend would otherwise never fire at all.
    settle_after (durationMs, isStillOpen, applySettled) {
      setTimeout(() => {
        if (isStillOpen()) applySettled()
      }, durationMs)
    },
    toggle_advanced () {
      if (!this.advanced_open) this.sync_advanced_from_query()
      this.advanced_open = !this.advanced_open
      this.advanced_settled = false
      if (this.advanced_open) {
        this.settle_after(370, () => this.advanced_open, () => { this.advanced_settled = true })
      }
    },

    toggle_keys () {
      this.keys_open = !this.keys_open
      this.keys_settled = false
      if (this.keys_open) {
        this.settle_after(370, () => this.keys_open, () => { this.keys_settled = true })
      }
    },

    toggle_adv_group (name) {
      const opening = !this.adv_groups[name]
      this.adv_groups = { ...this.adv_groups, [name]: opening }
      this.adv_group_settled = { ...this.adv_group_settled, [name]: false }
      if (opening) {
        this.settle_after(320, () => this.adv_groups[name], () => {
          this.adv_group_settled = { ...this.adv_group_settled, [name]: true }
        })
      }
    },

    adv_group_active_count (name) {
      return ADVANCED_GROUP_FIELDS[name].filter(
        field => this.adv_present[field] || (this.adv[field] || '').trim()
      ).length
    },

    adv_group_hint (name) {
      if (this.adv_groups[name]) return ''
      const count = this.adv_group_active_count(name)
      return count ? `${count} set` : 'expand for keys'
    },

    expand_adv_groups (fields) {
      const wanted = new Set(fields)
      const opened = Object.fromEntries(
        Object.entries(ADVANCED_GROUP_FIELDS)
          .filter(([, group_fields]) => group_fields.some(field => wanted.has(field)))
          .map(([name]) => [name, true])
      )
      this.adv_groups = { ...this.adv_groups, ...opened }
    },

    expand_adv_groups_with_values () {
      this.expand_adv_groups(
        Object.keys(this.adv).filter(
          field => this.adv_present[field] || (this.adv[field] || '').trim()
        )
      )
    },
    showTooltip (name, event) {
      clearTimeout(this.tooltip_close_timer)
      const trigger = event.currentTarget || event.target
      this.tooltip_trigger = trigger
      const rect = trigger.getBoundingClientRect()
      const tooltipW = 420
      // .info-tooltip-box caps at max-height: 80vh (see CSS) and scrolls
      // internally past that, so the metalog tooltip -- by far the tallest,
      // with 200 fields -- can never actually be taller than 80vh. Use that
      // as its height estimate instead of a fixed guess, otherwise an
      // undershoot here still lets the fixed-position box get placed too low
      // and run off the bottom of the viewport even though it isn't really
      // that tall.
      const tooltipH = {
        instrument_info: 420,
        library_info: 480,
        metadata_info: 360,
        platform_info: 100,
        organism_info: 150,
        taxonomy_info: 220,
        metadata: 360,
        age_info: 180,
        grid_info: 260,
        low_complexity_info: 150,
        synthetic_info: 150,
        non_metagenome_organism_info: 150,
        rna_or_non_dna_info: 150,
        metalog_info: Math.round(window.innerHeight * 0.8),
      }[name] ?? 300

      // Horizontal: prefer right of icon, flip left if it would overflow
      let x = rect.right + 10
      if (x + tooltipW > window.innerWidth - 10) {
        x = rect.left - tooltipW - 10
      }
      // Clamp to viewport left edge
      x = Math.max(10, x)

      // Vertical: align to icon top, shift up if it would overflow bottom
      let y = rect.top
      if (y + tooltipH > window.innerHeight - 10) {
        y = window.innerHeight - tooltipH - 10
      }
      // Clamp to viewport top edge
      y = Math.max(10, y)

      this.tooltip_x = x
      this.tooltip_y = y
      this.active_tooltip = name
      if (event.type === 'click' && event.detail === 0) {
        this.$nextTick(() => {
          document.querySelector('#advanced-search-popover .tt-clickable')?.focus()
        })
      }
    },
    hideTooltipDelayed () {
      clearTimeout(this.tooltip_close_timer)
      this.tooltip_close_timer = setTimeout(() => {
        this.active_tooltip = null
      }, 250)
    },
    keepTooltipOpen () {
      clearTimeout(this.tooltip_close_timer)
    },
    hideTooltip (event) {
      clearTimeout(this.tooltip_close_timer)
      if (event?.type === 'keydown') this.tooltip_trigger?.focus()
      this.active_tooltip = null
    },
    selectTooltipValue (value) {
      // "List of keys" value-list tooltips (platform_info/instrument_info/
      // library_info/habitat_info) list every real database value. Clicking
      // one appends "key: value" to the query bar itself, rather than
      // setting an Advanced-options field -- those are the separate
      // 'platform'/'instrument'/'library' tooltips handled below.
      const keysListField = {
        platform_info: 'platform',
        instrument_info: 'instrument',
        library_info: 'library_strategy',
        habitat_info: 'habitat',
        metadata_info: 'metadata',
      }[this.active_tooltip]
      if (keysListField) {
        // metadata_info mixes two kinds of buttons: full "key: value" example
        // snippets (already query-ready, used verbatim) and bare attribute
        // names (e.g. "host") that need "=" appended so the cursor lands
        // ready for a value. Other keysListField entries are always bare
        // enum values (e.g. "ILLUMINA") and never need the "=" suffix.
        let part
        if (value.includes(':')) part = value
        else if (this.active_tooltip === 'metadata_info') part = `${keysListField}: ${value}=`
        else part = `${keysListField}: ${value}`
        const existing = this.universal_query.trim()
        this.universal_query = existing ? `${existing}, ${part}` : part
        this.on_universal_input()
        clearTimeout(this.tooltip_close_timer)
        this.active_tooltip = null
        this.$nextTick(() => document.getElementById('advanced-search-query')?.focus())
        return
      }
      if (this.active_tooltip === 'platform') {
        this.adv_present.platform = false
        this.adv.platform = value
      } else if (this.active_tooltip === 'instrument') {
        this.adv_present.instrument = false
        this.adv.instrument = value
      } else if (this.active_tooltip === 'library') {
        this.adv_present.library_strategy = false
        this.adv.library_strategy = value
      } else if (this.active_tooltip === 'metadata') {
        // The alphabetical BioSample attribute-name picker (Advanced options'
        // "Metadata" field) had no branch here at all -- clicking any of its
        // ~150 buttons silently closed the tooltip and did nothing.
        this.adv_present.attr = false
        this.adv.attr = `${value}=`
      } else if (this.active_tooltip === 'metalog_info') {
        this.adv_present.metalog = false
        this.adv.metalog = `${value}=`
      }
      clearTimeout(this.tooltip_close_timer)
      this.tooltip_trigger?.focus()
      this.active_tooltip = null
    },

    fetchData () {
      fetchSandpiperStats()
        .then(response => {
          const r = response.data
          this.gtdb_version = r.gtdb_version
        })
    },
    build_query () {
      const parts = []
      // Keep only genuine free-text segments (not key:value pairs) from the current search bar
      const freetext_parts = splitQueryParts(this.universal_query)
        .filter(p => !ADVANCED_KEY_RE.test(p))
      parts.push(...freetext_parts)
      // The form has one control per key, while expert queries may repeat a
      // key to express AND conditions. Keep every extra clause verbatim so
      // editing an unrelated field cannot silently weaken the query.
      parts.push(...this.advanced_passthrough_parts
        .filter(({ field }) => !this.advanced_dirty_fields[field])
        .map(({ part }) => part))
      const text_fields = [
        ['keywords', this.adv.keywords],
        ['country', this.adv.country], ['continent', this.adv.continent],
        ['location', this.adv.location], ['latitude', this.adv.latitude], ['longitude', this.adv.longitude],
        ['grid', this.adv.grid],
        ['year', this.adv.year], ['release_year', this.adv.release_year],
        ['temperature', this.adv.temperature], ['depth', this.adv.depth],
        ['spf', this.adv.spf], ['ksf', this.adv.ksf],
        ['gbp', this.adv.gbp], ['reads', this.adv.reads], ['read_length', this.adv.read_length],
        ['platform', this.adv.platform], ['instrument', this.adv.instrument],
        ['library_strategy', this.adv.library_strategy],
        ['organism', this.adv.organism], ['taxonomy', this.adv.taxonomy],
        ['study', this.adv.study], ['abstract', this.adv.abstract], ['bioproject', this.adv.bioproject],
        ['sra_study', this.adv.sra_study], ['experiment', this.adv.experiment],
        ['sample_acc', this.adv.sample_acc], ['biosample', this.adv.biosample],
        ['organisation', this.adv.organisation],
        ['age', this.adv.age],
        ['metadata', this.adv.attr, 'attr'],
        ['metalog', this.adv.metalog],
        ['habitat', this.adv.habitat],
      ]
      for (const [key, val, stateKey = key] of text_fields) {
        // A "present" toggle always wins over the input's value -- pushing
        // "key: " (empty) tells the backend to match any populated value.
        if (this.adv_present[stateKey]) parts.push(`${key}: `)
        else if (val && val.trim()) parts.push(`${key}: ${quoteQueryValue(val.trim())}`)
      }
      if (this.adv_present.environment) parts.push('environment: ')
      else if (this.adv.environment) parts.push(`environment: ${this.adv.environment}`)
      if (this.adv_present.low_complexity) parts.push('low_complexity: ')
      else if (this.adv.low_complexity) parts.push(`low_complexity: ${this.adv.low_complexity}`)
      if (this.adv_present.synthetic) parts.push('synthetic: ')
      else if (this.adv.synthetic) parts.push(`synthetic: ${this.adv.synthetic}`)
      if (this.adv_present.non_metagenome_organism) parts.push('non_metagenome_organism: ')
      else if (this.adv.non_metagenome_organism) parts.push(`non_metagenome_organism: ${this.adv.non_metagenome_organism}`)
      if (this.adv_present.rna_or_non_dna) parts.push('rna_or_non_dna: ')
      else if (this.adv.rna_or_non_dna) parts.push(`rna_or_non_dna: ${this.adv.rna_or_non_dna}`)
      return parts.join(', ')
    },

    on_adv_field_input (field) {
      // Clear error immediately when user edits the field
      const { [field]: _, ...rest } = this.adv_errors
      this.adv_errors = rest
      // Cancel any existing timer for this field
      if (this.adv_error_timers[field]) {
        clearTimeout(this.adv_error_timers[field])
      }
      // Show error after 3 seconds of inactivity if still invalid
      const range_re = /^-?\d+(\.\d+)?(-(-?\d+(\.\d+)?))?$/
      const op_re = /^[<>]=?-?\d+(\.\d+)?$/
      this.adv_error_timers[field] = setTimeout(() => {
        if (this.adv_present[field]) return
        const val = (this.adv[field] || '').trim()
        if (val && !range_re.test(val) && !op_re.test(val)) {
          this.adv_errors = { ...this.adv_errors, [field]: 'Use a number, range e.g. 10-20, or operator e.g. >10' }
        }
      }, 3000)
    },

    validate_advanced () {
      this.adv_errors = this.advanced_validation_errors()
      return Object.keys(this.adv_errors).length === 0
    },

    advanced_validation_errors () {
      const errors = {}
      const range_re = /^-?\d+(\.\d+)?(-(-?\d+(\.\d+)?))?$/
      const op_re = /^[<>]=?-?\d+(\.\d+)?$/
      for (const field of ['year', 'release_year', 'temperature', 'depth', 'latitude', 'longitude', 'spf', 'ksf', 'gbp', 'reads', 'read_length', 'age']) {
        if (this.adv_present[field]) continue
        const val = (this.adv[field] || '').trim()
        if (val && !range_re.test(val) && !op_re.test(val)) {
          errors[field] = 'Use a number, range e.g. 10-20, or operator e.g. >10'
        }
      }
      return errors
    },

    parse_query_to_advanced () {
      this.syncing_query_to_advanced = true
      this.advanced_passthrough_parts = []
      this.advanced_dirty_fields = {}
      this.adv_errors = {}
      for (const timer of Object.values(this.adv_error_timers)) clearTimeout(timer)
      this.adv_error_timers = {}
      for (const key of Object.keys(this.adv)) this.adv[key] = ''
      for (const key of Object.keys(this.adv_present)) this.adv_present[key] = false

      const seen = new Set()
      for (const part of splitQueryParts(this.universal_query)) {
        const m = part.match(/^([\w\s]+?):\s*(.*)$/)
        if (m) {
          const adv_key = ADVANCED_KEY_MAP[m[1].toLowerCase().trim()]
          if (adv_key) {
            if (seen.has(adv_key)) {
              this.advanced_passthrough_parts.push({ field: adv_key, part })
              continue
            }
            seen.add(adv_key)
            const value = unquoteQueryValue(m[2])
            if (!value && Object.prototype.hasOwnProperty.call(this.adv_present, adv_key)) {
              this.adv_present[adv_key] = true
            } else {
              this.adv[adv_key] = value
            }
          }
        }
      }
      this.advanced_primary_state = Object.fromEntries(
        Object.keys(this.adv).map(field => [field, {
          value: this.adv[field],
          present: this.adv_present[field]
        }])
      )
      // A collapsed group must never hide a filter that is already in play.
      this.expand_adv_groups_with_values()
      // Keep the expert query exactly as entered. The fields mirror it; opening
      // Advanced options must never silently change what will be submitted.
      this.$nextTick(() => { this.syncing_query_to_advanced = false })
    },

    on_route_query_change (value) {
      const query = queryParamToString(value)
      if (query === this.universal_query) return
      const requestId = ++this.universal_request_id
      this.debounced_universal_preview.cancel()
      this.universal_loading = false
      this.universal_result = null
      this.query_generated_from_advanced = false
      this.universal_query = query
      this.sync_advanced_from_query()
      if (query.trim()) this.debounced_universal_preview(requestId)
    },

    on_universal_input () {
      this.refresh_universal_state()
      const el = document.getElementById('advanced-search-query')
      this.ac_on_input(this.universal_query, el ? el.selectionStart : this.universal_query.length)
    },

    // Advanced-options sync + result preview, split out of on_universal_input
    // so apply_universal_suggestion (below) can run it WITHOUT also
    // recomputing autocomplete suggestions. Recomputing them right after an
    // accept was the actual bug: a just-accepted value like "Australia: NSW"
    // still satisfies the live-suggestion trigger (length >= 2) and matches
    // itself when re-queried, so the dropdown never emptied out -- every
    // following Enter press kept re-"accepting" the same already-complete
    // value (harmless on its own, but see apply_universal_suggestion) instead
    // of ever falling through to search_universal()'s actual search.
    refresh_universal_state () {
      const requestId = ++this.universal_request_id
      this.universal_loading = false
      this.universal_result = null
      this.query_generated_from_advanced = false
      this.sync_advanced_from_query()
      if (!this.universal_query.trim()) {
        this.debounced_universal_preview.cancel()
        this.universal_result = null
        return
      }
      this.debounced_universal_preview(requestId)
    },

    // Tab cycles the ghost-text candidate instead of moving focus, but only
    // while a suggestion is actually showing -- otherwise Tab keeps its
    // normal browser behavior (move to the next focusable element).
    // Enter accepts the active suggestion when one is showing (first Enter
    // completes the word, matching a search-bar-with-suggestions pattern the
    // user is likely already used to); with no suggestion open it runs the
    // search and scrolls to the match count and the two "Explore" buttons
    // (search_universal -> reveal_universal_result), so the user picks between
    // a random run and the tabled results instead of being sent to a run.
    // Right-arrow accepts too, but only with the caret at the very end of
    // the input, so it doesn't hijack normal cursor movement mid-string.
    on_universal_keydown (event) {
      if (event.key === 'Tab') {
        if (this.ac_suggestions.length === 0) return
        event.preventDefault()
        this.ac_cycle_next()
        return
      }
      if (event.key === 'Enter') {
        if (this.ac_suggestions.length > 0) {
          event.preventDefault()
          this.accept_active_suggestion(event.target)
          return
        }
        this.search_universal()
        return
      }
      if (event.key === 'ArrowRight') {
        const el = event.target
        const atEnd = el.selectionStart === el.value.length && el.selectionStart === el.selectionEnd
        if (atEnd && this.ac_suggestions.length > 0) {
          event.preventDefault()
          this.accept_active_suggestion(el)
        }
        return
      }
      if (event.key === 'Escape') {
        this.ac_clear()
      }
    },

    accept_active_suggestion (inputEl) {
      const s = this.ac_suggestions[this.ac_active_index]
      if (!s) return
      this.apply_universal_suggestion(s, inputEl)
    },

    on_universal_click_suggestion (s) {
      this.apply_universal_suggestion(s, document.getElementById('advanced-search-query'))
    },

    apply_universal_suggestion (s, inputEl) {
      const caret = inputEl ? inputEl.selectionStart : this.universal_query.length
      const { text, caret: newCaret } = this.ac_apply_suggestion(this.universal_query, caret, s)
      this.universal_query = text
      this.refresh_universal_state()
      // Close the dropdown -- see refresh_universal_state's comment. If the
      // user keeps typing after this, the normal @input handler
      // (on_universal_input) recomputes suggestions fresh, which is exactly
      // what should happen; this only suppresses the immediate, spurious
      // "reopens because the just-picked value matches itself" recompute.
      this.ac_clear()
      this.$nextTick(() => {
        if (!inputEl) return
        inputEl.setSelectionRange(newCaret, newCaret)
        inputEl.focus()
      })
    },

    // Copies the real input's computed padding/font/line-height onto the
    // ghost-text overlay so the invisible "typed" span lines up character
    // for character with what Buefy/Bulma actually render -- more robust
    // than hand-copying Bulma's padding constants, which can shift between
    // versions or theme overrides.
    sync_ghost_overlay_style () {
      const wrap = this.$el.querySelector('.search-autocomplete-wrap')
      const input = wrap && wrap.querySelector('input#advanced-search-query')
      if (!wrap || !input) return
      const cs = window.getComputedStyle(input)
      const props = ['fontFamily', 'fontSize', 'fontWeight', 'letterSpacing', 'lineHeight', 'padding', 'border', 'boxSizing']
      const overlay = wrap.querySelector('.search-ghost-overlay')
      if (!overlay) return // not rendered yet -- the ghost_suffix watcher re-runs this once it is
      for (const prop of props) overlay.style[prop] = cs[prop]
    },

    on_advanced_change () {
      if (this.syncing_query_to_advanced) return
      for (const [field, present] of Object.entries(this.adv_present)) {
        if (!present) continue
        if (this.adv_error_timers[field]) {
          clearTimeout(this.adv_error_timers[field])
          delete this.adv_error_timers[field]
        }
        if (this.adv_errors[field]) {
          const { [field]: _, ...rest } = this.adv_errors
          this.adv_errors = rest
        }
      }
      // These fields do not expose an "Any" button. If a presence-only query
      // populated hidden state and the user now types a value, the value must
      // replace that hidden state rather than being silently ignored.
      for (const key of ['continent', 'taxonomy', 'bioproject', 'sra_study', 'experiment', 'sample_acc', 'biosample', 'attr', 'metalog']) {
        if (this.adv_present[key] && (this.adv[key] || '').trim()) this.adv_present[key] = false
      }
      const dirtyFields = { ...this.advanced_dirty_fields }
      for (const [field, baseline] of Object.entries(this.advanced_primary_state)) {
        if (this.adv[field] !== baseline.value || this.adv_present[field] !== baseline.present) {
          dirtyFields[field] = true
        }
      }
      this.advanced_dirty_fields = dirtyFields
      this.query_generated_from_advanced = true
      this.universal_query = this.build_query()
      const requestId = ++this.universal_request_id
      this.universal_loading = false
      this.universal_result = null
      if (!this.universal_query.trim()) {
        this.debounced_universal_preview.cancel()
        this.universal_result = null
        return
      }
      if (Object.keys(this.advanced_validation_errors()).length > 0) {
        this.debounced_universal_preview.cancel()
        this.universal_result = null
        return
      }
      this.debounced_universal_preview(requestId)
    },

    try_universal_example () {
      this.universal_query = 'year: 2015-2020, metadata: sex=male'
      this.query_generated_from_advanced = false
      this.universal_result = null
      this.parse_query_to_advanced()
      this.search_universal()
    },

    // Squares picked on the map set only the grid key: each square carries its
    // own sample type and bounds, so Latitude, Longitude are left alone. A
    // single Environment choice would be ANDed with every square (wrongly
    // excluding the other type), so picking squares clears it.
    on_grid_change ({ grid }) {
      this.adv.grid = grid
      if (grid) {
        this.adv.environment = ''
        this.adv_present.environment = false
      }
    },

    toggle_env (val) {
      const next = this.adv.environment === val ? '' : val
      this.adv.environment = next
      if (next) this.adv_present.environment = false
    },

    toggle_environment_present () {
      this.adv_present.environment = !this.adv_present.environment
      if (this.adv_present.environment) this.adv.environment = ''
    },

    toggle_low_complexity (val) {
      const next = this.adv.low_complexity === val ? '' : val
      this.adv.low_complexity = next
      if (next) this.adv_present.low_complexity = false
    },

    toggle_low_complexity_present () {
      this.adv_present.low_complexity = !this.adv_present.low_complexity
      if (this.adv_present.low_complexity) this.adv.low_complexity = ''
    },

    toggle_synthetic (val) {
      const next = this.adv.synthetic === val ? '' : val
      this.adv.synthetic = next
      if (next) this.adv_present.synthetic = false
    },

    toggle_synthetic_present () {
      this.adv_present.synthetic = !this.adv_present.synthetic
      if (this.adv_present.synthetic) this.adv.synthetic = ''
    },

    toggle_non_metagenome_organism (val) {
      const next = this.adv.non_metagenome_organism === val ? '' : val
      this.adv.non_metagenome_organism = next
      if (next) this.adv_present.non_metagenome_organism = false
    },

    toggle_non_metagenome_organism_present () {
      this.adv_present.non_metagenome_organism = !this.adv_present.non_metagenome_organism
      if (this.adv_present.non_metagenome_organism) this.adv.non_metagenome_organism = ''
    },

    toggle_rna_or_non_dna (val) {
      const next = this.adv.rna_or_non_dna === val ? '' : val
      this.adv.rna_or_non_dna = next
      if (next) this.adv_present.rna_or_non_dna = false
    },

    toggle_rna_or_non_dna_present () {
      this.adv_present.rna_or_non_dna = !this.adv_present.rna_or_non_dna
      if (this.adv_present.rna_or_non_dna) this.adv.rna_or_non_dna = ''
    },

    async search_universal () {
      if (this.query_generated_from_advanced && !this.validate_advanced()) {
        this.advanced_open = true
        this.expand_adv_groups(Object.keys(this.adv_errors))
        return
      }
      const query = this.universal_query.trim()
      if (!query) {
        this.universal_request_id += 1
        this.debounced_universal_preview.cancel()
        this.universal_result = null
        this.universal_loading = false
        return
      }
      this.universal_query = query
      const requestId = ++this.universal_request_id
      this.debounced_universal_preview.cancel()
      if (this.$route.query.q !== query) {
        const savedY = window.scrollY
        this.$router.replace({ query: this.search_route_query(query) })
        this.$nextTick(() => window.scrollTo(0, savedY))
      }
      this.universal_loading = true
      try {
        const { data } = await this.current_preview_or_fetch(query)
        if (requestId !== this.universal_request_id) return
        this.universal_result = data
        if (data.count === 1 && data.random_acc) {
          this.$router.push(this.run_route(data.random_acc, query))
        } else {
          this.reveal_universal_result()
        }
      } catch (e) {
        if (requestId !== this.universal_request_id) return
        this.universal_result = { count: 0, match_description: 'search error' }
        this.reveal_universal_result()
      } finally {
        if (requestId === this.universal_request_id) this.universal_loading = false
      }
    },

    fetch_universal_preview (requestId) {
      if (requestId !== this.universal_request_id) return
      const query = this.universal_query.trim()
      if (!query) { this.universal_result = null; return }
      this.universal_loading = true
      this.fetch_matches_latest(query)
        .then(({ data }) => {
          if (requestId !== this.universal_request_id) return
          this.universal_result = data
        })
        .catch(() => {
          if (requestId !== this.universal_request_id) return
          this.universal_result = { count: 0, match_description: 'search error' }
        })
        .finally(() => {
          if (requestId === this.universal_request_id) this.universal_loading = false
        })
    },

    // Bring the match count and the "Explore" buttons into view and move
    // keyboard focus there: to the first button when there are matches (so
    // Enter again opens a random run), otherwise to the message itself.
    reveal_universal_result () {
      this.$nextTick(() => {
        const block = this.$refs.universalResult
        if (!block) return
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
        block.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'center' })
        const button = this.$refs.exploreRandomButton
        const target = this.universal_result?.count > 0 && button ? (button.$el || button) : block
        target.focus({ preventScroll: true })
      })
    },

    explore_random_universal () {
      if (this.universal_result && this.universal_result.random_acc) {
        const query = this.universal_query.trim()
        this.$router.push(this.run_route(this.universal_result.random_acc, query))
      }
    },

    explore_tabled_universal () {
      // The query that produced the count on screen, not the textbox, which
      // may have been edited since (the preview is debounced).
      const query = this.universal_result && this.universal_result.query
      if (!query) return
      this.$router.push({ name: 'QueryResults', query: { q: query } })
    },

    search_by_taxonomy () {
      this.$router.push({ name: 'SearchResults', params: { taxonomy: this.taxonomy } })
    },
    getAsyncData: debounce(function (name) {
      // if undefined or empty, reset the list
      if (name === undefined || name === null || !name.length) {
        this.autocomplete_taxons = []
        return
      }
      this.isFetching = true
      fetchTaxonomySearchHints(name).then(({ data }) => data.taxonomies)
        .then((taxa) => {
          this.autocomplete_taxons = taxa
          if (this.autocomplete_taxons != undefined && this.autocomplete_taxons.length >= 30) {
            this.autocomplete_taxons.push('.. possibly more')
          }
        })
        .catch((error) => {
          this.autocomplete_taxons = []
          throw error
        })
        .finally(() => {
          this.isFetching = false
        })
    }, 500),

    search_by_accession() {
      const uppercaseAccession = this.accession.toUpperCase();
      this.$router.push({ name: 'Accession', params: { accession: uppercaseAccession } });
    },

    search_by_random () {
      this.$router.push({ name: 'RunRandom', query: {
        host: this.random_choice_host,
        non_human_host: this.random_choice_non_human_host,
        ecological: this.random_choice_ecological,
        two_gbp: this.random_choice_two_gbp,
        exclude_strict_low_complexity: this.random_exclude_strict_low_complexity
      }})
    }
  }
}
</script>

<style>
.keys-columns code {
  color: hsl(271, 100%, 71%);
}
.info-tooltip-box {
  position: fixed;
  z-index: var(--z-tooltip);
  background: rgba(25, 25, 35, 0.97);
  color: #fff;
  border-radius: 8px;
  padding: 0.8rem 1rem;
  min-width: 280px;
  max-width: 420px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.5);
  font-size: 0.78rem;
  line-height: 1.5;
  pointer-events: auto;
}
/* metalog_info is far taller than every other tooltip (200 fields), so it
   alone gets a flex layout: header text (title/description/examples) keeps
   its natural height and stays fully visible, while .metalog-fields-scroll
   below it flexes to fill whatever's left of the box's 80vh cap and scrolls
   on its own -- the box itself no longer needs to scroll as a whole. */
.info-tooltip-box.is-scroll-list {
  display: flex;
  flex-direction: column;
  overflow-y: hidden;
}
.metalog-fields-scroll {
  flex: 1 1 auto;
  overflow-y: auto;
  min-height: 0;
  padding-right: 0.3rem;
}
.tt-clickable {
  appearance: none;
  border: 0;
  background: rgba(255, 255, 255, 0.12);
  color: inherit;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font: inherit;
  font-size: 0.75rem;
  line-height: inherit;
  text-align: left;
  white-space: nowrap;
  cursor: pointer;
}
.tt-clickable:hover,
.tt-clickable:focus-visible {
  background: rgba(255, 255, 255, 0.28) !important;
  color: #fff;
}
.tt-clickable:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 1px;
}
/* Buefy's <b-field grouped group-multiline> renders the actual flex-wrap
   row (the one that needs the vertical gap between wrapped rows) on a
   SECOND, internal nested b-field one level below the element our own
   class/style lands on (see Field.vue: grouped+group-multiline sets
   hasInnerField, which wraps the real slot content in
   .field-body > b-field.is-grouped-multiline). A plain `style="row-gap"`
   on the outer <b-field> tag has no visible effect -- that outer element
   only ever has one child (.field-body), so there's nothing for it to
   space apart; the actual wrapping happens one level deeper, outside
   what an inline style on the outer tag can reach. Targeting the real
   inner flex container directly via CSS descendant selector instead.
   Every group wrapper in the advanced panel (Location, Sample, Quality/
   Size, Sequencing, Taxonomy, Study, Identifiers, Submitter, Metadata)
   carries .adv-group-row so this applies uniformly -- needed for every
   group now, not just Sample, since uniform .adv-field widths mean more
   groups wrap onto multiple rows, and on narrow/phone widths nearly every
   group wraps. Scoped to the specific .adv-group-row class (not a bare
   .advanced-panel descendant selector) deliberately: an earlier attempt
   using a bare `.advanced-panel :deep(.field-body > .field.is-grouped-
   multiline)` selector matched more than intended and broke spacing that
   was already correct elsewhere. */
.adv-group-row > .field-body > .field.is-grouped-multiline {
  row-gap: 0.75rem;
}
/* Bulma puts margin-bottom: 0.75rem on a multiline group's `.control`
   children and cancels the last row's with margin-bottom: -0.75rem on the
   group itself. These rows hold `.field` children spaced by the row-gap
   above, so nothing ever compensates -- every group row reported 12px less
   height than it drew, and the last row spilled outside the group box. */
.adv-group-row > .field-body > .field.is-grouped-multiline:last-child {
  margin-bottom: 0;
}
/* Same trick, same problem, one level down: Bulma gives each `.button` in a
   `.buttons` group a 0.5rem bottom margin and cancels the last row's with
   -0.5rem on the group. These addon groups (Environment, Low complexity) are
   always a single row, so the pair just leaves the group 8px shorter than the
   buttons it contains. Drop both. */
.adv-group-row .buttons.has-addons,
.adv-group-row .buttons.has-addons .button {
  margin-bottom: 0;
}
@media (max-width: 768px) {
  .info-tooltip-box {
    left: 10px !important;
    top: 10px !important;
    width: calc(100vw - 20px);
    min-width: 0;
    max-width: none;
    max-height: calc(100dvh - 20px);
  }
  .info-tooltip-grid span,
  .info-tooltip-grid button {
    max-width: 100%;
    white-space: normal;
    overflow-wrap: anywhere;
  }
}
</style>

<style scoped>
/* Deliberately is-light + is-small, not is-primary -- easy to reach without
   scrolling, but a secondary action next to the actual search input, not
   competing with it for attention. */
.advanced-search-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3);
}
.random-search-button {
  flex-shrink: 0;
}

/* Ghost-text autocomplete overlay + suggestion dropdown for the universal
   search bar. The overlay's own font/padding is copied at runtime from the
   real input (see sync_ghost_overlay_style) since it has to line up exactly
   with Buefy/Bulma's rendering, not whatever this stylesheet guesses. */
.search-autocomplete-wrap {
  position: relative;
}
.search-ghost-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  white-space: pre;
  overflow: hidden;
}
.search-ghost-typed {
  visibility: hidden;
}
.search-ghost-suffix {
  color: rgba(60, 60, 60, 0.45);
}
.search-suggest-dropdown {
  position: absolute;
  left: 0;
  right: auto;
  /* As wide as the longest suggestion (never narrower than the input), so
     values aren't cut off; anything past the cap wraps instead. */
  min-width: 100%;
  width: max-content;
  max-width: min(40rem, calc(100vw - 2rem));
  top: 100%;
  margin-top: 0.25rem;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  max-height: 280px;
  overflow-y: auto;
  z-index: 30;
  list-style: none;
  padding: 0.25rem 0;
  margin-left: 0;
}
.search-suggest-dropdown li {
  padding: 0.4rem 0.75rem;
  font-size: 0.9rem;
  cursor: pointer;
  white-space: normal;
  overflow-wrap: anywhere;
}
.search-suggest-dropdown li.is-active,
.search-suggest-dropdown li:hover {
  background: rgba(50, 115, 220, 0.1);
}
/* Query syntax / example rows: a plain separated row by default (used
   inline inside .adv-box, which already has its own padding), upgraded to
   a tinted footer strip when it's the last thing inside .keys-box -- that
   box clips to its own border-radius via overflow:hidden, so the tint
   naturally picks up rounded bottom corners for free. */
.keys-syntax-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0 var(--space-1);
  border-top: 1px solid var(--color-accent-rule);
  margin-top: var(--space-3);
}
.keys-box .keys-syntax-row {
  padding: var(--space-2) var(--space-4);
  margin-top: var(--space-1);
}
.keys-syntax-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--color-accent);
  white-space: nowrap;
}
.keys-syntax-items {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 0.75rem;
}
.keys-syntax-item {
  font-size: 0.72rem;
  color: #666;
  white-space: nowrap;
}
.keys-syntax-item code {
  color: var(--color-accent);
  font-weight: 600;
  margin-right: 0.2rem;
}
.keys-example-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) 0 0;
}
.keys-box .keys-example-row {
  padding: var(--space-1) 0 var(--space-3);
}
.keys-example-label {
  font-size: 0.75rem;
  color: #666;
  white-space: nowrap;
}
.keys-example-query {
  font-size: 0.72rem;
  color: #444;
  flex: 1;
}

/* "List of keys" sits inline in the help sentence -- a minimal text link,
   deliberately not styled like the standalone "Advanced options" pill below
   (see .disclosure-toggle) since it isn't a section-level control. */
.inline-toggle {
  appearance: none;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  border: 0;
  background: transparent;
  padding: 0;
  margin-left: 0.3rem;
  color: var(--color-accent);
  font: inherit;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  border-bottom: 1px solid transparent;
  transition: border-color 220ms var(--ease-spring), color 220ms var(--ease-spring);
}
.inline-toggle:hover {
  border-bottom-color: currentColor;
}
.inline-toggle:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: 2px;
}
.inline-toggle .disclosure-chevron {
  transform: translateY(1px);
}
.inline-toggle.is-open .disclosure-chevron {
  transform: translateY(1px) rotate(180deg);
}

/* "Advanced options" -- plain text + chevron, same minimal language as the
   inline "List of keys" link, just standalone on its own line rather than
   sitting inside a sentence. No pill/button chrome. */
.disclosure-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
.disclosure-row-standalone {
  margin-top: var(--space-4);
}
.disclosure-toggle {
  appearance: none;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 0;
  border-bottom: 1px solid transparent;
  background: transparent;
  color: var(--color-accent-strong);
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  padding: 0.6rem 0;
  min-height: 44px;
  cursor: pointer;
  transition: border-color 220ms var(--ease-spring), color 220ms var(--ease-spring);
}
.disclosure-toggle:hover {
  border-bottom-color: currentColor;
}
.disclosure-toggle:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: 2px;
}
.disclosure-chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 300ms var(--ease-spring);
}
.disclosure-toggle.is-open .disclosure-chevron {
  transform: rotate(180deg);
}
.advanced-panel {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.35s var(--ease-spring);
}
.advanced-panel.is-open {
  grid-template-rows: 1fr;
}
.advanced-panel.is-settled {
  display: block;
}
/* .advanced-panel-clip (not .advanced-panel itself) carries the padding-free
   overflow:hidden -- .adv-box's own padding stays put and just gets clipped
   inside it, same reasoning as .adv-group-row above. */
.advanced-panel:not(.is-settled) > .advanced-panel-clip {
  min-height: 0;
  overflow: hidden;
}
.adv-box {
  padding: var(--space-2) 0 0;
  margin-top: var(--space-2);
}
/* Each group inside the advanced panel is its own disclosure: the whole
   header row is the hit target, and the bottom rule that used to sit under
   the bare title now runs the full row width so a closed group still reads
   as a section divider. */
.adv-group {
  margin-top: var(--space-3);
}
.adv-group:first-child {
  margin-top: 0;
}
.adv-group-toggle {
  appearance: none;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  width: 100%;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--color-accent-rule);
  padding: var(--space-1) 0;
  margin-bottom: 0;
  text-align: left;
  cursor: pointer;
  transition: border-color 220ms var(--ease-spring);
}
.adv-group-toggle:hover {
  border-bottom-color: var(--color-accent);
}
.adv-group-toggle:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: 2px;
}
.adv-group-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--color-accent-strong);
}
/* Search box row. */
.search-bar-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.search-bar-row > .search-autocomplete-wrap {
  flex: 1 1 18rem;
  min-width: 0;
}
.adv-group-chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-accent);
  transition: transform 300ms var(--ease-spring);
}
.adv-group.is-open .adv-group-toggle {
  margin-bottom: var(--space-2);
}
.adv-group.is-open .adv-group-chevron {
  transform: rotate(180deg);
}
.adv-group-hint {
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.01em;
  color: var(--color-ink-muted);
}
/* Grid-row collapse for the *animation* only. A grid row's own auto/fr
   sizing measures the body's intrinsic (max-content) height, which is the
   same measurement that undercounts .adv-group-row's wrapped multiline
   fields (see the row-gap/negative-margin comment above .adv-group-row) --
   good enough not to be visually wrong for the ~300ms it's on screen mid-
   transition, but not something to trust as the *settled* height. Once
   `is-settled` lands (a fixed timeout after opening, see settle_after), the
   group drops out of grid sizing back to plain block flow, whose real
   layout is never wrong. `:inert` keeps a closed group's inputs out of the
   tab order and away from AT. */
.adv-group-collapse {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 300ms var(--ease-spring);
}
.adv-group-collapse.is-open {
  grid-template-rows: 1fr;
}
.adv-group-collapse.is-settled {
  display: block;
}
/* Padding lives on .adv-group-row (the body's sole child), not on the
   clipped .adv-group-body itself -- padding is unconditional box-model
   space that overflow:hidden/min-height:0 can never zero out, so keeping it
   on the clip target left a permanent sliver visible even at 0fr. */
.adv-group-collapse:not(.is-settled) > .adv-group-body {
  overflow: hidden;
  min-height: 0;
}
.adv-group-note {
  margin: 0 0 0.75rem;
  max-width: 62ch;
  font-size: 0.8rem;
  line-height: 1.5;
  color: var(--color-ink-muted);
}
.adv-group-row {
  /* Headroom for the `on-border` floating labels, which straddle each input's
     top edge, and for focus rings while the group is clipped mid-animation. */
  padding: 0.55rem 3px 0.25rem;
}
.info-icon-btn {
  cursor: help;
  color: #aaa;
  font-size: 0.85rem;
  margin-left: 0.3rem;
  align-self: center;
  user-select: none;
}
.info-icon-btn:hover {
  color: #555;
}
.info-tooltip-title {
  font-weight: 700;
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 0.5rem;
}
.tooltip-hint {
  font-weight: 400;
  color: rgba(255, 255, 255, 0.35);
}
.info-tooltip-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
.info-tooltip-grid span,
.info-tooltip-grid .tt-clickable {
  background: rgba(255, 255, 255, 0.12);
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-size: 0.75rem;
  white-space: nowrap;
}
.info-tooltip-grid .tt-clickable {
  appearance: none;
  border: 0;
  color: inherit;
  font: inherit;
  font-size: 0.75rem;
  line-height: inherit;
  text-align: left;
}
.keys-panel {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.35s var(--ease-spring);
}
.keys-panel.is-open {
  grid-template-rows: 1fr;
}
.keys-panel.is-settled {
  display: block;
}
.keys-panel:not(.is-settled) > .keys-box {
  min-height: 0;
  overflow: hidden;
}
.keys-box {
  margin-top: var(--space-2);
  overflow: hidden;
}
.keys-columns {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4) var(--space-6);
  padding: var(--space-3) 0 var(--space-2);
}
.keys-group {
  min-width: 150px;
  flex: 1;
}
.keys-group-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--color-accent-strong);
  border-bottom: 1px solid var(--color-accent-rule);
  padding-bottom: var(--space-1);
  margin-bottom: var(--space-2);
}
.keys-item {
  font-size: 0.78rem;
  margin-bottom: 0.15rem;
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
}
/* Same grid/spacing structure as .keys-box/.keys-columns above -- each
   toggle gets its own grid cell so they distribute evenly and reflow
   automatically (multiple per row on wide screens, one-per-row once a row
   can no longer fit two 220px-minimum cells, in practice phone widths) --
   but no visible card chrome (no background/border) so it reads as part of
   the page rather than a boxed widget. */
.random-run-box {
  padding: var(--space-3);
}
.random-run-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-2);
}
.random-run-option {
  padding: var(--space-0);
  display: flex;
  align-items: center;
  min-height: 44px;
}
.keys-item-label {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
}
.keys-example {
  color: #a3a3a3;
  font-size: 0.75rem;
  padding-left: 0.25rem;
}
/* Low complexity used to sit alone at the end of its row (width: 100%,
   margin-top: 0.65rem to nudge it into place) -- now paired with IndicPiper
   habitat in .low-complexity-habitat-group instead. Both of those old rules
   are superseded by the uniform .adv-field sizing below; only the
   bottom-alignment for this specific pair remains here (label heights
   differ slightly between a 3-button row and a text-input + button row). */
.low-complexity-habitat-group {
  align-items: flex-end;
}

/* Every field in the advanced-options panel gets this class (see the
   template) so they all render as identical-sized boxes regardless of
   content -- a PresenceField (input + Any button), a plain b-input with no
   Any button, and Environment/Low complexity's button row all end up the
   same width, so the whole panel reads as a neat grid instead of each
   field being exactly as wide as its own content. min-width/max-width
   pinned to the same value as flex-basis so nothing can grow or shrink
   away from it. */
.advanced-panel :deep(.adv-field) {
  flex: 0 0 260px;
  min-width: 260px;
  max-width: 260px;
}
@media (max-width: 600px) {
  .advanced-panel :deep(.adv-field) {
    flex-basis: 100%;
    min-width: 0;
    max-width: 100%;
  }
}
/* The Keywords bar is the one long field: it takes a whole row of its group. */
.advanced-panel :deep(.adv-field.adv-field-keywords) {
  flex: 1 1 100%;
  min-width: 0;
  max-width: none;
}

@media (max-width: 768px) {
  section.section.container {
    padding: 1rem;
  }
  section.section.container > .section {
    padding: 1.5rem 0;
  }
  .advanced-search-section :deep(.field),
  .advanced-search-section :deep(.field-body),
  .advanced-search-section :deep(.control) {
    min-width: 0;
    max-width: 100%;
  }
  .advanced-panel :deep(.field-body > .field.is-grouped),
  .advanced-panel :deep(.field-body > .field.is-grouped-multiline) {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    width: 100%;
    gap: 0.75rem;
  }
  .advanced-panel :deep(.field.is-grouped > .control),
  .advanced-panel :deep(.field.is-grouped-multiline > .control),
  .advanced-panel :deep(.field-body > .field) {
    width: 100%;
    margin-right: 0;
  }
  .advanced-panel :deep(.field.is-floating-label > .label) {
    position: static;
    display: flex;
    align-items: center;
    gap: 0.25rem;
    max-width: 100%;
    margin-bottom: 0.35rem;
    padding: 0;
    overflow: visible;
    white-space: normal;
    text-overflow: clip;
    font-size: 0.875rem;
  }
  .advanced-panel :deep(.field.is-floating-label > .label::before) {
    display: none;
  }
  .advanced-panel :deep(.input.is-small) {
    height: 44px;
    font-size: 16px;
  }
  .advanced-panel.is-open > .advanced-panel-clip,
  .keys-panel.is-open > .keys-box {
    overflow: visible;
  }
  .adv-group-toggle {
    min-height: 44px;
  }
  .adv-box {
    padding: var(--space-3);
  }
  .keys-columns {
    gap: 1rem;
    padding: var(--space-4) var(--space-4) var(--space-2);
  }
  .keys-group {
    flex: 1 1 calc(50% - 0.5rem);
    min-width: 0;
  }
  .keys-syntax-row,
  .keys-example-row {
    align-items: flex-start;
    flex-direction: column;
  }
  .keys-box .keys-syntax-row,
  .keys-box .keys-example-row {
    padding-left: var(--space-4);
    padding-right: var(--space-4);
  }
  .keys-example-query {
    width: 100%;
    overflow-wrap: anywhere;
  }
  .info-tooltip-grid span,
  .info-tooltip-grid .tt-clickable {
    max-width: 100%;
    white-space: normal;
    overflow-wrap: anywhere;
  }
  .info-tooltip-grid .tt-clickable {
    min-height: 44px;
    padding: 0.5rem 0.65rem;
  }
  .advanced-search-section :deep(.button) {
    min-height: 44px;
  }
}

@media (max-width: 430px) {
  .keys-group {
    flex-basis: 100%;
  }
  .keys-syntax-item {
    white-space: normal;
  }
}

@media (prefers-reduced-motion: reduce) {
  .advanced-panel,
  .keys-panel,
  .adv-group-collapse,
  .adv-group-chevron {
    transition: none;
  }
}

.adv-group-subtitle {
  margin-left: 0.5rem;
  font-size: 0.8em;
  font-weight: 400;
  opacity: 0.5;          /* the slight see-through look */
  text-transform: none;  /* only needed if .adv-group-title is uppercase */
  letter-spacing: normal;
}

</style>
