<template>
  <section class="section container">

    <section class="section" @keyup.enter="search_universal">
      <p class="title is-4">Advanced search</p>
      <b-field>
        <b-input v-model="universal_query" placeholder="e.g. country: Australia, year: 2010-2015" icon="magnify" expanded @input="search_universal_debounced"></b-input>
      </b-field>
      <p class="help">
        Key: value, comma-separated for multiple (e.g. "country: Australia, year: 2020").
        <a class="keys-toggle" @click="keys_open = !keys_open">List of Keys</a>
        <b-icon icon="information-outline" size="is-small" class="info-icon-btn" @mouseenter="showTooltip('keys_info', $event)" @mouseleave="hideTooltipDelayed" />
      </p>

      <div class="keys-panel" :class="{ 'is-open': keys_open }">
        <div class="box mt-2 keys-box">
          <div class="keys-columns">

            <div class="keys-group">
              <p class="keys-group-title">Location</p>
              <div class="keys-item"><code>country</code><span class="keys-example">e.g. Australia</span></div>
              <div class="keys-item"><code>location</code><span class="keys-example">e.g. Pacific Ocean</span></div>
              <div class="keys-item"><code>latitude</code><span class="keys-example">e.g. -33.8 or -40-30</span></div>
              <div class="keys-item"><code>longitude</code><span class="keys-example">e.g. 151.2 or 140-160</span></div>
            </div>

            <div class="keys-group">
              <p class="keys-group-title">Sample</p>
              <div class="keys-item"><code>year</code><span class="keys-example">e.g. 2010 or 2010-2015</span></div>
              <div class="keys-item"><code>release_year</code><span class="keys-example">e.g. 2018 or 2015-2020</span></div>
              <div class="keys-item"><code>temperature</code><span class="keys-example">e.g. 25 or 20-30</span></div>
              <div class="keys-item"><code>depth</code><span class="keys-example">e.g. 100 or 0-200</span></div>
              <div class="keys-item"><code>environment</code><span class="keys-example">host or ecological</span></div>
              <div class="keys-item"><code>low_complexity</code><span class="keys-example">yes or no</span></div>
              <div class="keys-item">
                <code class="keys-item-label">age <b-icon icon="information-outline" size="is-small" class="info-icon-btn" @mouseenter="showTooltip('age_info', $event)" @mouseleave="hideTooltipDelayed" /></code>
                <span class="keys-example">e.g. 25 or 20-30</span>
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
                <code class="keys-item-label">platform <b-icon icon="information-outline" size="is-small" class="info-icon-btn" @mouseenter="showTooltip('platform_info', $event)" @mouseleave="hideTooltipDelayed" /></code>
                <span class="keys-example">e.g. Illumina</span>
              </div>
              <div class="keys-item">
                <code class="keys-item-label">instrument <b-icon icon="information-outline" size="is-small" class="info-icon-btn" @mouseenter="showTooltip('instrument_info', $event)" @mouseleave="hideTooltipDelayed" /></code>
                <span class="keys-example">e.g. HiSeq 2500</span>
              </div>
              <div class="keys-item">
                <code class="keys-item-label">library_strategy <b-icon icon="information-outline" size="is-small" class="info-icon-btn" @mouseenter="showTooltip('library_info', $event)" @mouseleave="hideTooltipDelayed" /></code>
                <span class="keys-example">e.g. WGS</span>
              </div>
              <p class="keys-group-title" style="margin-top: 1rem;">Taxonomy</p>
              <div class="keys-item"><code>organism</code><span class="keys-example">e.g. marine metagenome</span></div>
              <div class="keys-item">
                <code class="keys-item-label">taxonomy <b-icon icon="information-outline" size="is-small" class="info-icon-btn" @mouseenter="showTooltip('taxonomy_info', $event)" @mouseleave="hideTooltipDelayed" /></code>
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
                <code class="keys-item-label">metadata <b-icon icon="information-outline" size="is-small" class="info-icon-btn" @mouseenter="showTooltip('metadata_info', $event)" @mouseleave="hideTooltipDelayed" /></code>
                <span class="keys-example">e.g. sex=male or body_site=arm</span>
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
            </div>
          </div>
          <div class="keys-example-row">
            <span class="keys-example-label">Example:</span>
            <code class="keys-example-query">year: 2015-2020, metadata: sex=male</code>
            <b-button size="is-small" type="is-primary" @click="universal_query = 'year: 2015-2020, metadata: sex=male'; search_universal()">Try it</b-button>
          </div>
        </div>
      </div>

      <a class="advanced-toggle has-text-grey is-size-7" @click="advanced_open = !advanced_open">
        Advanced options {{ advanced_open ? '▴' : '▾' }}
      </a>

      <div class="advanced-panel" :class="{ 'is-open': advanced_open }">
        <div class="box mt-3">

          <p class="adv-group-title has-text-primary">Location</p>
          <b-field grouped group-multiline>
            <b-field label="Country" label-position="on-border">
              <b-input v-model="adv.country" placeholder="e.g. Australia" size="is-small"></b-input>
            </b-field>
            <b-field label="Location" label-position="on-border">
              <b-input v-model="adv.location" placeholder="e.g. Pacific Ocean" size="is-small"></b-input>
            </b-field>
            <b-field label="Latitude" label-position="on-border" :message="adv_errors.latitude" :type="adv_errors.latitude ? 'is-danger' : ''">
              <b-input v-model="adv.latitude" placeholder="e.g. -33.8 or -40-30" size="is-small" @input="on_adv_field_input('latitude')"></b-input>
            </b-field>
            <b-field label="Longitude" label-position="on-border" :message="adv_errors.longitude" :type="adv_errors.longitude ? 'is-danger' : ''">
              <b-input v-model="adv.longitude" placeholder="e.g. 151.2 or 140-160" size="is-small" @input="on_adv_field_input('longitude')"></b-input>
            </b-field>
          </b-field>

          <p class="adv-group-title has-text-primary">Sample</p>
          <b-field grouped group-multiline style="row-gap: 0.75rem;">
            <b-field label="Collection year" label-position="on-border" :message="adv_errors.year" :type="adv_errors.year ? 'is-danger' : ''">
              <b-input v-model="adv.year" placeholder="e.g. 2010 or 2010-2015" size="is-small" @input="on_adv_field_input('year')"></b-input>
            </b-field>
            <b-field label="Release year" label-position="on-border" :message="adv_errors.release_year" :type="adv_errors.release_year ? 'is-danger' : ''">
              <b-input v-model="adv.release_year" placeholder="e.g. 2018 or 2015-2020" size="is-small" @input="on_adv_field_input('release_year')"></b-input>
            </b-field>
            <b-field label="Temperature (°C)" label-position="on-border" :message="adv_errors.temperature" :type="adv_errors.temperature ? 'is-danger' : ''">
              <b-input v-model="adv.temperature" placeholder="e.g. 25 or 20-30" size="is-small" @input="on_adv_field_input('temperature')"></b-input>
            </b-field>
            <b-field label="Depth (m)" label-position="on-border" :message="adv_errors.depth" :type="adv_errors.depth ? 'is-danger' : ''">
              <b-input v-model="adv.depth" placeholder="e.g. 100 or 0-200" size="is-small" @input="on_adv_field_input('depth')"></b-input>
            </b-field>
            <b-field label-position="on-border" :message="adv_errors.age" :type="adv_errors.age ? 'is-danger' : ''">
              <template #label>
                Age
                <b-icon icon="information-outline" size="is-small" class="info-icon-btn" @mouseenter="showTooltip('age_info', $event)" @mouseleave="hideTooltipDelayed" />
              </template>
              <b-input v-model="adv.age" placeholder="e.g. 25 or 20-30" size="is-small" @input="on_adv_field_input('age')"></b-input>
            </b-field>
            <b-field label="Environment" label-position="on-border">
              <div class="buttons has-addons">
                <b-button size="is-small" :type="adv.environment === 'host' ? 'is-primary' : ''" @click="toggle_env('host')">Host</b-button>
                <b-button size="is-small" :type="adv.environment === 'ecological' ? 'is-primary' : ''" @click="toggle_env('ecological')">Ecological</b-button>
              </div>
            </b-field>
            <b-field label="Low complexity" label-position="on-border" style="width: 1000px; top: 10px; position relative">
              <div class="buttons has-addons">
                <b-button size="is-small" style="width: 82px;" :type="adv.low_complexity === 'yes' ? 'is-primary' : ''" @click="adv.low_complexity = adv.low_complexity === 'yes' ? '' : 'yes'">Yes</b-button>
                <b-button size="is-small" style="width: 82px;" :type="adv.low_complexity === 'no' ? 'is-primary' : ''" @click="adv.low_complexity = adv.low_complexity === 'no' ? '' : 'no'">No</b-button>
              </div>
            </b-field>
          </b-field>

          <p class="adv-group-title has-text-primary">Quality / Size</p>
          <b-field grouped group-multiline>
            <b-field label="SPF %" label-position="on-border" :message="adv_errors.spf" :type="adv_errors.spf ? 'is-danger' : ''">
              <b-input v-model="adv.spf" placeholder="e.g. 80 or 50-100" size="is-small" @input="on_adv_field_input('spf')"></b-input>
            </b-field>
            <b-field label="Known species fraction %" label-position="on-border" :message="adv_errors.ksf" :type="adv_errors.ksf ? 'is-danger' : ''">
              <b-input v-model="adv.ksf" placeholder="e.g. 90 or 70-100" size="is-small" @input="on_adv_field_input('ksf')"></b-input>
            </b-field>
            <b-field label="Size (Gbp)" label-position="on-border" :message="adv_errors.gbp" :type="adv_errors.gbp ? 'is-danger' : ''">
              <b-input v-model="adv.gbp" placeholder="e.g. 5 or 2-10" size="is-small" @input="on_adv_field_input('gbp')"></b-input>
            </b-field>
            <b-field label="Reads (millions)" label-position="on-border" :message="adv_errors.reads" :type="adv_errors.reads ? 'is-danger' : ''">
              <b-input v-model="adv.reads" placeholder="e.g. 50 or 10-100" size="is-small" @input="on_adv_field_input('reads')"></b-input>
            </b-field>
            <b-field label="Read length (bp)" label-position="on-border" :message="adv_errors.read_length" :type="adv_errors.read_length ? 'is-danger' : ''">
              <b-input v-model="adv.read_length" placeholder="e.g. 150 or 100-250" size="is-small" @input="on_adv_field_input('read_length')"></b-input>
            </b-field>
          </b-field>

          <p class="adv-group-title has-text-primary">Sequencing</p>
          <b-field grouped group-multiline>
            <b-field label-position="on-border">
              <template #label>
                Platform
                <b-icon icon="information-outline" size="is-small" class="info-icon-btn" @mouseenter="showTooltip('platform', $event)" @mouseleave="hideTooltipDelayed" />
              </template>
              <b-input v-model="adv.platform" placeholder="e.g. Illumina" size="is-small"></b-input>
            </b-field>
            <b-field label-position="on-border">
              <template #label>
                Instrument
                <b-icon icon="information-outline" size="is-small" class="info-icon-btn" @mouseenter="showTooltip('instrument', $event)" @mouseleave="hideTooltipDelayed" />
              </template>
              <b-input v-model="adv.instrument" placeholder="e.g. HiSeq 2500" size="is-small"></b-input>
            </b-field>
            <b-field label-position="on-border">
              <template #label>
                Library strategy
                <b-icon icon="information-outline" size="is-small" class="info-icon-btn" @mouseenter="showTooltip('library', $event)" @mouseleave="hideTooltipDelayed" />
              </template>
              <b-input v-model="adv.library_strategy" placeholder="e.g. WGS" size="is-small"></b-input>
            </b-field>
          </b-field>

          <teleport to="body">
            <div v-if="active_tooltip" class="info-tooltip-box" :style="{ left: tooltip_x + 'px', top: tooltip_y + 'px' }" @mouseenter="keepTooltipOpen" @mouseleave="hideTooltip">
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
                <p class="info-tooltip-title">Platform — all values</p>
                <div class="info-tooltip-grid">
                  <span>ILLUMINA</span><span>Illumina</span><span>Metagenomic</span>
                </div>
              </template>
              <template v-if="active_tooltip === 'instrument_info'">
                <p class="info-tooltip-title">Instrument — all values</p>
                <div class="info-tooltip-grid">
                  <span>Illumina NovaSeq 6000</span><span>Illumina HiSeq 2500</span><span>Illumina HiSeq 4000</span>
                  <span>NextSeq 500</span><span>Illumina HiSeq 2000</span><span>Illumina MiSeq</span>
                  <span>HiSeq X Ten</span><span>Illumina NovaSeq X</span><span>NextSeq 2000</span>
                  <span>NextSeq 550</span><span>Illumina HiSeq 3000</span><span>Illumina NovaSeq X Plus</span>
                  <span>Illumina HiSeq X</span><span>Illumina HiSeq 1000</span><span>Illumina HiSeq 1500</span>
                  <span>NextSeq 1000</span><span>Illumina MiniSeq</span><span>Illumina Genome Analyzer IIx</span>
                  <span>Illumina Genome Analyzer II</span><span>Illumina Genome Analyzer</span>
                  <span>Illumina HiSeq X Ten</span><span>HiSeq X Five</span><span>Illumina HiScanSQ</span>
                  <span>Illumina iSeq 100</span><span>Nova seq</span><span>MiSeq i100</span>
                </div>
              </template>
              <template v-if="active_tooltip === 'library_info'">
                <p class="info-tooltip-title">Library strategy — all values</p>
                <div class="info-tooltip-grid">
                  <span>WGS</span><span>OTHER</span><span>AMPLICON</span><span>WGA</span>
                  <span>RNA-Seq</span><span>Targeted-Capture</span><span>POOLCLONE</span><span>WXS</span>
                  <span>WCS</span><span>Hi-C</span><span>CLONE</span><span>ChIP-Seq</span>
                  <span>Bisulfite-Seq</span><span>Synthetic-Long-Read</span><span>RAD-Seq</span><span>ATAC-seq</span>
                  <span>CLONEEND</span><span>Tn-Seq</span><span>shotgun sequencing</span><span>FAIRE-seq</span>
                  <span>miRNA-Seq</span><span>FL-cDNA</span><span>DNase-Hypersensitivity</span><span>CTS</span>
                  <span>MRE-Seq</span><span>FINISHING</span><span>ssRNA-seq</span><span>EST</span>
                  <span>GBS</span><span>RIP-Seq</span><span>ncRNA-Seq</span><span>Ribo-seq</span>
                  <span>Tethered Chromatin Conformation Capture</span><span>NOMe-Seq</span><span>MBD-Seq</span>
                </div>
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
              <template v-if="active_tooltip === 'metadata_info'">
                <p class="info-tooltip-title">Metadata</p>
                <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.8); font-size: 0.78rem;">
                  Searches all free-form BioSample attributes submitted to NCBI — any extra metadata not covered by the structured fields above.
                </p>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.5); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em;">Two formats</p>
                <div class="info-tooltip-grid" style="margin-bottom: 0.5rem;">
                  <span>metadata: Sus scrofa — matches any attribute containing this value</span>
                  <span>metadata: host=Sus scrofa — matches only the "host" attribute</span>
                </div>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.5); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em;">Example attributes</p>
                <div class="info-tooltip-grid">
                  <span>host</span><span>tissue</span><span>disease</span><span>treatment</span>
                  <span>isolation_source</span><span>env_biome</span><span>body_site</span><span>age</span>
                  <span>sex</span><span>phenotype</span><span>genotype</span><span>strain</span>
                </div>
              </template>
              <template v-if="active_tooltip === 'platform'">
                <p class="info-tooltip-title">Platform values — click to select</p>
                <div class="info-tooltip-grid">
                  <span class="tt-clickable" @click="selectTooltipValue('ILLUMINA')">ILLUMINA</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina')">Illumina</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Metagenomic')">Metagenomic</span>
                </div>
              </template>
              <template v-if="active_tooltip === 'instrument'">
                <p class="info-tooltip-title">Instrument values — click to select</p>
                <div class="info-tooltip-grid">
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina NovaSeq 6000')">Illumina NovaSeq 6000</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 2500')">Illumina HiSeq 2500</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 4000')">Illumina HiSeq 4000</span>
                  <span class="tt-clickable" @click="selectTooltipValue('NextSeq 500')">NextSeq 500</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 2000')">Illumina HiSeq 2000</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina MiSeq')">Illumina MiSeq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('HiSeq X Ten')">HiSeq X Ten</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina NovaSeq X')">Illumina NovaSeq X</span>
                  <span class="tt-clickable" @click="selectTooltipValue('NextSeq 2000')">NextSeq 2000</span>
                  <span class="tt-clickable" @click="selectTooltipValue('NextSeq 550')">NextSeq 550</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 3000')">Illumina HiSeq 3000</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina NovaSeq X Plus')">Illumina NovaSeq X Plus</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq X')">Illumina HiSeq X</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 1000')">Illumina HiSeq 1000</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq 1500')">Illumina HiSeq 1500</span>
                  <span class="tt-clickable" @click="selectTooltipValue('NextSeq 1000')">NextSeq 1000</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina MiniSeq')">Illumina MiniSeq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina Genome Analyzer IIx')">Illumina Genome Analyzer IIx</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina Genome Analyzer II')">Illumina Genome Analyzer II</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina Genome Analyzer')">Illumina Genome Analyzer</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina HiSeq X Ten')">Illumina HiSeq X Ten</span>
                  <span class="tt-clickable" @click="selectTooltipValue('HiSeq X Five')">HiSeq X Five</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina HiScanSQ')">Illumina HiScanSQ</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Illumina iSeq 100')">Illumina iSeq 100</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Nova seq')">Nova seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('MiSeq i100')">MiSeq i100</span>
                </div>
              </template>
              <template v-if="active_tooltip === 'metadata'">
                <p class="info-tooltip-title">Metadata</p>
                <p style="margin-bottom: 0.5rem; color: rgba(255,255,255,0.8); font-size: 0.78rem;">
                  Searches all free-form BioSample attributes submitted to NCBI — any extra metadata not covered by the structured fields above.
                </p>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.5); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em;">Two formats</p>
                <div class="info-tooltip-grid" style="margin-bottom: 0.5rem;">
                  <span>metadata: Sus scrofa — matches any attribute containing this value</span>
                  <span>metadata: host=Sus scrofa — matches only the "host" attribute</span>
                </div>
                <p style="margin-bottom: 0.4rem; color: rgba(255,255,255,0.5); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em;">Example attributes</p>
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
                  <span class="tt-clickable" @click="selectTooltipValue('WGS')">WGS</span>
                  <span class="tt-clickable" @click="selectTooltipValue('OTHER')">OTHER</span>
                  <span class="tt-clickable" @click="selectTooltipValue('AMPLICON')">AMPLICON</span>
                  <span class="tt-clickable" @click="selectTooltipValue('WGA')">WGA</span>
                  <span class="tt-clickable" @click="selectTooltipValue('RNA-Seq')">RNA-Seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Targeted-Capture')">Targeted-Capture</span>
                  <span class="tt-clickable" @click="selectTooltipValue('POOLCLONE')">POOLCLONE</span>
                  <span class="tt-clickable" @click="selectTooltipValue('WXS')">WXS</span>
                  <span class="tt-clickable" @click="selectTooltipValue('WCS')">WCS</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Hi-C')">Hi-C</span>
                  <span class="tt-clickable" @click="selectTooltipValue('CLONE')">CLONE</span>
                  <span class="tt-clickable" @click="selectTooltipValue('ChIP-Seq')">ChIP-Seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Bisulfite-Seq')">Bisulfite-Seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Synthetic-Long-Read')">Synthetic-Long-Read</span>
                  <span class="tt-clickable" @click="selectTooltipValue('RAD-Seq')">RAD-Seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('ATAC-seq')">ATAC-seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('CLONEEND')">CLONEEND</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Tn-Seq')">Tn-Seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('shotgun sequencing')">shotgun sequencing</span>
                  <span class="tt-clickable" @click="selectTooltipValue('FAIRE-seq')">FAIRE-seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('miRNA-Seq')">miRNA-Seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('FL-cDNA')">FL-cDNA</span>
                  <span class="tt-clickable" @click="selectTooltipValue('DNase-Hypersensitivity')">DNase-Hypersensitivity</span>
                  <span class="tt-clickable" @click="selectTooltipValue('CTS')">CTS</span>
                  <span class="tt-clickable" @click="selectTooltipValue('MRE-Seq')">MRE-Seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('FINISHING')">FINISHING</span>
                  <span class="tt-clickable" @click="selectTooltipValue('ssRNA-seq')">ssRNA-seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('EST')">EST</span>
                  <span class="tt-clickable" @click="selectTooltipValue('GBS')">GBS</span>
                  <span class="tt-clickable" @click="selectTooltipValue('RIP-Seq')">RIP-Seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('ncRNA-Seq')">ncRNA-Seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Ribo-seq')">Ribo-seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('Tethered Chromatin Conformation Capture')">Tethered Chromatin Conformation Capture</span>
                  <span class="tt-clickable" @click="selectTooltipValue('NOMe-Seq')">NOMe-Seq</span>
                  <span class="tt-clickable" @click="selectTooltipValue('MBD-Seq')">MBD-Seq</span>
                </div>
              </template>
            </div>
          </teleport>

          <p class="adv-group-title has-text-primary">Taxonomy</p>
          <b-field grouped group-multiline>
            <b-field label="Organism" label-position="on-border">
              <b-input v-model="adv.organism" placeholder="e.g. marine metagenome" size="is-small"></b-input>
            </b-field>
            <b-field label="Taxonomy" label-position="on-border">
              <b-input v-model="adv.taxonomy" placeholder="e.g. s__Prochlorococcus" size="is-small"></b-input>
            </b-field>
          </b-field>

          <p class="adv-group-title has-text-primary">Study</p>
          <b-field grouped group-multiline>
            <b-field label="Study title" label-position="on-border">
              <b-input v-model="adv.study" placeholder="e.g. Tara Oceans" size="is-small"></b-input>
            </b-field>
            <b-field label="Abstract" label-position="on-border">
              <b-input v-model="adv.abstract" placeholder="e.g. coral reef" size="is-small"></b-input>
            </b-field>
            <b-field label="BioProject" label-position="on-border">
              <b-input v-model="adv.bioproject" placeholder="e.g. PRJNA12345" size="is-small"></b-input>
            </b-field>
          </b-field>

          <p class="adv-group-title has-text-primary">Identifiers</p>
          <b-field grouped group-multiline>
            <b-field label="SRA study" label-position="on-border">
              <b-input v-model="adv.sra_study" placeholder="e.g. SRP012345" size="is-small"></b-input>
            </b-field>
            <b-field label="Experiment" label-position="on-border">
              <b-input v-model="adv.experiment" placeholder="e.g. SRX012345" size="is-small"></b-input>
            </b-field>
            <b-field label="Sample accession" label-position="on-border">
              <b-input v-model="adv.sample_acc" placeholder="e.g. SRS012345" size="is-small"></b-input>
            </b-field>
            <b-field label="BioSample" label-position="on-border">
              <b-input v-model="adv.biosample" placeholder="e.g. SAMN12345" size="is-small"></b-input>
            </b-field>
          </b-field>

          <p class="adv-group-title has-text-primary">Submitter</p>
          <b-field grouped group-multiline>
            <b-field label="Organisation" label-position="on-border">
              <b-input v-model="adv.organisation" placeholder="e.g. MIT or Woods Hole" size="is-small"></b-input>
            </b-field>
          </b-field>

          <p class="adv-group-title has-text-primary">Metadata</p>
          <b-field grouped group-multiline>
            <b-field label-position="on-border">
              <template #label>
                Metadata
                <b-icon icon="information-outline" size="is-small" class="info-icon-btn" @mouseenter="showTooltip('metadata', $event)" @mouseleave="hideTooltipDelayed" />
              </template>
              <b-input v-model="adv.attr" placeholder="e.g. sex=male or age=1-2" size="is-small"></b-input>
            </b-field>
          </b-field>

          <div class="keys-syntax-row" style="margin-top: 1rem;">
            <span class="keys-syntax-title">Query Syntax</span>
            <div class="keys-syntax-items">
              <span class="keys-syntax-item"><code>2-10</code> range</span>
              <span class="keys-syntax-item"><code>&gt;10</code> greater than</span>
              <span class="keys-syntax-item"><code>&gt;=10</code> at least</span>
              <span class="keys-syntax-item"><code>&lt;10</code> less than</span>
              <span class="keys-syntax-item"><code>&lt;=10</code> at most</span>
              <span class="keys-syntax-item"><code>10</code> exact / approx</span>
            </div>
          </div>

          <b-button type="is-primary" size="is-small" class="mt-2" @click="generate_query">Generate query</b-button>

        </div>
      </div>

      <br /><b-button type="is-primary" @click="search_universal" :loading="universal_loading">Search</b-button>

      <div v-if="universal_result" class="mt-4">
        <b-message v-if="universal_result.count === 0" type="is-warning" has-icon>
          No samples found matching {{ universal_result.match_description }}.
        </b-message>
        <b-message v-else type="is-info" has-icon>
          <strong>{{ universal_result.count.toLocaleString() }}</strong> samples match {{ universal_result.match_description }}.
          <br />
          <b-button type="is-primary is-small" class="mt-2" @click="explore_random_universal">Explore a random one</b-button>
        </b-message>
      </div>
    </section>

    <section class="section" @keyup.enter="search_by_taxonomy">
      <p class="title is-4">Search for public metagenomes by taxonomy</p>
      <b-field>
        <b-autocomplete v-model="taxonomy" rounded
          max-height="600px"
          icon="magnify"
          :data="autocomplete_taxons"
          :loading="isFetching"
          @typing="getAsyncData">
          <template #empty>No results found</template>
        </b-autocomplete>
      </b-field>
      <p class="help">
        Suggestions include <a href='http://gtdb.ecogenomic.org'>Genome Taxonomy Database (GTDB)</a> ({{ GTDB_VERSION }})
        and <a href='http://globdb.org'>GlobDB</a> ({{ GLOBDB_VERSION }}) taxonomies.
      </p>
      <br /><b-button type="is-primary" @click="search_by_taxonomy">Search</b-button>
    </section>

    <section class="section"  @keyup.enter="search_by_accession">
      <p class="title is-4">Search for run/sample/project accession</p>
      <b-field>
        <b-input v-model="accession"></b-input>
      </b-field>
      <br /><b-button type="is-primary" @click="search_by_accession">Search</b-button>
    </section>


    <section class="section"  @keyup.enter="search_by_random">
      <p class="title is-4">Find a random run</p>
      <b-field>
        <b-switch v-model="random_choice_host">Eukaryote host-associated</b-switch>
        <b-switch v-model="random_choice_ecological">Ecological</b-switch>
        <b-switch v-model="random_choice_two_gbp">2+ Gbp</b-switch>
        <b-switch v-model="random_choice_non_human_host">Non-human host only</b-switch>
        <b-switch v-model="random_exclude_strict_low_complexity">Exclude low complexity (≥95% one order)</b-switch>
      </b-field>
      <br /><b-button type="is-primary" @click="search_by_random">Search</b-button>
    </section>

  </section>
