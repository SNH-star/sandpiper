<script setup>
import sandpiperLogo from "@/assets/sandpiper_logo.png";
import algorithmDiagram from "@/assets/singlem_weebill_integration_v4.png";
import { GTDB_VERSION, GLOBDB_VERSION } from '@/versions'
import PageRail from '@/components/PageRail.vue'
import habitatLabels from '@/constants/indicpiperHabitats.json'
import {
  INDICATOR_GENERA_BY_HABITAT as indicatorGenera, INDICPIPER_VERSION, INDICATORS_DEFINED_FROM, HABITAT_COUNT, INDICATOR_GENUS_COUNT
} from '@/utils/indicpiperFacts'

// Each IndicPiper habitat with the BioSample organism values recorded as it, without the " metagenome" suffix,
// the one with the most indicator genera first.
const INDICPIPER_HABITATS = Object.entries(habitatLabels).reduce((rows, [label, habitat]) => {
  const row = rows.find(item => item.habitat === habitat) || rows[rows.push({ habitat, organisms: [] }) - 1]
  row.organisms.push(label.replace(/ metagenome$/, ''))
  return rows
}, []).sort((a, b) => (indicatorGenera[b.habitat] || []).length - (indicatorGenera[a.habitat] || []).length || a.habitat.localeCompare(b.habitat))
</script>

