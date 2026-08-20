import axios from 'axios'

// Cannot set directly because different running locally (localhost:5000) and in production (sandpiper.qut.edu.au)
let API_URL = 'unset'
if (import.meta.env.PROD) {
  const raw = import.meta.env.VITE_API_URL
  // Allow raw to be passed already with scheme
  if (raw.startsWith('http://') || raw.startsWith('https://')) {
    API_URL = `${raw.replace(/\/$/,'')}/api`
  } else {
    // Use http for localhost or anything containing a port (internal docker host like api:5000)
    const hasPort = raw.includes(':')
    const useHttps = !raw.includes('localhost') && !hasPort
    API_URL = `${useHttps ? 'https' : 'http'}://${raw}/api`
  }
} else {
  API_URL = 'http://localhost:8090/api'
}

export function api_url () {
  return API_URL
}

export function fetchSandpiperStats () {
  return axios.get(`${API_URL}/sandpiper_stats`)
}

export function fetchRunMetadata (runId: string) {
  return axios.get(`${API_URL}/metadata/${runId}`)
}

export function fetchRunCondensed (runId: string, taxonomyType: string) {
  return axios.get(`${API_URL}/condensed/${runId}?taxonomy_type=${taxonomyType}`)
}

export function fetchProjectMetadata (model_bioproject: string) {
  return axios.get(`${API_URL}/project?model_bioproject=${model_bioproject}`)
}

// Niche Mapping filter values (pH, temperature, host association), applied
// server-side to the maps and table alike -- see NicheFilters usage below.
// Each axis is a single selected bucket value (or absent = "Any"), not a
// range: the sliders only ever offer values known to exist, from
// fetchTaxonomyNicheOptions below.
export interface NicheFilters {
  ph?: number
  temperature?: number
  hostAssociation?: string
  piperCommunity?: string
}

function nicheFilterParams (niche?: NicheFilters): Record<string, string | number> {
  if (!niche) return {}
  const params: Record<string, string | number> = {}
  if (niche.ph !== undefined) params.ph = niche.ph
  if (niche.temperature !== undefined) params.temperature = niche.temperature
  if (niche.hostAssociation) params.host_association = niche.hostAssociation
  if (niche.piperCommunity) params.piper_community = niche.piperCommunity
  return params
}

export interface NicheOptions {
  ph_options: number[]
  temperature_options: number[]
  host_association_options: string[]
  piper_community_options: string[]
}

export function fetchTaxonomyNicheOptions (taxonomy: string, taxonomyType: string, niche?: NicheFilters) {
  // Bucketed values actually present for this taxon, each computed against
  // whatever is currently selected on the *other* two axes -- backs the
  // cascading Niche Mapping sliders.
  return axios.get<NicheOptions>(`${API_URL}/taxonomy_niche_options/${taxonomy}`,
    { params: { taxonomy_type: taxonomyType, ...nicheFilterParams(niche) } })
}

export function fetchRunsByTaxonomy (
  taxonomy: string,
  taxonomyType: string,
  page: number,
  sortField: string,
  sortDirection: string,
  pageSize: number,
  excludeLowComplexity: boolean = true,
  // Map cluster to restrict to, as {lat, lon, precision}. Filtered server-side
  // because this table is paginated server-side.
  cluster: { lat: number, lon: number, precision: number } | null = null,
  niche?: NicheFilters
) {
  let url = `${API_URL}/taxonomy_search_run_data/${taxonomy}?taxonomy_type=${taxonomyType}&sort_field=${sortField}&sort_direction=${sortDirection}&page=${page}&page_size=${pageSize}&exclude_low_complexity=${excludeLowComplexity}`
  if (cluster) {
    url += `&cluster_lat=${cluster.lat}&cluster_lon=${cluster.lon}&cluster_precision=${cluster.precision}`
  }
  return axios.get(url, { params: nicheFilterParams(niche) })
}

export function fetchGlobalDataByTaxonomy (taxonomy: string, taxonomyType: string, niche?: NicheFilters) {
  return axios.get(`${API_URL}/taxonomy_search_global_data/${taxonomy}`,
    { params: { taxonomy_type: taxonomyType, ...nicheFilterParams(niche) } })
}

export function fetchTaxonomyMap (taxonomy: string, taxonomyType: string, precision = 1, niche?: NicheFilters) {
  // Server-side aggregated sample counts per map cell, split by environment
  // category. Unlike the marker map this is not capped, because the database
  // returns cells rather than runs. Deliberately excludes per-cell study
  // titles -- see fetchTaxonomyMapCellStudies below.
  return axios.get(`${API_URL}/taxonomy_map/${taxonomy}`,
    { params: { taxonomy_type: taxonomyType, precision, ...nicheFilterParams(niche) } })
}

export function fetchTaxonomyMapCellStudies (
  taxonomy: string, taxonomyType: string, lat: number, lon: number, precision = 1, niche?: NicheFilters
) {
  // Study titles are tooltip-only content, and bundling them into every cell
  // of fetchTaxonomyMap roughly doubled that response's size for a
  // mid-sized taxon -- fetched per cell instead, on hover.
  return axios.get(`${API_URL}/taxonomy_map_cell_studies/${taxonomy}`,
    { params: { taxonomy_type: taxonomyType, lat, lon, precision, ...nicheFilterParams(niche) } })
}

export function fetchTaxonomySearchHints (taxonomy: string, taxonomyType?: string) {
  const taxonomyTypeParam = taxonomyType ? `?taxonomy_type=${taxonomyType}` : ''
  return axios.get(`${API_URL}/taxonomy_search_hints/${taxonomy}${taxonomyTypeParam}`)
}

export function fetchRandomAccession(host: boolean, ecological: boolean, two_gbp: boolean, exclude_strict_low_complexity: boolean = true, non_human_host: boolean = true) {
  return axios.get(`${API_URL}/random_run?host=${host}&ecological=${ecological}&two_gbp=${two_gbp}&exclude_strict_low_complexity=${exclude_strict_low_complexity}&non_human_host=${non_human_host}`)
}

export function fetchAccession(accession: string) {
  return axios.get(`${API_URL}/accession/${accession}`)
}

export function verifyRecaptcha (token: string) {
  return axios.post(`${API_URL}/verify-recaptcha`, {
    token
  })
}

export function fetchUniversalSearch (q: string, exclude?: string) {
  // `exclude` keeps the backend from returning the run already being viewed,
  // so "Next" always moves somewhere new when another match exists.
  return axios.get(`${API_URL}/universal_search`, { params: { q, exclude } })
}
