// Single source of truth for the universal search bar's `key: value` syntax:
// every key name, its aliases, which "List of Keys" group it belongs to, and
// -- for fields with a small enough set of real values -- that set itself.
//
// This replaces two things that used to drift independently: Search.vue's
// hand-written ADVANCED_KEY_MAP/ADVANCED_GROUP_FIELDS, and the hand-typed
// value lists duplicated across App.vue's and Search.vue's "List of Keys"
// tooltips. It also feeds the autocomplete dropdown (useSearchAutocomplete).
//
// `values` counts and `liveField` targets were verified against
// sandpiper_40.duckdb directly (ncbi_metadata / parsed_sample_attributes /
// indicator_habitat_scores), not guessed -- see the counts inline. Two real
// data-quality findings came out of that verification, kept as comments
// rather than silently "fixed" in the data itself:
//   - platform's "Illumina" (108 rows) is a rare submitter-casing variant of
//     "ILLUMINA" (912,954 rows); the backend's `ilike` match already treats
//     them the same, so they're folded into one display entry here.
//   - habitat previously showed ~25 values in the UI, but
//     indicator_habitat_scores only contains 13 real habitats (IndicPiper's
//     `multipatt()` analysis was trained on exactly 13) -- the other ~12
//     ("activated sludge", "chicken gut", "hot springs", ... ) never match
//     any run. This file lists only the 13 that exist.

export interface SearchFieldValue {
  value: string
  count: number
}

export interface SearchFieldDef {
  key: string
  aliases: string[]
  group: string
  example: string
  /** Small, stable value set -- ranked by count (descending) in the autocomplete. */
  values?: SearchFieldValue[]
  /**
   * High-cardinality field with a live backend suggestion source.
   * 'taxonomy' is a reserved marker for the existing /taxonomy_search_hints
   * endpoint (no count returned); every other value names the <field> path
   * segment for the generalized /search_field_values/<field>/<query> endpoint.
   */
  liveField?: string
  /**
   * `continent` round-trips through the query string but has no input in
   * the Advanced options panel (no `adv.continent`) -- keeping it out of
   * ADVANCED_GROUP_FIELDS is what the original hand-written map did, so a
   * collapsed group's "N set" count / auto-expand check (which reads
   * `adv[field]`) never looks up a field that doesn't exist.
   */
  excludeFromGroupFields?: boolean
}

export const SEARCH_GROUPS: Record<string, string> = {
  keywords: 'Keywords',
  location: 'Location',
  sample: 'Sample',
  quality: 'Quality / Size',
  sequencing: 'Sequencing',
  taxonomy: 'Taxonomy',
  study: 'Study',
  identifiers: 'Identifiers',
  submitter: 'Submitter',
  metadata: 'Metadata',
}