<template>
  <div class="about-page">
    <header class="section about-header">
      <div class="container">
      <b-image
        :src="sandpiperLogo"
        class="about-logo"
        alt="Sandpiper Logo"
        />
      <p class="about-lede">A searchable database of the microbial communities in public metagenomes, profiled with SingleM.</p>
      </div>
    </header>

    <page-rail :items="JUMP_ITEMS" :current="current_section" strip top="8rem" @jump="jumpTo" />

    <section id="team" class="section about-section">
      <div class="container">
      <h2 class="title is-3 about-heading">Team</h2>
      <div class="about-body">
        <p>This website, and SingleM itself, is the result of a collaboration between (in no particular order):</p>
        <ul class="about-people">
          <li><a href="https://research.qut.edu.au/cmr/team/ben-woodcroft/">Ben Woodcroft</a></li>
          <li>Rossen Zhao</li>
          <li>Mitchell Cunningham</li>
          <li>Joshua Mitchell</li>
          <li>Samuel Aroney</li>
          <li>Rizky Nurdiansyah</li>
          <li><a href="https://findanexpert.unimelb.edu.au/profile/753413-linda-blackall">Linda Blackall</a></li>
          <li><a href="https://research.qut.edu.au/cmr/team/gene-tyson/">Gene Tyson</a></li>
          <li><a href="https://www.alberdilab.dk/members">Raphael Eisenhofer</a></li>
          <li><a href="https://www.alberdilab.dk/members">Antton Alberdi</a></li>
          <li>Stefan Herholdt</li>
        </ul>
        <p>Most of us are at the <a href="https://research.qut.edu.au/cmr/">Centre for Microbiome Research</a>, School of Biomedical Sciences, Queensland University of Technology (<a href="https://www.qut.edu.au">QUT</a>), Translational Research Institute, Woolloongabba, Australia. Mitchell Cunningham and Linda Blackall are at the School of BioSciences, The University of Melbourne, Victoria, Australia. Raphael Eisenhofer and Antton Alberdi are at the Centre for Evolutionary Hologenomics, Globe Institute, University of Copenhagen, Denmark.</p>
      </div>
      </div>
    </section>

    <section id="citations" class="section about-section">
      <div class="container">
      <h2 class="title is-3 about-heading">Citations</h2>
      <div class="about-body">
        <p>The overall citation for SingleM/Sandpiper:</p>
        <p>Ben J. Woodcroft, Samuel T. N. Aroney, Rossen Zhao, Mitchell Cunningham, Joshua A. M. Mitchell, Rizky Nurdiansyah, Linda Blackall & Gene W. Tyson. <i>Comprehensive taxonomic identification of microbial species in metagenomic data using SingleM and Sandpiper</i>. Nat Biotechnol (2025). <a href="https://doi.org/10.1038/s41587-025-02738-1">https://doi.org/10.1038/s41587-025-02738-1</a></p>

        <p>The prokaryotic fraction (SPF) mode of SingleM:</p>
        <p>Eisenhofer, R., Alberdi, A., & Woodcroft, B. J. (2026). <i>Large-scale estimation of bacterial and archaeal DNA prevalence in metagenomes reveals biome-specific patterns</i>. mSystems, 11(4), e0106225. <a href="https://doi.org/10.1128/msystems.01062-25">https://doi.org/10.1128/msystems.01062-25</a>.</p>
      </div>
      </div>
    </section>

    <section id="bulk-download" class="section about-section">
      <div class="container">
      <h2 class="title is-3 about-heading">Bulk download</h2>
      <div class="about-body">
        <p>Community profiles, IndicPiper habitat results and Metalog metadata are available for download.</p>
        <p>Community profiles for all runs are available for download from <a href="https://zenodo.org/doi/10.5281/zenodo.10547493">Zenodo</a>. The data behind older versions of Sandpiper can also be downloaded there as they are stored as old Zenodo versions.</p>
        <p>IndicPiper habitat results and Metalog sample metadata, for every run in this database, will also be made available via Zenodo.</p>
        <p>Please feel free to get in touch with <a href="https://research.qut.edu.au/cmr/team/ben-woodcroft/">us</a> if you have any questions or comments, or want data of other kinds.</p>
      </div>
      </div>
    </section>

    <section id="how-built" class="section about-section">
      <div class="container">
      <h2 class="title is-3 about-heading">How Sandpiper {{ version }} was built</h2>
      <div class="about-body">
        <p>Sandpiper profiles the microbial communities of public metagenomes. The runs come from the <a href="https://www.ncbi.nlm.nih.gov/sra">NCBI SRA</a>: those designated as metagenomic, or derived from "metagenomic" organisms such as "soil metagenome". This list of public metagenomes was generated on {{ scrape_date }}.</p>

        <p>Each run is profiled in two ways:</p>
        <div class="content">
          <ul>
            <li><a href="https://github.com/wwood/singlem">SingleM</a> reads sequences from 59 single-copy marker genes, so it detects lineages without needing a reference genome for each species.</li>
            <li><a href="#weebill" @click.prevent="jumpTo('weebill')">Weebill</a> matches the reads against whole reference genomes, which names species that the marker genes alone leave unassigned.</li>
          </ul>
        </div>
      </div>

      <figure class="workflow-figure">
        <a :href="algorithmDiagram" target="_blank" rel="noopener" title="Open the diagram full size">
          <img :src="algorithmDiagram" width="7225" height="5101" loading="lazy"
               alt="Diagram of the Sandpiper algorithm in three panels. Panel a, SingleM: shotgun reads from one run are screened with a fast DIAMOND BLASTX search against dereplicated markers, aligned to 59 marker HMMs and grouped into OTUs, then given species-level taxonomy by matching OTU nucleotides and genus-level taxonomy with DIAMOND BLASTX, giving one OTU table per marker. Panel b, Weebill, new in v2.2: reads and GTDB R232 genomes are sketched into k-mers, matched to find which genomes are present, genomes are kept at 95 percent ANI or more, shared k-mers are reassigned to the best-supported genome, and the report gives each genome's ANI and coverage on the true scale. Panel c, integration with SingleM: the marker profiles are condensed into one consensus profile. Species found by both tools keep SingleM's estimate. Species only Weebill detects are injected as a new species leaf, with coverage drawn from the unresolved part of their clade, so SingleM stays the authority on each clade's total coverage. The output is coverage and relative abundance for every taxon." />
        </a>
        <figcaption>The Sandpiper algorithm: SingleM marker genes (a), Weebill whole-genome matching (b) and how the two are integrated (c). Select the diagram to open it full size.</figcaption>
      </figure>

      <div class="about-body">
        <p>The taxonomy from the community profiles was assigned using either the <a href="https://gtdb.ecogenomic.org/">Genome Taxonomy Database (GTDB)</a> ({{ GTDB_VERSION }}), or <a href="https://globdb.org">GlobDB</a> ({{ GLOBDB_VERSION }}). The GTDB profiles combine SingleM and Weebill. The GlobDB profiles use SingleM only.</p>

        <p>SingleM estimates lineage abundances directly from shotgun metagenome data without heavy reliance on reference sequence databases. It operates by scanning for reads that cover highly conserved regions of single copy marker genes (35 bacterial, 37 archaeal, 59 total) when translated into amino acids. Reads covering these conserved sections are clustered prior to taxonomy assignment, allowing detection of strain-level diversity and novel lineages.</p>

        <p>The SingleM marker-gene profiles are combined ("condensed") into a single taxonomic profile per run, representing the read coverage of each taxon in the metagenome. For GTDB, the Weebill species profile of the same run is merged in at this step: where Weebill detects a species that SingleM could not resolve to species level, that species is added to the profile. Species found by both tools keep SingleM's estimate, and a species only Weebill detects takes its coverage from the unresolved part of its clade, so SingleM remains the authority on each clade's total coverage. Relative abundance is found by dividing the coverage of each taxon by the total coverage of the metagenome, and this is used to generate the Sandpiper visualisations.</p>

        <p>The known species fraction is calculated from the combined SingleM + Weebill GTDB profile. The low complexity flag, the top order fraction, the SingleM Prokaryotic Fraction (SPF) and the host prediction are based on the SingleM profile alone.</p>

        <p>For more complicated analyses that rely on alternative taxonomic groupings or novel lineages, a more bespoke search procedure might be appropriate. These kinds of analyses cannot currently be done on the sandpiper website, but in such cases please <a :href="'mailto:'+decode('o.jbbqpebsg@dhg.rqh.nh')">get in touch</a> with us.</p>

        <p>Community profiles derived from older versions are available as a bulk download (see above).</p>
      </div>

      <div class="about-detail-tools">
        <p class="about-detail-tools-title">Details</p>
        <b-button size="is-small" type="is-primary" @click="setDetails(true)">Expand all</b-button>
        <b-button size="is-small" type="is-primary" @click="setDetails(false)">Collapse all</b-button>
      </div>

      <details id="spf" class="about-detail">
        <summary><h3 class="title is-5">SingleM Prokaryotic Fraction (SPF)</h3></summary>
        <div class="about-detail-body">
          <p>To estimate the number of reads in each metagenome which are either bacterial or archaeal, the <a href="https://wwood.github.io/singlem/tools/prokaryotic_fraction">prokaryotic_fraction</a> (SPF) mode of SingleM was used. SPF bases its estimate on the coverage of each taxon in the SingleM community profile, the genome lengths of those taxons, and the total size of the metagenome. It does not rely on mapping reads to non-prokaryotic reference genomes.</p>
        </div>
      </details>

      <details id="weebill" class="about-detail">
        <summary><h3 class="title is-5">Weebill (Sylph fork)</h3></summary>
        <div class="about-detail-body">
          <p>
            <a href="https://github.com/wwood/weebill">Weebill</a> is a fork of
            <a href="https://github.com/bluenote-1577/sylph">Sylph</a>, a metagenome profiler that compares
            k-mer sketches. It reduces sequencing reads and a database of reference genomes to small sketches,
            and reports which genomes are present and at what coverage. Sylph is described in Shaw &amp; Yu,
            <i>Rapid species-level metagenome profiling and containment estimation with sylph</i>,
            <i>Nature Biotechnology</i> (2024), <a href="https://doi.org/10.1038/s41587-024-02412-y">https://doi.org/10.1038/s41587-024-02412-y</a>.
          </p>
          <p><strong>What it changes.</strong> More of each community is assigned to named species, which raises the known species fraction.</p>
          <p><strong>Weebill only runs.</strong> For some runs SingleM found no marker genes, so the whole GTDB profile comes from Weebill's k-mer matching; these runs are in Sandpiper only because of Weebill. They carry a "Weebill only" pill on the Run page and can be found with <span class="query-box">weebill_only: yes</span>. GlobDB profiles use SingleM alone, so these runs have no GlobDB profile.</p>
          <p><strong>How it is used here.</strong> Each run was profiled with Weebill against the genomes of GTDB R232, using the genome database bundled with the SingleM metapackage. Weebill was first used in Sandpiper v2.2.*; <a href="#how-built" @click.prevent="jumpTo('how-built')">how its results are merged</a> is described above.</p>
          <p><strong>Version.</strong> Weebill 0.4.0.</p>
        </div>
      </details>

      <details id="host-prediction" class="about-detail">
        <summary><h3 class="title is-5">Prediction of whether the metagenome is associated with a eukaryotic host</h3></summary>
        <div class="about-detail-body">
          <p>Each metagenome was predicted as either host-associated or ecological based upon a machine learning algorithm (an <a href="https://xgboost.ai/">XGBoost</a> one achieving ~93% accuracy), using the "organism" metadata field recorded at NCBI as the target for prediction, and the taxonomic profile as the input data. Metagenomes are either classified as "eukaryote host-associated" or "ecological". Host-associated samples are recorded or predicted to be under the <a href="https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=410656">organismal metagenome</a> NCBI taxonomy, ecological ones are all others. We anticipate that predictions based on microbial community profiles will become an increasingly important method for characterising microbiomes in the future, and we hope that future versions of this website will provide more detailed predictions about each community.</p>
        </div>
      </details>

      <details id="metadata-corrections" class="about-detail">
        <summary><h3 class="title is-5">Metadata corrections</h3></summary>
        <div class="about-detail-body">
          <p>Sandpiper uses data from the <a href="https://www.ncbi.nlm.nih.gov/sra">NCBI SRA</a> and associated databases to add metadata to each sequence dataset. Many times, this metadata is incorrect, vague or missing. If you notice something like this, we are collecting and correcting them in <a href="https://github.com/wwood/public_sequencing_metadata_corrections">public repository</a>. Any corrections submitted there (or submitted directly upstream e.g. to NCBI) are appreciated.</p>
        </div>
      </details>

      <details id="low-complexity" class="about-detail">
        <summary><h3 class="title is-5">Low Complexity</h3></summary>
        <div class="about-detail-body">
          <p>Samples flagged as low complexity are much less likely than most metagenomes to be true microbial communities. For instance, they might be single amplified genomes (SAGs), negative controls, or isolate genomic data that was marked as metagenomic when the data was deposited by the authors. Since the primary interest of Sandpiper is in microbial communities, these samples are hidden by default in most places on Sandpiper.</p>
          <p>We define “low complexity” samples as those where 95% or more of the community was assigned to a single order by SingleM, using the GTDB reference database.</p>
        </div>
      </details>

      <details id="metalog" class="about-detail">
        <summary><h3 class="title is-5">Metalog Metadata</h3></summary>
        <div class="about-detail-body">
          <p>
            Additional contextual metadata was obtained from
            <a href="https://metalog.embl.de/">Metalog</a><span v-if="metalog_retrieved_date">
            on {{ metalog_retrieved_date }}</span>. Kuhn et al.,
            <i>Metalog: curated and harmonised contextual data for global metagenomics samples</i>,
            <i>Nucleic Acids Research</i> (2025),
            <a href="https://doi.org/10.1093/nar/gkaf1118">https://doi.org/10.1093/nar/gkaf1118</a>.
            Information is presented under Metalog additional information within each Run page. Pages that do not contain any information will report back "No Metalog metadata recorded for this run". We downloaded Metalog's four "Extended wide" files (Human, animal, ocean and environment), because Metalog has no per-sample API. The extended wide allows one row per sample, allowing it to be an easy lookup and allocate.
          </p>
          <p class="about-tiles-title"><a href="https://metalog.embl.de/">Last metadata update: {{ metalog_last_update }}</a></p>
          <dl class="metalog-tiles">
            <div v-for="tile in METALOG_TILES" :key="tile.key" :class="{ 'is-total': tile.key === 'total' }">
              <dt>{{ tile.label }}</dt>
              <dd>{{ metalog_sample_counts[tile.key] }}</dd>
            </div>
          </dl>
          <p class="about-note">Sample counts, taken from the Metalog website at the time of database generation.</p>
        </div>
      </details>

      <details id="gold" class="about-detail">
        <summary><h3 class="title is-5">Gold (JGI) Metadata</h3></summary>
        <div class="about-detail-body">
          <p>
            Runs that were sequenced by the Joint Genome Institute (JGI) carry a project ID from its
            <a href="https://gold.jgi.doe.gov/">Genomes OnLine Database (GOLD)</a> in their BioSample record
            (Gp followed by digits, for example Gp0119859). Using the
            <a href="https://gold-ws.jgi.doe.gov/">GOLD web service</a> Sandpiper holds the additional metadata related to the metagenomes. GOLD is a curated resource, so its habitat classification, collection details and
            study descriptions are often more complete than what the submitter gave NCBI.
          </p>
          <p>
            Information is presented within Sample information on each Run page, in gold rows next to the green Metalog rows, and
            only for runs with a GOLD project ID; other pages show nothing. Each row's information button describes the field.
            The rows cover GOLD's habitat path (ecosystem, category, type, subtype and specific ecosystem), collection site,
            location, date, depth, pH, salinity, temperature and other measurements, host details, ENVO terms, the sequencing
            platform, centre and funding programme, and the study name and description. Publications that GOLD links to the project
            appear in gold under Publications near the top of the page, alongside those already linked from NCBI. The
            Additional Run Metadata CSV on each page holds the Metalog and GOLD details for that run together.
          </p>
          <p>
            Like the NCBI fields, each GOLD field is compared with the related runs of the same study that also have GOLD data.
            Many runs have no related
            GOLD runs, so no bars are shown for them.
          </p>
          <p>
            Every field GOLD records can be searched with the GOLD (JGI) field in the Advanced Search, in the same way as Metalog:
            <span class="query-box">gold: habitat=marine</span> looks only in the habitat field, <span class="query-box">gold: eye</span> looks in every field (so it
            also finds IDs, lists and publication details), a GOLD project ID finds that project, and an empty field finds every
            run with GOLD data. The help button beside the field lists every field name. The records are a copy taken when this
            version was built (the Statistics page gives the date), so a later edit in GOLD shows only in the next version.
            Contact names and email addresses in GOLD's records are not kept or shown.
          </p>
          <p>
            GOLD metadata is provided by the Joint Genome Institute (JGI), a U.S. Department of Energy Office of Science user
            facility, from the <a href="https://gold.jgi.doe.gov/">Genomes OnLine Database (GOLD)</a>. Please cite: Mukherjee S, et
            al. Genomes OnLine Database (GOLD) v.10: new features and updates. <i>Nucleic Acids Research</i> (2024),
            <a href="https://doi.org/10.1093/nar/gkae1000">doi:10.1093/nar/gkae1000</a>. (A portion of) These data were produced by the
            US Department of Energy Joint Genome Institute (<a href="https://ror.org/04xm1d337">https://ror.org/04xm1d337</a>)
            operated under Contract No. DE-AC02-05CH11231 in collaboration with the user community. GOLD data is shown as provided and is
            subject to the <a href="https://jgi.doe.gov/disclaimer/">JGI disclaimer</a>, which gives no warranty of its accuracy or
            completeness. Its use here does not imply endorsement by JGI or the Department of Energy.
          </p>
          <p class="about-tiles-title"><a href="https://gold.jgi.doe.gov/">GOLD project IDs found in this database</a></p>
          <dl class="metalog-tiles">
            <div v-for="tile in gold_tiles" :key="tile.key" :class="{ 'is-total': tile.key === 'runs' }">
              <dt>{{ tile.label }}</dt>
              <dd>{{ tile.value }}</dd>
            </div>
          </dl>
        </div>
      </details>

      <details id="indicpiper" class="about-detail">
        <summary><h3 class="title is-5">IndicPiper habitat indicators</h3></summary>
        <div class="about-detail-body">
          <p>
            <a href="https://github.com/cliffbueno/IndicPiper">IndicPiper</a>, by <i>Cliff Bueno de Mesquita</i>, identifies GTDB genera
            that are strong indicators of particular habitats. It uses established ecological methods of indicator “species” analysis
            (indicspecies:multipatt, IndVal), but the indicators are genera rather than species. Sandpiper does not run this analysis itself:
            it uses IndicPiper's own curated, published indicator database as-is. In the current version of IndicPiper ({{ INDICPIPER_VERSION }}), {{ INDICATOR_GENUS_COUNT }} genera
            were flagged as indicators of one of {{ HABITAT_COUNT }} habitats, each with a resampling-stability score from 100 runs of the analysis.
            Each habitat corresponds to one or more BioSample “organism” values (shown without the “ metagenome” suffix):
          </p>
          <table class="table is-narrow indicpiper-habitat-table">
            <thead><tr><th>IndicPiper habitat</th><th>“organism” BioSample values</th><th>Indicator genera</th></tr></thead>
            <tbody>
              <tr v-for="row in INDICPIPER_HABITATS" :key="row.habitat">
                <td>{{ row.habitat }}</td>
                <td class="organism-values">{{ row.organisms.join(', ') }}</td>
                <td>{{ (indicatorGenera[row.habitat] || []).length }}</td>
              </tr>
            </tbody>
          </table>
          <p>
            The full list of indicator genera for each habitat, with their IndVal and stability statistics, is in the
            <a href="https://github.com/cliffbueno/IndicPiper">IndicPiper GitHub repository </a>
            <b>(genus_habitat_indicators_v{{ INDICPIPER_VERSION }}.csv)</b>.
          </p>
          <p>
            Importantly, the total relative abundance of indicator genera differs between habitats. For instance, human vaginal samples are
            mostly made up of indicator genera, while indicator genera are the minority in soil samples. A low indicator fraction does not by
            itself mean a sample is misannotated. Organism labels outside the table, such as “canine gut metagenome”, are not matched to a habitat.
          </p>
          <p>
            Indicator genera were defined from Sandpiper {{ INDICATORS_DEFINED_FROM }} community profiles. This site applies that fixed set of genera to the current
            Sandpiper profiles, which use an updated profiling algorithm. For every run in this database, we compute how strongly its own genus
            composition matches each of the {{ HABITAT_COUNT }} habitat signatures, as the summed relative abundance of that habitat's indicator genera present in the sample.
          </p>
          <p>
            These scores are shown under "IndicPiper habitat indicators" within each Run page, and can
            be searched directly via the indicpiper key in
            <router-link :to="{ name: 'Search' }">advanced search</router-link>. Only habitats with a
            real, non-zero match are shown for a given run most runs match a handful of habitats.
            Triangles above and below each habitat's bar mark the average for all the runs recorded as that habitat
            (runs with no indicator genus for it count as zero), and the Statistics page charts these same averages for every habitat.
            Add a comparison after the habitat name (e.g. soil>=0.1) to threshold on
            that habitat's score itself, rather than only matching runs where it's present at all. A
            comparison with no habitat name, e.g. >0.5, matches runs whose single
            strongest habitat match exceeds that value, whichever habitat it turns out to be.
          </p>
          <p>
            The <router-link :to="{ name: 'Statistics' }">Statistics page</router-link> provides an overview of IndicPiper on Sandpiper.
            The IndicPiper <a href="https://github.com/cliffbueno/IndicPiper">bioRxiv preprint</a> describes the method in full, including how likely
            misannotated metagenomes are excluded.
          </p>
        </div>
      </details>
      </div>
    </section>

    <section id="changelog" class="section about-section">
      <div class="container">
      <h2 class="title is-3 about-heading">Changelog</h2>
      <div class="about-body">
        <p>Note that point releases (e.g. v2.0.x, v2.1.x) may not be listed here, and are only for minor bug/deployment fixes.</p>
      </div>
      <details v-for="(entry, index) in CHANGELOG" :key="entry.heading + (entry.version || '')" class="log-entry" :open="index < 1">
        <summary>
          <h3 class="title is-5 log-heading">{{ entry.heading }}</h3>
          <span v-if="index === 0 && !entry.released" class="log-badge">Current</span>
          <span v-if="entry.released" class="log-meta">{{ entry.released }}</span>
          <span v-if="entry.runs" class="log-meta">{{ entry.runs.toLocaleString('en-US') }} runs</span>
        </summary>
        <div class="content log-body" v-html="entry.html"></div>
      </details>
      </div>
    </section>

    <section id="acknowledgements" class="section about-section">
      <div class="container">
      <h2 class="title is-3 about-heading">Acknowledgements</h2>
      <div class="about-body">
        <p>Development of Sandpiper and SingleM was funded through Australian Research Council Future Fellow (#FT210100521), Discovery Project (#DP230101171) and Discovery Early Career Research Award (#DE160100248) grants, as well as the <a href="https://emerge-bii.github.io/">EMERGE</a> National Science Foundation (NSF) Biology Integration Institute (#2022070) and Genomic Science Program of the United States Department of Energy (DOE) Office of Biological and Environmental Research (BER), grants DE-SC0004632, DE-SC0010580 and DE-SC0016440. Cloud computing was generously contributed by Amazon Web Services (AWS) and Google Cloud (GCP).</p>
        <p>The sandpiper background image on the front page was derived from <a href="https://www.flickr.com/photos/snarfel/11631543856/in/pool-birds_birds_birds">Frans Vandewalle</a> (CC-NC).</p>
      </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.indicpiper-habitat-table { margin-bottom: var(--space-4); table-layout: fixed; width: 100%; max-width: 42rem; }
.indicpiper-habitat-table th:first-child { width: 28%; }
.indicpiper-habitat-table th:last-child { width: 6.5rem; }
.indicpiper-habitat-table td { overflow-wrap: anywhere; vertical-align: top; }
.organism-values { white-space: normal; }
.about-header { padding-bottom: var(--space-4); }
.about-header .container { text-align: center; }
.about-logo {
  width: min(400px, 100%);
  height: auto;
  margin: 0 auto var(--space-6);
}
.about-logo :deep(img) {
  width: 100%;
  height: auto;
}
.about-title { margin-bottom: var(--space-2); }
.about-lede { max-width: 70ch; margin: 0 auto; font-size: 1.1rem; line-height: 1.5; color: var(--color-ink-muted); }

/* A little air above a jumped-to section. */
.about-page .section[id], .about-page .about-detail[id] { scroll-margin-top: var(--space-4); }

.about-section { padding-top: var(--space-8); padding-bottom: var(--space-4); }
.about-heading { margin-bottom: var(--space-4); }
.about-body p, .about-detail-body p { line-height: 1.65; text-align: justify; text-justify: inter-word; }
@media (max-width: 768px) {
  .about-body p, .about-detail-body p { text-align: left; }
}
.about-body p + p, .about-body p + .content, .about-body .content + p, .about-detail-body p + p { margin-top: var(--space-4); }
.about-body .content { margin-top: var(--space-2); }

.about-people {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-6);
  margin: var(--space-4) 0;
  padding: 0;
  list-style: none;
}
.about-people li { font-weight: 500; }

.workflow-figure { margin: var(--space-6) 0; }
.workflow-figure img { display: block; width: 100%; max-width: 1100px; height: auto; margin: 0 auto; }
.workflow-figure figcaption { max-width: 62ch; margin: var(--space-2) auto 0; font-size: 0.85rem; text-align: center; color: var(--color-ink-muted); }
.workflow-figure a:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 3px; }