</template>

<script>
import { fetchTaxonomySearchHints, fetchSandpiperStats, fetchUniversalSearch } from '@/api'
import { GTDB_VERSION, GLOBDB_VERSION } from '@/versions'
import debounce from 'lodash/debounce'

export default {
  name: 'Search',
  title: 'Search - Sandpiper',
  data () {
    return {
      GTDB_VERSION,
      GLOBDB_VERSION,
      gtdb_version: null,

      universal_query: '',
      universal_loading: false,
      universal_result: null,

      keys_open: false,
      advanced_open: false,
      adv: {
        // Location
        country: '', continent: '', location: '', latitude: '', longitude: '',
        // Sample
        year: '', release_year: '', temperature: '', depth: '', environment: '', low_complexity: '',
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
      },
      adv_errors: {},
      adv_error_timers: {},
      active_tooltip: null,
      tooltip_x: 0,
      tooltip_y: 0,
      tooltip_close_timer: null,

      taxonomy: 'c__Bog-38',
      autocomplete_taxons: [],
      selected: null,
      isFetching: false,
      accession: 'ERR1914274',

      random_choice_host: false,
      random_choice_non_human_host: true,
      random_choice_ecological: true,
      random_choice_two_gbp: true,
      random_exclude_strict_low_complexity: true
    }
  },

  created () {
    if (this.$route.query.q) {
      this.universal_query = this.$route.query.q
    }
    this.fetchData()
  },

  watch: {
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
  
  methods: {
    showTooltip (name, event) {
      clearTimeout(this.tooltip_close_timer)
      const rect = event.target.getBoundingClientRect()
      const tooltipW = 420
      const tooltipH = {
        instrument_info: 420,
        library_info: 480,
        metadata_info: 360,
        platform_info: 100,
        taxonomy_info: 220,
        metadata: 360,
        age_info: 180,
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
    },
    hideTooltipDelayed () {
      this.tooltip_close_timer = setTimeout(() => {
        this.active_tooltip = null
      }, 250)
    },
    keepTooltipOpen () {
      clearTimeout(this.tooltip_close_timer)
    },
    hideTooltip () {
      clearTimeout(this.tooltip_close_timer)
      this.active_tooltip = null
    },
    selectTooltipValue (value) {
      if (this.active_tooltip === 'platform') this.adv.platform = value
      else if (this.active_tooltip === 'instrument') this.adv.instrument = value
      else if (this.active_tooltip === 'library') this.adv.library_strategy = value
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
      const KEY_RE = /^(longitude|lon|latitude|lat|country|continent|location|geo|year|release_year|temperature|temp|depth|environment|env|low_complexity|spf|prokaryotic_fraction|ksf|known_species_fraction|gbp|bases|size|reads|spots|read_length|platform|instrument|model|library_strategy|strategy|organism|taxon_name|taxonomy|study|study_title|title|abstract|study_abstract|bioproject|sra_study|sra|experiment|exp|sample_acc|sample|biosample|organisation|organization|age|attr|attribute|biosample_attr|metadata)\s*:/i
      const freetext_parts = this.universal_query.split(',')
        .map(p => p.trim())
        .filter(p => p && !KEY_RE.test(p))
      parts.push(...freetext_parts)
      const text_fields = [
        ['country', this.adv.country], ['continent', this.adv.continent],
        ['location', this.adv.location], ['latitude', this.adv.latitude], ['longitude', this.adv.longitude],
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
        ['metadata', this.adv.attr],
      ]
      for (const [key, val] of text_fields) {
        if (val && val.trim()) parts.push(`${key}: ${val.trim()}`)
      }
      if (this.adv.environment) parts.push(`environment: ${this.adv.environment}`)
      if (this.adv.low_complexity) parts.push(`low_complexity: ${this.adv.low_complexity}`)
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
        const val = (this.adv[field] || '').trim()
        if (val && !range_re.test(val) && !op_re.test(val)) {
          this.adv_errors = { ...this.adv_errors, [field]: 'Use a number, range e.g. 10-20, or operator e.g. >10' }
        }
      }, 3000)
    },

    validate_advanced () {
      this.adv_errors = {}
      const range_re = /^-?\d+(\.\d+)?(-(-?\d+(\.\d+)?))?$/
      const op_re = /^[<>]=?-?\d+(\.\d+)?$/
      for (const field of ['year', 'release_year', 'temperature', 'depth', 'latitude', 'longitude', 'spf', 'ksf', 'gbp', 'reads', 'read_length', 'age']) {
        const val = (this.adv[field] || '').trim()
        if (val && !range_re.test(val) && !op_re.test(val)) {
          this.adv_errors[field] = 'Use a number, range e.g. 10-20, or operator e.g. >10'
        }
      }
      return Object.keys(this.adv_errors).length === 0
    },

    parse_query_to_advanced () {
      if (!this.universal_query.trim()) return
      const KEY_MAP = {
        country: 'country', continent: 'continent',
        location: 'location', geo: 'location',
        latitude: 'latitude', lat: 'latitude',
        longitude: 'longitude', lon: 'longitude',
        year: 'year', release_year: 'release_year',
        temperature: 'temperature', temp: 'temperature',
        depth: 'depth',
        environment: 'environment', env: 'environment',
        low_complexity: 'low_complexity',
        spf: 'spf', prokaryotic_fraction: 'spf',
        ksf: 'ksf', known_species_fraction: 'ksf',
        gbp: 'gbp', bases: 'gbp', size: 'gbp',
        reads: 'reads', spots: 'reads',
        read_length: 'read_length',
        platform: 'platform',
        instrument: 'instrument', model: 'instrument',
        library_strategy: 'library_strategy', strategy: 'library_strategy',
        organism: 'organism', taxon_name: 'organism',
        taxonomy: 'taxonomy',
        study: 'study', study_title: 'study', title: 'study',
        abstract: 'abstract', study_abstract: 'abstract',
        bioproject: 'bioproject',
        sra_study: 'sra_study', sra: 'sra_study',
        experiment: 'experiment', exp: 'experiment',
        sample_acc: 'sample_acc', sample: 'sample_acc',
        biosample: 'biosample',
        organisation: 'organisation', organization: 'organisation',
        age: 'age',
        attr: 'attr', attribute: 'attr', biosample_attr: 'attr', metadata: 'attr',
      }
      const freetext = []
      for (const part of this.universal_query.split(',').map(p => p.trim()).filter(Boolean)) {
        const m = part.match(/^([\w\s]+?):\s*(.+)$/)
        if (m) {
          const adv_key = KEY_MAP[m[1].toLowerCase().trim()]
          if (adv_key) {
            this.adv[adv_key] = m[2].trim()
            continue
          }
        }
        freetext.push(part)
      }
      this.universal_query = freetext.join(', ')
    },

    toggle_env (val) {
      this.adv.environment = this.adv.environment === val ? '' : val
    },

    generate_query () {
      if (!this.validate_advanced()) return
      this.universal_query = this.build_query()
    },

    async search_universal () {
      const query = this.universal_query.trim()
      if (!query) { this.universal_result = null; return }
      if (this.$route.query.q !== query) {
        const savedY = window.scrollY
        this.$router.replace({ query: { q: query } })
        this.$nextTick(() => window.scrollTo(0, savedY))
      }
      this.universal_loading = true
      try {
        const { data } = await fetchUniversalSearch(query)
        this.universal_result = data
        if (data.count === 1 && data.random_acc) {
          this.$router.push({ name: 'Run', params: { accession: data.random_acc }, query: { q: query } })
        }
      } catch (e) {
        this.universal_result = { count: 0, match_description: 'search error' }
      } finally {
        this.universal_loading = false
      }
    },

    async next_universal () {
      const query = this.universal_query.trim()
      if (!query) return
      if (this.$route.query.q !== query) {
        this.$router.replace({ query: { q: query } })
      }
      this.universal_loading = true
      try {
        const { data } = await fetchUniversalSearch(query)
        this.universal_result = data
        if (data.random_acc) {
          this.$router.push({ name: 'Run', params: { accession: data.random_acc }, query: { q: query } })
        }
      } catch (e) {
        this.universal_result = { count: 0, match_description: 'search error' }
      } finally {
        this.universal_loading = false
      }
    },

    search_universal_debounced: debounce(function () {
      const query = this.universal_query.trim()
      if (!query) { this.universal_result = null; return }
      this.universal_loading = true
      fetchUniversalSearch(query)
        .then(({ data }) => {
          this.universal_result = data
          if (data.count === 1 && data.random_acc) {
            this.$router.push({ name: 'Run', params: { accession: data.random_acc }, query: { q: query } })
          }
        })
        .catch(() => {
          this.universal_result = { count: 0, match_description: 'search error' }
        })
        .finally(() => {
          this.universal_loading = false
        })
    }, 450),

    explore_random_universal () {
      if (this.universal_result && this.universal_result.random_acc) {
        const query = this.universal_query.trim()
        this.$router.push({ name: 'Run', params: { accession: this.universal_result.random_acc }, query: query ? { q: query } : undefined })
      }
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
      fetchTaxonomySearchHints(name)
        .then(({ data }) => {
          this.autocomplete_taxons = data.taxonomies
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
  z-index: 9999;
  background: rgba(25, 25, 35, 0.97);
  color: #fff;
  border-radius: 8px;
  padding: 0.8rem 1rem;
  min-width: 280px;
  max-width: 420px;
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.5);
  font-size: 0.78rem;
  line-height: 1.5;
  pointer-events: auto;
}
.tt-clickable {
  cursor: pointer;
}
.tt-clickable:hover {
  background: rgba(255, 255, 255, 0.28) !important;
  color: #fff;
}
</style>

<style scoped>
.keys-syntax-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 0.75rem 0.1rem;
  border-top: 1px solid rgba(0,0,0,0.07);
  margin-top: 0.4rem;
}
.keys-syntax-title {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #999;
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
  color: hsl(271, 100%, 71%);
  margin-right: 0.2rem;
}
.keys-example-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem 0.25rem;
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
.advanced-toggle {
  cursor: pointer;
  display: inline-block;
  margin-top: 0.5rem;
  user-select: none;
}
.advanced-panel {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
}
.advanced-panel.is-open {
  max-height: 4000px;
}
.adv-group-title {
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: 1.75rem;
  margin-bottom: 0.6rem;
}
.adv-group-title:first-child {
  margin-top: 0;
}
.keys-toggle {
  cursor: pointer;
  font-weight: 600;
  margin-left: 0.2rem;
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
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 0.5rem;
}
.info-tooltip-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
.info-tooltip-grid span {
  background: rgba(255, 255, 255, 0.12);
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-size: 0.75rem;
  white-space: nowrap;
}
.keys-panel {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
}
.keys-panel.is-open {
  max-height: 1200px;
}
.keys-box {
  padding: 1rem 1.25rem;
}
.keys-columns {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem 2rem;
}
.keys-group {
  min-width: 160px;
  flex: 1;
}
.keys-group-title {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #999;
  border-bottom: 1px solid #eee;
  padding-bottom: 0.2rem;
  margin-bottom: 0.45rem;
}
.keys-item {
  font-size: 0.82rem;
  margin-bottom: 0.3rem;
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
}
.keys-item-label {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
}
.keys-example {
  color: #aaa;
  font-size: 0.75rem;
  padding-left: 0.25rem;
}
</style>
