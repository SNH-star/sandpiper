// The data behind each Statistics figure as a table, for the CSV download. Each builder takes the same
// numbers the figure draws and returns { columns: [text], rows: [[value]] }, so the file and the figure agree.
// Plain functions with no Vue in them, so they can be tested on their own.

const SAMPLE_CALLS = [
  { key: 'host_associated', label: 'Host-associated' },
  { key: 'ecological', label: 'Ecological' },
  { key: 'unclassified', label: 'Unclassified' }
]
const PERCENT_DECIMALS = 2
const sentence = text => text.charAt(0).toUpperCase() + text.slice(1)
const plainName = name => name.replace(/^[a-z]__/, '')
const rounded = (value, decimals = PERCENT_DECIMALS) => +Number(value).toFixed(decimals)
const sum = values => values.reduce((total, value) => total + value, 0)

// Runs released per year; split by sample call when the breakdown is given; running totals when cumulative.
export function releaseYearsTable ({ years, breakdown = null, cumulative = false }) {
  const split = breakdown && Array.isArray(breakdown.years)
  const byYear = new Map((split ? breakdown.years : []).map(row => [row.year, row]))
  const running = Object.fromEntries([['runs', 0], ...SAMPLE_CALLS.map(call => [call.key, 0])])
  const rows = years.map(row => {
    const own = { runs: row.runs, ...(byYear.get(row.year) || {}) }
    Object.keys(running).forEach(key => { running[key] = (cumulative ? running[key] : 0) + (own[key] || 0) })
    return split
      ? [row.year, ...SAMPLE_CALLS.map(call => running[call.key]), running.runs]
      : [row.year, running.runs]
  })
  const total = cumulative ? 'Cumulative runs' : 'Runs'
  return { columns: split ? ['Year', ...SAMPLE_CALLS.map(call => call.label), 'Total'] : ['Year', total], rows }
}

// Sequencing depth per release year. The summary keeps log10 bases; the table gives bases.
export function depthTable (years) {
  const bases = value => Math.round(10 ** value)
  return {
    columns: ['Year', 'Runs', '5th percentile (bases)', '25th percentile (bases)', 'Median (bases)', '75th percentile (bases)', '95th percentile (bases)'],
    rows: years.map(row => [row.year, row.runs, bases(row.p5), bases(row.q1), bases(row.median), bases(row.q3), bases(row.p95)])
  }
}

export function sampleTypesTable (sampleTypes, text) {
  return {
    columns: ['Type of sample', 'Runs', 'Percent of runs'],
    rows: sampleTypes.map(row => [text[row.key].name, row.runs, row.percent])
  }
}

// The share of runs with each kind of information; IndicPiper's split by warning follows its own row.
export function coverageTable (coverage, text, parts) {
  const rows = coverage.flatMap(row => {
    const name = text[row.key].name
    const split = row.caution_runs === undefined ? [] : parts.map(part => [`${name}: ${part.label}`, row[`${part.key}_runs`], row[`${part.key}_percent`]])
    return [[name, row.runs, row.percent], ...split]
  })
  return { columns: ['Information', 'Runs', 'Percent of runs'], rows }
}

// A bin's width, from where the first two bins start.
const binWidth = start => (start.length > 1 ? start[1] - start[0] : 1)
const BIN_DECIMALS = 4

// The bins of a density chart: one row per bin, and a column per line giving its share of runs in the bin.
export function densityTable ({ xTitle, series }) {
  const first = series.length ? series[0].histogram.start : []
  const width = binWidth(first)
  return {
    columns: [`${xTitle} from`, 'to', ...series.map(item => `${item.label} (% of runs)`)],
    rows: first.map((start, bin) => [rounded(start, BIN_DECIMALS), rounded(start + width, BIN_DECIMALS), ...series.map(item => item.histogram.percent[bin])])
  }
}

// Time from collection to release: the share of each call's day-dated runs released after each month of lag.
export function lagTable (summary, calls) {
  const precision = 'day'
  const series = calls.map(call => {
    const counts = summary.counts[call.call][precision]
    const runs = sum(counts)
    return { label: call.label, runs, histogram: { start: counts.map((_, month) => month / 12), percent: counts.map(n => (runs ? rounded(100 * n / runs, 3) : 0)) } }
  }).filter(item => item.runs > 0).sort((a, b) => b.runs - a.runs)
  return densityTable({ xTitle: 'Years from collection to release', series })
}

// Several groups' bins in one table, a row per group and bin. kinds: [{ type, key, groups: [{ name, label }] }].
export function groupDensityTable (version, kinds, { xTitle }) {
  const rows = kinds.flatMap(kind => {
    const histograms = version[kind.key] || {}
    return kind.groups
      .filter(group => histograms[group.name])
      .sort((a, b) => histograms[b.name].runs - histograms[a.name].runs)
      .flatMap(group => {
        const { start, percent, runs } = histograms[group.name]
        const width = binWidth(start)
        return start.map((from, bin) => [kind.type, group.label, runs, rounded(from, BIN_DECIMALS), rounded(from + width, BIN_DECIMALS), percent[bin]])
      })
  })
  return { columns: ['Sample type', 'Group', 'Runs', `${xTitle} from`, 'to', '% of runs'], rows }
}