.about-detail-tools { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2) var(--space-3); margin: var(--space-8) 0 var(--space-2); }
.about-detail-tools-title { margin-right: var(--space-2); font-weight: 700; color: var(--color-ink); }

.about-detail, .log-entry { border-top: 1px solid var(--color-rule); }
.about-detail:last-of-type, .log-entry:last-of-type { border-bottom: 1px solid var(--color-rule); }
.about-detail summary, .log-entry summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1) var(--space-3);
  padding: var(--space-3) 0;
  cursor: pointer;
  list-style: none;
}
.about-detail summary::-webkit-details-marker, .log-entry summary::-webkit-details-marker { display: none; }
.about-detail summary::before, .log-entry summary::before {
  content: '';
  flex: none;
  width: 0.5rem;
  height: 0.5rem;
  border-right: 2px solid var(--color-ink-muted);
  border-bottom: 2px solid var(--color-ink-muted);
  transform: rotate(-45deg);
  transition: transform 0.15s;
}
.about-detail[open] > summary::before, .log-entry[open] > summary::before { transform: rotate(45deg); }
.about-detail summary:focus-visible, .log-entry summary:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.about-detail summary .title, .log-entry summary .title { flex: 1 1 0; min-width: 0; margin: 0; }
.log-entry summary .title { flex: none; }
.about-detail-body { padding: 0 0 var(--space-4) calc(0.5rem + var(--space-3)); }
.log-body { padding: 0 0 var(--space-4) calc(0.5rem + var(--space-3)); text-align: left; }
.log-badge { padding: 0 var(--space-2); font-size: 0.8rem; font-weight: 600; color: var(--color-surface); background: var(--color-accent); border-radius: var(--radius-bar, 4px); }
.log-meta { font-size: 0.85rem; color: var(--color-ink-muted); }

