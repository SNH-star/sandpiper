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
  cluster: { lat: number, lon: number, precision: number } | null = null
) {
  let url = `${API_URL}/taxonomy_search_run_data/${taxonomy}?taxonomy_type=${taxonomyType}&sort_field=${sortField}&sort_direction=${sortDirection}&page=${page}&page_size=${pageSize}&exclude_low_complexity=${excludeLowComplexity}`
  if (cluster) {
    url += `&cluster_lat=${cluster.lat}&cluster_lon=${cluster.lon}&cluster_precision=${cluster.precision}`
  }
  return axios.get(url)
}

export function fetchGlobalDataByTaxonomy (
  taxonomy: string,
  taxonomyType: string,
  // Same cluster shape as fetchRunsByTaxonomy above -- so the Individual
  // Runs map (and its caption, both driven by this endpoint's response)
  // actually reflect a clicked map cluster instead of only panning/zooming
  // to it while still describing the taxon's full unfiltered set.
  cluster: { lat: number, lon: number, precision: number } | null = null
) {
  const params: Record<string, string | number> = { taxonomy_type: taxonomyType }
  if (cluster) {
    params.cluster_lat = cluster.lat
    params.cluster_lon = cluster.lon
    params.cluster_precision = cluster.precision
  }
  return axios.get(`${API_URL}/taxonomy_search_global_data/${taxonomy}`, { params })
}

export function fetchTaxonomyMap (taxonomy: string, taxonomyType: string, precision = 1) {
  // Server-side aggregated sample counts per map cell, split by environment
  // category. Unlike the marker map this is not capped, because the database
  // returns cells rather than runs. Deliberately excludes per-cell study
  // titles -- see fetchTaxonomyMapCellStudies below.
  return axios.get(`${API_URL}/taxonomy_map/${taxonomy}`,
    { params: { taxonomy_type: taxonomyType, precision } })
}

export function fetchTaxonomyMapCellStudies (
  taxonomy: string, taxonomyType: string, lat: number, lon: number, precision = 1
) {
  // Study titles are tooltip-only content, and bundling them into every cell
  // of fetchTaxonomyMap roughly doubled that response's size for a
  // mid-sized taxon -- fetched per cell instead, on hover.
  return axios.get(`${API_URL}/taxonomy_map_cell_studies/${taxonomy}`,
    { params: { taxonomy_type: taxonomyType, lat, lon, precision } })
}

export function fetchTaxonomySearchHints (taxonomy: string, taxonomyType?: string, signal?: AbortSignal) {
  const taxonomyTypeParam = taxonomyType ? `?taxonomy_type=${taxonomyType}` : ''
  return axios.get(`${API_URL}/taxonomy_search_hints/${taxonomy}${taxonomyTypeParam}`, { signal })
}

export function fetchSearchFieldValues (field: string, query: string, signal?: AbortSignal) {
  return axios.get(`${API_URL}/search_field_values/${field}/${encodeURIComponent(query)}`, { signal })
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

export function fetchUniversalSearch (q: string, exclude?: string, signal?: AbortSignal) {
  // `exclude` keeps the backend from returning the run already being viewed,
  // so "Next" always moves somewhere new when another match exists.
  // `signal` lets the caller drop a request a newer one has replaced.
  return axios.get(`${API_URL}/universal_search`, { params: { q, exclude }, signal })
}

// "Explore tabled results" page: the taxonomy-page view of every run matching
// a search-box query.

export interface MapCluster {
  lat: number
  lon: number
  precision: number
}

function clusterParams (cluster: MapCluster | null): Record<string, number> {
  return cluster ? { cluster_lat: cluster.lat, cluster_lon: cluster.lon, cluster_precision: cluster.precision } : {}
}

export function fetchQueryGlobalData (q: string, cluster: MapCluster | null = null) {
  return axios.get(`${API_URL}/query_search_global_data`,
    { params: { q, ...clusterParams(cluster) } })
}

export function fetchQueryRunData (
  q: string,
  page: number,
  sortField: string,
  sortDirection: string,
  pageSize: number,
  excludeLowComplexity: boolean,
  cluster: MapCluster | null = null,
  // 'gtdb' | 'globdb': which database's abundance to show when the search names a taxon.
  taxonomyType = 'gtdb'
) {
  return axios.get(`${API_URL}/query_search_run_data`, {
    params: {
      q,
      page,
      page_size: pageSize,
      sort_field: sortField,
      sort_direction: sortDirection,
      exclude_low_complexity: excludeLowComplexity,
      taxonomy_type: taxonomyType,
      ...clusterParams(cluster)
    }
  })
}

export function fetchQueryMap (q: string, precision = 1) {
  return axios.get(`${API_URL}/query_map`, { params: { q, precision } })
}

export function fetchQueryMapCellStudies (
  q: string, lat: number, lon: number, precision = 1
) {
  return axios.get(`${API_URL}/query_map_cell_studies`,
    { params: { q, lat, lon, precision } })
}

// Same filters as the runs table, so the CSV holds exactly the table's runs.
export function queryCsvUrl (
  q: string, excludeLowComplexity: boolean, cluster: MapCluster | null = null,
  taxonomyType = 'gtdb'
) {
  const params = new URLSearchParams({ q, exclude_low_complexity: String(excludeLowComplexity), taxonomy_type: taxonomyType })
  for (const [key, value] of Object.entries(clusterParams(cluster))) {
    params.set(key, String(value))
  }
  return `${API_URL}/query_search_csv?${params}`
}