export const SEARCH_FIELDS: SearchFieldDef[] = [
  // --- Keywords ---
  // Comma-separated phrases; each must appear in the title, abstract, location,
  // organism or a study/BioProject accession of the same sample.
  { key: 'keywords', aliases: [], group: 'keywords', example: 'e.g. "sponge reef, coral"' },

  // --- Location ---
  { key: 'country', aliases: [], group: 'location', example: 'e.g. Australia', liveField: 'country' },
  { key: 'continent', aliases: [], group: 'location', example: 'e.g. Oceania', excludeFromGroupFields: true },
  { key: 'location', aliases: ['geo'], group: 'location', example: 'e.g. Pacific Ocean', liveField: 'location' },
  { key: 'latitude', aliases: ['lat'], group: 'location', example: 'e.g. -33.8 or -40-30' },
  { key: 'longitude', aliases: ['lon'], group: 'location', example: 'e.g. 151.2 or 140-160' },
  // Squares picked on the map: semicolon-separated south-west corners, see utils/grid.ts.
  { key: 'grid', aliases: ['graph'], group: 'location', example: 'e.g. 10/-60;15/-60' },

  // --- Sample ---
  { key: 'year', aliases: [], group: 'sample', example: 'e.g. 2010 or 2010-2015' },
  { key: 'release_year', aliases: [], group: 'sample', example: 'e.g. 2018 or 2015-2020' },
  { key: 'temperature', aliases: ['temp'], group: 'sample', example: 'e.g. 25 or 20-30' },
  { key: 'depth', aliases: [], group: 'sample', example: 'e.g. 0-200' },
  {
    key: 'environment', aliases: ['env'], group: 'sample', example: 'host or ecological',
    // parsed_sample_attributes.host_or_not_mature: host 660,848 / ecological 234,889
    values: [
      { value: 'host', count: 660848 },
      { value: 'ecological', count: 234889 },
    ],
  },
  {
    key: 'low_complexity', aliases: [], group: 'sample', example: 'yes or no',
    values: [
      { value: 'no', count: 836050 },
      { value: 'yes', count: 77021 },
    ],
  },
  {
    key: 'synthetic', aliases: [], group: 'sample', example: 'yes or no',
    values: [
      { value: 'no', count: 908555 },
      { value: 'yes', count: 4516 },
    ],
  },
  {
    key: 'non_metagenome_organism', aliases: [], group: 'sample', example: 'yes or no',
    values: [
      { value: 'no', count: 843172 },
      { value: 'yes', count: 69899 },
    ],
  },
  {
    key: 'rna_or_non_dna', aliases: [], group: 'sample', example: 'yes or no',
    values: [
      { value: 'no', count: 900284 },
      { value: 'yes', count: 12787 },
    ],
  },
  { key: 'age', aliases: [], group: 'sample', example: 'e.g. 25 or 20-30' },
  {
    key: 'habitat', aliases: ['indicpiper'], group: 'sample', example: 'e.g. soil or soil>=0.1',
    // indicator_habitat_scores: count(distinct run_id) per habitat -- the
    // only 13 values that actually match (see file header).
    values: [
      { value: 'human oral', count: 509429 },
      { value: 'mammalian gut', count: 508568 },
      { value: 'human vaginal', count: 448625 },
      { value: 'wastewater', count: 238151 },
      { value: 'soil', count: 168287 },
      { value: 'phyllosphere', count: 162508 },
      { value: 'human skin', count: 133154 },
      { value: 'freshwater sediment', count: 127508 },
      { value: 'freshwater water', count: 126424 },
      { value: 'glacier', count: 109939 },
      { value: 'marine sediment', count: 73834 },
      { value: 'marine water', count: 39513 },
      { value: 'hydrothermal vent', count: 16009 },
    ],
  },

  // --- Quality / Size ---
  { key: 'spf', aliases: ['prokaryotic_fraction'], group: 'quality', example: 'e.g. 50-100 or >50' },
  { key: 'ksf', aliases: ['known_species_fraction'], group: 'quality', example: 'e.g. 70-100 or >70' },
  { key: 'gbp', aliases: ['bases', 'size'], group: 'quality', example: 'e.g. 2-10 or >2' },
  { key: 'reads', aliases: ['spots'], group: 'quality', example: 'e.g. 10-100 or >10' },
  { key: 'read_length', aliases: [], group: 'quality', example: 'e.g. 100-250 or >100' },

  // --- Sequencing ---
  {
    key: 'platform', aliases: [], group: 'sequencing', example: 'e.g. Illumina',
    // ncbi_metadata.platform: ILLUMINA 912,954 + Illumina 108 folded into one
    // display entry (see file header); Metagenomic 9 is a real but mislabeled
    // submitter value (a library type, not a platform).
    values: [
      { value: 'ILLUMINA', count: 913062 },
      { value: 'Metagenomic', count: 9 },
    ],
  },
  {
    key: 'instrument', aliases: ['model'], group: 'sequencing', example: 'e.g. HiSeq 2500',
    // ncbi_metadata.model, excluding "unspecified" (42,661) and junk
    // single-letter values ('S'/'T'/'G', 4 rows each) -- neither is a real
    // instrument name a user would search for.
    values: [
      { value: 'Illumina NovaSeq 6000', count: 400769 },
      { value: 'Illumina HiSeq 2500', count: 102228 },
      { value: 'Illumina HiSeq 4000', count: 65697 },
      { value: 'NextSeq 500', count: 61852 },
      { value: 'Illumina HiSeq 2000', count: 57969 },
      { value: 'Illumina MiSeq', count: 32223 },
      { value: 'HiSeq X Ten', count: 27933 },
      { value: 'Illumina NovaSeq X', count: 24885 },
      { value: 'NextSeq 2000', count: 20452 },
      { value: 'NextSeq 550', count: 20159 },
      { value: 'Illumina HiSeq 3000', count: 16272 },
      { value: 'Illumina NovaSeq X Plus', count: 14247 },
      { value: 'Illumina HiSeq X', count: 10428 },
      { value: 'Illumina HiSeq 1000', count: 4059 },
      { value: 'Illumina HiSeq 1500', count: 2977 },
      { value: 'NextSeq 1000', count: 1839 },
      { value: 'Illumina MiniSeq', count: 1463 },
      { value: 'Illumina Genome Analyzer IIx', count: 1307 },
      { value: 'Illumina Genome Analyzer II', count: 1158 },
      { value: 'Illumina Genome Analyzer', count: 1000 },
      { value: 'Illumina HiSeq X Ten', count: 541 },
      { value: 'HiSeq X Five', count: 446 },
      { value: 'Illumina HiScanSQ', count: 344 },
      { value: 'Illumina iSeq 100', count: 95 },
      { value: 'Nova seq', count: 42 },
      { value: 'MiSeq i100', count: 12 },
    ],
  },
  {
    key: 'library_strategy', aliases: ['strategy'], group: 'sequencing', example: 'e.g. WGS',
    // ncbi_metadata.library_strategy: exact match to all 34 distinct DB values.
    values: [
      { value: 'WGS', count: 757270 },
      { value: 'OTHER', count: 71234 },
      { value: 'AMPLICON', count: 35656 },
      { value: 'WGA', count: 24704 },
      { value: 'RNA-Seq', count: 12668 },
      { value: 'Targeted-Capture', count: 5625 },
      { value: 'POOLCLONE', count: 1275 },
      { value: 'WXS', count: 1137 },
      { value: 'WCS', count: 1043 },
      { value: 'Hi-C', count: 911 },
      { value: 'CLONE', count: 319 },
      { value: 'ChIP-Seq', count: 282 },
      { value: 'Bisulfite-Seq', count: 149 },
      { value: 'Synthetic-Long-Read', count: 117 },
      { value: 'RAD-Seq', count: 105 },
      { value: 'ATAC-seq', count: 75 },
      { value: 'CLONEEND', count: 73 },
      { value: 'Tn-Seq', count: 71 },
      { value: 'shotgun sequencing', count: 52 },
      { value: 'FAIRE-seq', count: 46 },
      { value: 'miRNA-Seq', count: 36 },
      { value: 'FL-cDNA', count: 36 },
      { value: 'DNase-Hypersensitivity', count: 35 },
      { value: 'CTS', count: 33 },
      { value: 'MRE-Seq', count: 31 },
      { value: 'FINISHING', count: 25 },
      { value: 'ssRNA-seq', count: 15 },
      { value: 'GBS', count: 14 },
      { value: 'EST', count: 14 },
      { value: 'RIP-Seq', count: 9 },
      { value: 'ncRNA-Seq', count: 5 },
      { value: 'Ribo-seq', count: 3 },
      { value: 'Tethered Chromatin Conformation Capture', count: 1 },
      { value: 'NOMe-Seq', count: 1 },
      { value: 'MBD-Seq', count: 1 },
    ],
  },

  // --- Taxonomy ---
  { key: 'organism', aliases: ['taxon_name'], group: 'taxonomy', example: 'e.g. marine metagenome', liveField: 'organism' },
  { key: 'taxonomy', aliases: [], group: 'taxonomy', example: 'e.g. s__Prochlorococcus', liveField: 'taxonomy' },

  // --- Study ---
  { key: 'study', aliases: ['study_title', 'title'], group: 'study', example: 'e.g. Tara Oceans', liveField: 'study' },
  { key: 'abstract', aliases: ['study_abstract'], group: 'study', example: 'e.g. coral reef' },
  { key: 'bioproject', aliases: [], group: 'study', example: 'e.g. PRJNA12345', liveField: 'bioproject' },

  // --- Identifiers ---
  { key: 'sra_study', aliases: ['sra'], group: 'identifiers', example: 'e.g. SRP012345' },
  { key: 'experiment', aliases: ['exp'], group: 'identifiers', example: 'e.g. SRX012345' },
  { key: 'sample_acc', aliases: ['sample'], group: 'identifiers', example: 'e.g. SRS012345' },
  { key: 'biosample', aliases: [], group: 'identifiers', example: 'e.g. SAMN12345' },

  // --- Submitter ---
  { key: 'organisation', aliases: ['organization'], group: 'submitter', example: 'e.g. MIT or Woods Hole', liveField: 'organisation' },

  // --- Metadata ---
  { key: 'attr', aliases: ['attribute', 'biosample_attr', 'metadata'], group: 'metadata', example: 'e.g. host=Sus scrofa' },
  { key: 'metalog', aliases: [], group: 'metadata', example: 'e.g. host=Sus scrofa or diabetes' },
]

export const ADVANCED_KEY_MAP: Record<string, string> = Object.fromEntries(
  SEARCH_FIELDS.flatMap(f => [[f.key, f.key], ...f.aliases.map(a => [a, f.key])])
)

export const ADVANCED_GROUP_FIELDS: Record<string, string[]> = SEARCH_FIELDS
  .filter(f => !f.excludeFromGroupFields)
  .reduce((acc, f) => {
    (acc[f.group] ||= []).push(f.key)
    return acc
  }, {} as Record<string, string[]>)

export function findSearchField (key: string): SearchFieldDef | undefined {
  const canonical = ADVANCED_KEY_MAP[key.toLowerCase().trim()]
  return canonical ? SEARCH_FIELDS.find(f => f.key === canonical) : undefined
}