.about-tiles-title { margin-top: var(--space-4); font-weight: 600; }
.metalog-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(7.5rem, 1fr)); gap: var(--space-3); margin-top: var(--space-2); }
.metalog-tiles > div { padding: var(--space-3); border: 1px solid var(--color-rule); border-radius: var(--radius-bar, 4px); }
.metalog-tiles > div.is-total { border-color: var(--color-ink-muted); }
.metalog-tiles dt { font-size: 0.85rem; color: var(--color-ink-muted); }
.metalog-tiles dd { font-size: 1.3rem; font-weight: 600; font-variant-numeric: tabular-nums; color: var(--color-ink); }
.about-note { margin-top: var(--space-2); font-size: 0.85rem; color: var(--color-ink-muted); }
/* An example search typed in the Advanced Search: a plain grey box, in the text and in the changelog (v-html). */
.about-page :deep(.query-box) { padding: 0.05em 0.4em; border-radius: var(--radius-bar, 4px); background: color-mix(in srgb, var(--color-ink) 10%, transparent); color: inherit; font-size: inherit; white-space: nowrap; }

@media (min-width: 1440px) {
  /* Content is capped at 1152px (Bulma's widescreen width) so the contents list (PageRail) fits beside it
     on laptop screens; wider screens just get wider gutters. */
  .about-page :deep(.container:not(.page-rail-inner)) { max-width: 1152px; }
}
@media (prefers-reduced-motion: reduce) {
  .about-detail summary::before, .log-entry summary::before { transition: none; }
}
</style>