// Mean abundance of each phylum in each group. sides: [[key in the summary, name shown]]. Phyla differ by side, so
// the columns are every phylum seen and a group leaves blank those it has none of.
export function phylumTable (composition, sides) {
  const phyla = []
  sides.forEach(([key]) => composition[key].phyla.forEach(phylum => { if (!phyla.includes(phylum)) phyla.push(phylum) }))
  const rows = sides.flatMap(([key, type]) => [...composition[key].groups]
    .sort((a, b) => b.runs - a.runs)
    .map(group => [type, sentence(group.name), group.runs, ...phyla.map(phylum => (phylum in group.percent ? group.percent[phylum] : null))]))
  return { columns: ['Sample type', 'Group', 'Runs', ...phyla.map(phylum => `${phylum} (%)`)], rows }
}

// The most widely detected taxa. Each row is split by group when it has segments, else by host-associated and ecological.
export function topTaxaTable (taxa, { database, level, runs }) {
  const labels = []
  taxa.forEach(row => (row.segments || []).forEach(segment => { if (!labels.includes(segment.label)) labels.push(segment.label) }))
  const stacked = labels.length > 0
  const breakdown = stacked ? labels.map(label => `${label} runs`) : ['Host-associated runs', 'Ecological runs']
  const split = row => (stacked
    ? labels.map(label => sum((row.segments || []).filter(segment => segment.label === label).map(segment => segment.runs)))
    : [row.host || 0, row.ecological || 0])
  return {
    columns: ['Rank', 'Taxon', 'Runs', 'Percent of runs', ...breakdown, 'Taxonomy database', 'Level', 'Runs counted in'],
    rows: taxa.map((row, i) => [i + 1, plainName(row.name), row.runs, row.percent, ...split(row), database, level, runs])
  }
}

// GTDB taxa found only in host-associated runs, only in ecological runs, and in both, at each level.
export function sampleTypeTaxaTable (rows, database) {
  return {
    columns: ['Level', 'Host-associated only', 'In both', 'Ecological only', 'All detected taxa', 'Percent in both', 'Taxonomy database'],
    rows: rows.map(row => [
      row.label, row.host_only, row.both, row.ecological_only, row.host_only + row.both + row.ecological_only,
      rounded(row.both_width), database
    ])
  }
}

// IndicPiper's habitats that have runs, most abundant first (as the figure lists them).
export function indicpiperTable (habitats) {
  const rows = Object.entries(habitats)
    .filter(([, group]) => group.runs > 0)
    .sort((a, b) => b[1].mean_abundance - a[1].mean_abundance || a[0].localeCompare(b[0]))
    .map(([habitat, group]) => [
      sentence(habitat), group.runs, group.matched_runs, rounded(group.mean_abundance * 100), rounded(group.mean_genera),
      rounded(group.mean_abundance_matched * 100), rounded(group.mean_genera_matched)
    ])
  return {
    columns: [
      'Habitat', 'Runs', 'Runs with an indicator genus', 'Mean indicator abundance (% of sample)', 'Mean indicator genera per run',
      'Mean indicator abundance, runs with an indicator genus (% of sample)', 'Mean indicator genera, runs with an indicator genus'
    ],
    rows
  }
}

// The mean known species fraction by year for each line of a trend chart.
export function yearTrendTable (series) {
  const years = [...new Set(series.flatMap(item => item.points.map(point => point.year)))].sort((a, b) => a - b)
  return {
    columns: ['Year', ...series.flatMap(item => [`${item.label} mean known species fraction (%)`, `${item.label} runs`])],
    rows: years.map(year => [year, ...series.flatMap(item => {
      const point = item.points.find(candidate => candidate.year === year)
      return point ? [point.mean, point.runs] : [null, null]
    })])
  }
}

// Runs in each map hexagon, by the hexagon's centre.
export function hexMapTable (map) {
  return {
    columns: ['Latitude of hexagon centre', 'Longitude of hexagon centre', 'Host-associated runs', 'Ecological runs', 'All runs'],
    rows: map.hexes.map(hex => [hex.lat, hex.lon, hex.host_associated, hex.ecological, hex.host_associated + hex.ecological])
  }
}

// The Sandpiper database versions table; a version with no value for something leaves it blank.
export function databaseVersionsTable (versions) {
  return {
    columns: ['Version', 'Released', 'GTDB', 'GlobDB', 'GOLD (JGI) retrieved', 'Metalog collected', 'IndicPiper version'],
    rows: versions.map(row => [row.label, row.released, row.gtdb, row.globdb, row.gold, row.metalog, row.indicpiper])
  }
}

// Several density charts in one table, a row per measure, line and bin. measures: [{ title, xTitle, series }].
export function densityLongTable (measures, lineName) {
  const rows = measures.flatMap(measure => measure.series.flatMap(item => {
    const width = binWidth(item.histogram.start)
    return item.histogram.start.map((from, bin) => [
      measure.title, item.label, rounded(from, BIN_DECIMALS), rounded(from + width, BIN_DECIMALS), item.histogram.percent[bin]
    ])
  }))
  return { columns: ['Measure', lineName, 'Bin from', 'Bin to', '% of runs'], rows }
}