<script>
import { fetchSandpiperStats } from '@/api'
import { stopPageLoading } from '@/store/pageLoading'
import { METALOG_LAST_UPDATE, METALOG_SAMPLE_COUNTS, metalogCount } from '@/constants/metalog'

// The Changelog shown below, newest first. The Statistics page imports this
// same list for its version history, so adding an entry here updates both.
//
// heading   the title shown on the About page
// version   the version name on the Statistics page (the heading when absent)
// gtdb, globdb
//           the taxonomy database release, only where that version's changelog
//           used by that version. Left out when it is not known (GlobDB before v1.1.*).
// metalog, indicpiper
//           optional. The date the Metalog data was collected (e.g. '3rd March, 2026'), and the IndicPiper
//           database version, for a version that is no longer the live build. The newest
//           version takes both from the API, so they need not be set for it.
// released, date (YYYY-MM-DD, or YYYY-MM when only the month is known), runs
//           optional. An entry with a date and a run count is also drawn on the
//           Statistics page's metagenomes-over-time graph.
// html      the changelog list, shown as written
export const CHANGELOG = [
  {
    heading: '2.2.*',
    version: 'v2.2.0',
    gtdb: 'R232',
    globdb: 'R232',
    indicpiper: '2.1.0',
    // When the GOLD (JGI) records were retrieved for this build, in the form the Metalog collected date is shown.
    gold: '11 November 2026',
    released: 'Novemeber 10th, 2026',
    date: '2026-10-11',
    runs: 926082,
    html: `<ul>
        <li><strong>Profiling</strong>
          <ul>
            <li>Addition of Weebill profiles to each run. Weebill matches reads against whole reference genomes, so more of each community is assigned to named species, which raises the known species fraction (see the Statistics page). This increases the total number of metagenomes screened within Sandpiper from 913,071 -> 926,082</li>
            <li>Addition of <a href="https://github.com/cliffbueno/IndicPiper">IndicPiper</a> habitat indicators within each Run page, showing how strongly a sample's genus composition matches known habitat signatures (a caution message is shown if the environment signatures do not match the documented environment).</li>
            <li>Addition to the Sunburst model. Users can search for specific taxa, which are then highlighted. In a breadcrumb fashion the Sunburst can be collapsed with a reset view and a 'go back a step' option in the centre.</li>
            <li>Addition of a new sample abundance graph with zoom and filter functionality.</li>
          </ul>
        </li>
        <li><strong>Run pages</strong>
          <ul>
            <li>Run pages now display pills that highlight important information about the run, including a "Weebill only" pill for runs where SingleM found no marker genes and the profile comes from Weebill alone.</li>
            <li>The sample location map on Run pages now opens as a flat map that draws every country at its true relative size (Equal Earth projection), so areas can be compared fairly, with countries and oceans named. A Globe option shows the same place on a globe with a Map or Satellite picture, which uses free, keyless map data from <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> <a href="https://openfreemap.org/">(OpenFreeMap)</a> and <a href="https://s2maps.eu">Sentinel-2 cloudless</a> imagery by <a href="https://eox.at">EOX IT Services GmbH</a> (contains modified Copernicus Sentinel data 2021). Both views have + and − buttons, Sample and World buttons, and zoom with Ctrl (⌘ on a Mac) and scroll or pinch.</li>
            <li>The map on Project pages matches: a flat true-size map by default and a Globe option, with numbered markers that merge nearby places, a list of the runs at a place when hovered or clicked, and an All runs button that fits every run on screen.</li>
            <li>Publications at the top of each Run page now also include papers recorded by <a href="https://metalog.embl.de/">Metalog</a> (shown as green pills), alongside NCBI's and GOLD's. A paper already listed is not repeated.</li>
            <li>The Taxonomic profile section states which methods built the selected profile: GTDB combines SingleM and Weebill, GlobDB uses SingleM only (so Weebill-only runs have no GlobDB profile).</li>
            <li>Addition of <a href="https://metalog.embl.de/">Metalog</a> within each Run page. Contains additional metadata that is not present within NCBI. Metalog rows within the Sample Information section are green.</li>
            <li>Addition of <a href="https://gold.jgi.doe.gov/">GOLD (JGI)</a> metadata and publications within each Run page for samples sequenced by JGI. GOLD rows within the Sample Information section are gold, publications linked by GOLD appear as gold pills, and an information button explains the source. GOLD's records are downloaded once and stored in the database, so Run pages show them without waiting for JGI. The About page has a new GOLD (JGI) section, including how many runs and projects have GOLD data.</li>
            <li>The Metalog and GOLD details for a run can be downloaded together as the Additional Run Metadata CSV.</li>
            <li>Metadata on each Run page has a coloured stripe beside the field name showing whether it differs from other runs: green = different value, grey = different but expected (IDs, sizes etc.), yellow = only this run has the entry. NCBI fields are compared with the other runs of the BioProject, and GOLD fields with the related runs of the same study.</li>
            <li>Filter fields within the Sample Information section by source (Metalog, GOLD, NCBI-defined or custom attributes) or by how they differ from other runs.</li>
            <li>On each Run page, users can continue searching without returning to the search page, via a dropdown search bar.</li>
            <li>A check compares a run's recorded Geo loc name with its latitude and longitude. When the coordinates fall in a different country, a caution panel opens at the top of Sample information and the map is flagged, because the coordinates may be wrong. Samples at sea or on small islands are not flagged.</li>
          </ul>
        </li>
        <li><strong>Advanced search</strong>
          <ul>
            <li>Addition of an Advanced Search bar option. Users type a search query as comma-separated key: value pairs (for example "country: Australia, year: 2010-2015"), with suggestions and autocompletion as they type, and see the number of samples detected before jumping to a random sample.</li>
            <li>Explore tabled results takes the query to a table of every matching run.</li>
            <li>A List of keys on the search page lists every available key, grouped as Keywords, Location, Sample, Quality / Size, Sequencing, Taxonomy, Study, Identifiers, Submitter and Metadata, each with an example. Information buttons beside the keys that need more help (age, habitat, platform, instrument, library strategy, organism, taxonomy, Metadata, Metalog and GOLD (JGI)) show their allowed values or how they are searched.</li>
            <li>The Query Syntax guide covers ranges (2-10), greater and less than (&gt;10, &gt;=10, &lt;10, &lt;=10) and exact or approximate values (10).</li>
            <li>The advanced options form offers the same fields as inputs, including location (country, location, latitude, longitude and grid squares on the map), dates, quality, sequencing, study and metadata. Fields have an Any option that matches every run with a value recorded.</li>
            <li>A Weebill only field (<span class="query-box">weebill_only: yes</span> or <span class="query-box">no</span>) finds runs whose profile was made by Weebill alone.</li>
            <li>A GOLD (JGI) field finds runs by GOLD project ID, or every run with GOLD data when left empty. As with Metalog, any GOLD field can be searched, either as plain text across every field or as <code>field=value</code> (for example <span class="query-box">gold: habitat=marine</span>); the help button lists every field.</li>
            <li>On the location map, the area of each circle now follows the square root of the number of runs, so small and large groups are both easy to read.</li>
          </ul>
        </li>
        <li><strong>Statistics page</strong> (new), displaying database-wide information:
          <ul>
            <li>Runs by release year, and sequencing depth by release year, shown on a square-root scale so both shallow and very deep runs are readable.</li>
            <li>Time from collection to release, in years, for host-associated and ecological samples, drawn from the runs whose collection date is recorded to the day.</li>
            <li>Types of sample (host-associated, ecological and unclassified).</li>
            <li>Where samples were collected, on a map of hexagons whose colour shows how many runs fall in each. Hovering a hexagon also highlights its latitude band.</li>
            <li>Most widely detected taxa, which can be shown for all runs, host-associated runs or ecological runs, or for one group such as pig, human, soil or marine.</li>
            <li>Information coverage: location, Metalog, GOLD (JGI), IndicPiper and low complexity. The IndicPiper bar is split into runs with and without a warning.</li>
            <li>Known species fraction by release year, for all runs and separately for host-associated samples (human and mouse split into gut and non-gut) and ecological samples. A simple linear model fitted to the trend is extended forward to estimate when the fraction would reach 100%.</li>
            <li>Prokaryotic fraction, known species fraction and average genome size by group, for host-associated and ecological samples.</li>
            <li>Phylum composition by group.</li>
            <li>IndicPiper indicator genera by habitat: the average indicator abundance and the average number of indicator genera per run, for the runs recorded as each habitat.</li>
            <li>Comparison between versions of Sandpiper.</li>
            <li>Hovering over a line highlights it, and clicking it (or its legend entry) dims the others; click again to undo. Legends show run counts, are sorted by number of runs, and read down in columns.</li>
            <li>Every chart on the Statistics page can be downloaded as an SVG or PNG image. The download keeps any highlighted or selected lines, so the image matches what is on screen.</li>
          </ul>
        </li>
      </ul>`
  },
  {
    heading: '2.1.*',
    version: 'v2.1.1',
    gtdb: 'R232',
    globdb: 'R232',
    released: 'July 10th, 2026',
    date: '2026-07-10',
    runs: 913071,
    html: `<ul>
        <li>Integration of <a href="https://globdb.org/">GlobDB</a> R232 community profiles.</li>
        <li>Updated GlobDB database reference R226 -> R232.</li>
        <li>Fixed environmental viral metagenomes incorrectly labeled "host-associated" due to NCBI's labelling "Organismal".</li>
        <li>Taxonomy page now has a Shuffle button, letting users randomise the order of sample results.</li>
        <li>Total metagenomes screened -> 913,071. Down 94 due to redacted SRA data from NCBI (Error 404).</li>
        <li>NPM update</li>
        <li>New information present within each Run page, under *Derived information*:</li>
        <ul>
          <li>Non-metagenome organism (Strict/Loose): Samples flagged true when the organism name recorded in NCBI names a specific species rather than a metagenome or a community (for example 'Homo sapiens' or 'Escherichia coli'). The sample may be an isolate or a single genome, or a community deposited under its host's name; the flag is judged from the recorded name only, not from the reads. Loose additionally includes vague placeholder names like 'bacterium', 'unidentified', etc.</li>
          <li>Synthetic: Samples flagged true when the organism name contains 'synthetic' or 'simulat' (simulated/simulation), or the BioSample library source is recorded as SYNTHETIC.</li>
          <li>RNA / non-DNA (Strict/Loose): Samples flagged true when the sequencing library strategy or BioSample library source indicate RNA or other non-DNA metadata related information.</li>
          <li>Domain-only (GTDB, GlobDB, or both): Derived from the condensed taxonomic profiles; samples flagged true where the condensed taxonomic profile did not resolve below domain-level classification.</li>
        </ul>
      </ul>`
  },
  {
    heading: 'v2.0.*',
    version: 'v2.0.0',
    gtdb: 'R232',
    globdb: 'R226',
    released: 'May 26th, 2026',
    date: '2026-05-26',
    runs: 913165,
    html: `<ul>
        <li>Integration of <a href="https://gtdb.ecogenomic.org/">GTDB</a> R232 community profiles.</li>
        <li>Addition of low complexity flags to samples (True/False).</li>
        <li>Random search now has the ability to exclude low complexity samples.</li>
        <li>Within sequencing information, top order fraction is now displayed on each sample's page.</li>
        <li>Within taxonomy search, a new slider allows toggling the visibility of low complexity flagged samples. When active, the distribution of low complexity flagged entries is exluded from the table.</li>
        <li>Additional public metagenomes analysed = 205,695, total metagenomes screened -> 913,165.</li>
        <li>Metadata annotations procured using Kingfisher on 14th May, 2026. Raw metagenomes up to 3rd March, 2026 were screened.</li>
        <li>Version numbers are now shown for all database references (e.g. GTDB R232, GlobDB R226).</li>
        <li>Database buttons are now greyed out and marked as unavailable when a sample has no data in that database (e.g. sample available in newer R232 GTDB database but not older R226 GlobDB database). </li>
      </ul>`
  },
  {
    heading: 'v1.1.*',
    released: 'November 21st, 2025',
    date: '2025-11-21',
    gtdb: 'R226',
    globdb: 'R226',
    html: `<ul>
        <li>Integration of <a href="https://globdb.org">GlobDB</a> R226 community profiles.</li>
        <li>Latitude, longitude and other metadata for taxon search results can now be downloaded.</li>
        <li>Website infrastructure upgraded.</li>
        <li>OTU tables can no longer be downloaded from Sandpiper.</li>
        <li>Metadata annotations for each run procured using <a href="https://github.com/wwood/kingfisher-download/">Kingfisher</a> on 27 August, 2025.</li>
        <li>(No new public metagenomes were analysed since the previous release).</li>
      </ul>`
  },
  {
    heading: 'v1.0.*',
    version: 'v1.0.0',
    gtdb: 'R226',
    released: 'April 17th, 2025',
    date: '2025-04-17',
    runs: 707470,
    html: `<ul>
        <li>Raw metagenomes up to 20 Feb 2025 scanned using SingleM 'pipe' version 0.18.3. Metagenomes included in the previous version were scanned from scratch, for better detection of lineages using translation table 4, and a very minor improvement in novel species detection.</li>
        <li>Taxonomic annotations, profiles and SMF values updated to use GTDB R226 (metapackage S5.4.0.GTDB_r226.metapackage_20250331.smpkg), using a development version conceptually identical to SingleM renew v0.18.3.</li>
        <li>Metadata annotations for each run procured using <a href="https://github.com/wwood/kingfisher-download/">Kingfisher</a> on 14 April, 2025.</li>
        <li>Email addresses of contacts are sometimes available. To prevent spam of submitters, they are hidden by default but can be revealed by human interaction (via reCAPTCHA).</li>
        <li>Minor improvements to the website. The download button of taxonomy search results now includes latitude and longitude of each sample where the taxon is detected.</li>
      </ul>`
  },
  {
    heading: 'v0.3.0',
    version: 'v0.3.0',
    gtdb: 'R220',
    released: 'June 7th, 2024',
    date: '2024-06-07',
    runs: 295598,
    html: `<ul>
        <li>Update profiles to use GTDB R220, generated using SingleM renew v0.17.0.</li>
      </ul>`
  },
  {
    heading: 'v0.2.2',
    released: 'February 2024',
    date: '2024-02',
    gtdb: 'R214',
    html: `<ul>
        <li>NPM package updates.</li>
      </ul>`
  },
  {
    heading: 'v0.2.1',
    released: 'January 2024',
    date: '2024-01',
    gtdb: 'R214',
    html: `<ul>
        <li>Added links to bulk download of condensed profiles.</li>
      </ul>`
  },
  {
    heading: 'v0.2.0',
    released: 'December 2023',
    date: '2023-12',
    gtdb: 'R214',
    html: `<ul>
        <li>Updated to use SingleM 0.16.0, changing the species assignment and "condense" procedures</li>
        <li>Added "SPF" (SingleM Prokaryotic Fraction) statistics, previously known as "SMF" / SingleM Microbial Fraction</li>
        <li>Community profile and SPF data: originally generated from SRA metadata collected Dec 15, 2021, using git commit of SingleM e97d171 and metapackage 'S3.metapackage_20211101.smpkg. Then renewed with SingleM v0.16.0 using metapackage S3.2.1.GTDB_r214.metapackage_20231006.smpkg.</li>
        <li>Community profiles can be downloaded in bulk from <a href="https://zenodo.org/doi/10.5281/zenodo.10547493">Zenodo</a>.</li>
      </ul>`
  }
]

// The jump bar's sections, in page order; each id is on that section's element.
const JUMP_ITEMS = [
  { id: 'team', label: 'Team' },
  { id: 'citations', label: 'Citations' },
  { id: 'bulk-download', label: 'Bulk download' },
  { id: 'how-built', label: 'How it was built' },
  { id: 'weebill', label: 'Details' },
  { id: 'changelog', label: 'Changelog' },
  { id: 'acknowledgements', label: 'Acknowledgements' }
]

const JUMP_LINE_FRACTION = 0.33
const PIN_RELEASE_EVENTS = ['wheel', 'touchmove', 'keydown']

const METALOG_TILES = [
  { key: 'human', label: 'Human' },
  { key: 'animal', label: 'Animal' },
  { key: 'ocean', label: 'Ocean' },
  { key: 'environmental', label: 'Environmental' },
  { key: 'total', label: 'Total' }
]

export default {
  name: 'About',
  components: { PageRail },
  title: 'About - Sandpiper',
  data: function () {
    return {
      CHANGELOG,
      JUMP_ITEMS,
      METALOG_TILES,
      current_section: null,
      pinned_section: null,
      num_terrabases: null,
      num_runs: null,
      num_bioprojects: null,
      version: null,
      scrape_date: null,
      metalog_retrieved_date: null,
      // Metalog's own published release, as recorded when the data was
      // fetched. Null until the stats call returns, and on databases built
      // before this was captured -- the computeds below fall back then.
      metalog_release: null,
      // Runs and projects carrying a GOLD project ID, counted when the database was generated.
      gold_counts: null
    }
  },

  computed: {
    gold_tiles () {
      const counts = this.gold_counts
      const share = counts && this.num_runs ? (100 * counts.runs / this.num_runs).toFixed(1) + '%' : '—'
      return [
        { key: 'runs', label: 'Runs with GOLD data', value: metalogCount(counts?.runs) },
        { key: 'projects', label: 'GOLD projects', value: metalogCount(counts?.projects) },
        { key: 'stored', label: 'Projects with a GOLD record', value: metalogCount(counts?.stored) },
        { key: 'publications', label: 'Projects with publications', value: metalogCount(counts?.publications) },
        { key: 'share', label: 'Share of all runs', value: share }
      ]
    },

    metalog_last_update () {
      return this.metalog_release?.last_metadata_update || METALOG_LAST_UPDATE
    },

    metalog_sample_counts () {
      const counts = this.metalog_release?.sample_counts || METALOG_SAMPLE_COUNTS
      return Object.fromEntries(
        Object.entries(counts).map(([category, value]) => [category, metalogCount(value)])
      )
    }
  },
  created () {
    // The template has no data gate -- the page renders immediately.
    stopPageLoading()
    this.fetchData()
  },
  mounted () {
    this.observeSections()
  },
  beforeUnmount () {
    this.unobserveSections()
  },
  methods: {
    fetchData () {
      fetchSandpiperStats()
        .then(response => {
          const r = response.data
          this.num_terrabases = r.num_terrabases
          this.num_runs = r.num_runs
          this.num_bioprojects = r.num_bioprojects
          this.version = r.version
          this.scrape_date = r.scrape_date
          this.gtdb_version = r.gtdb_version
          this.metalog_retrieved_date = r.metalog_retrieved_date
          this.metalog_release = r.metalog_release
          this.gold_counts = r.gold_counts || null
        })
    },

    // Glides to a section (instant when the reader prefers reduced motion), opening it
    // first when it is a collapsed block. A section near the page end can't scroll up
    // to the top, so the click's choice is held as current until the reader scrolls by hand.
    jumpTo (id) {
      const target = document.getElementById(id)
      if (!target) return
      if (target.tagName === 'DETAILS') target.open = true
      const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      this.pinned_section = id
      this.current_section = id
      target.scrollIntoView({ behavior: still ? 'auto' : 'smooth', block: 'start' })
    },

    setDetails (open) {
      document.querySelectorAll('.about-detail').forEach(block => { block.open = open })
    },

    // The current section is the last one whose top has passed a line a third of the
    // way down the window. At the very bottom of the page the last section takes over,
    // unless a jump-bar click pinned another one.
    updateCurrentSection () {
      if (this.pinned_section) return
      const line = window.innerHeight * JUMP_LINE_FRACTION
      let current = null
      JUMP_ITEMS.forEach(item => {
        const el = document.getElementById(item.id)
        if (el && el.getBoundingClientRect().top <= line) current = item.id
      })
      const atEnd = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2
      if (atEnd) current = JUMP_ITEMS[JUMP_ITEMS.length - 1].id
      if (current) this.current_section = current
    },

    releasePin () {
      if (this.pinned_section) {
        this.pinned_section = null
        this.updateCurrentSection()
      }
    },

    observeSections () {
      this.unobserveSections()
      window.addEventListener('scroll', this.updateCurrentSection, { passive: true })
      window.addEventListener('resize', this.updateCurrentSection, { passive: true })
      // Hand input (not the smooth scroll a click starts) releases the pin.
      PIN_RELEASE_EVENTS.forEach(ev => window.addEventListener(ev, this.releasePin, { passive: true }))
      this.updateCurrentSection()
    },

    unobserveSections () {
      window.removeEventListener('scroll', this.updateCurrentSection)
      window.removeEventListener('resize', this.updateCurrentSection)
      PIN_RELEASE_EVENTS.forEach(ev => window.removeEventListener(ev, this.releasePin))
    },

    decode (a) {
      // ROT13 : a Caesar cipher
      // letter -> letter' such that code(letter') = (code(letter) + 13) modulo 26
      return a.replace(/[a-zA-Z]/g, function(c){
        return String.fromCharCode((c <= "Z" ? 90 : 122) >= (c = c.charCodeAt(0) + 13) ? c : c - 26);
      })
    }
  },
  watch: {
    // call again the method if the route changes
    $route: 'fetchData'
  }
}
</script>
