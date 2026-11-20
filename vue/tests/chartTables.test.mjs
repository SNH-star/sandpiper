// Run with: node --test vue/tests
import test from 'node:test'
import assert from 'node:assert/strict'
import { csvText } from '../src/components/statistics/tableExport.js'
import {
  releaseYearsTable, depthTable, sampleTypesTable, coverageTable, densityTable, groupDensityTable, phylumTable,
  topTaxaTable, sampleTypeTaxaTable, lagTable, densityLongTable, indicpiperTable, yearTrendTable, hexMapTable, databaseVersionsTable
} from '../src/components/statistics/chartTables.js'

test('csvText quotes commas, quotes and newlines, leaves blanks empty, and starts with a BOM', () => {
  const text = csvText({ columns: ['a', 'b'], rows: [['x, y', 'say "hi"'], [null, 3], ['two\nlines', undefined]] })
  assert.equal(text, '﻿a,b\r\n"x, y","say ""hi"""\r\n,3\r\n"two\nlines",\r\n')
})

test('releaseYearsTable gives runs per year, or running totals when cumulative', () => {
  const years = [{ year: 2020, runs: 5 }, { year: 2021, runs: 7 }]
  assert.deepEqual(releaseYearsTable({ years }), { columns: ['Year', 'Runs'], rows: [[2020, 5], [2021, 7]] })
  assert.deepEqual(releaseYearsTable({ years, cumulative: true }), { columns: ['Year', 'Cumulative runs'], rows: [[2020, 5], [2021, 12]] })
})

test('releaseYearsTable splits by sample call when given the breakdown', () => {
  const years = [{ year: 2020, runs: 5 }, { year: 2021, runs: 7 }]
  const breakdown = { years: [
    { year: 2020, host_associated: 3, ecological: 1, unclassified: 1 },
    { year: 2021, host_associated: 4, ecological: 2, unclassified: 1 }
  ] }
  const split = releaseYearsTable({ years, breakdown })
  assert.deepEqual(split.columns, ['Year', 'Host-associated', 'Ecological', 'Unclassified', 'Total'])
  assert.deepEqual(split.rows[1], [2021, 4, 2, 1, 7])
  const running = releaseYearsTable({ years, breakdown, cumulative: true })
  assert.deepEqual(running.rows[1], [2021, 7, 3, 2, 12])
})

test('depthTable turns log10 bases into bases', () => {
  const table = depthTable([{ year: 2011, runs: 283, p5: 9, q1: 9.5, median: 10, q3: 10.5, p95: 11 }])
  assert.equal(table.columns[0], 'Year')
  assert.deepEqual(table.rows[0], [2011, 283, 1e9, Math.round(10 ** 9.5), 1e10, Math.round(10 ** 10.5), 1e11])
})

test('sampleTypesTable names each type', () => {
  const table = sampleTypesTable([{ key: 'ecological', runs: 5, percent: 50 }], { ecological: { name: 'Ecological' } })
  assert.deepEqual(table, { columns: ['Type of sample', 'Runs', 'Percent of runs'], rows: [['Ecological', 5, 50]] })
})

test('coverageTable lists each kind of information and IndicPiper’s warning split', () => {
  const rows = [
    { key: 'coordinates', runs: 10, percent: 50 },
    { key: 'indicpiper', runs: 8, percent: 40, clear_runs: 6, clear_percent: 30, caution_runs: 2, caution_percent: 10 },
    { key: 'gold', runs: null, percent: null }
  ]
  const text = { coordinates: { name: 'Location' }, indicpiper: { name: 'IndicPiper' }, gold: { name: 'GOLD' } }
  const parts = [{ key: 'clear', label: 'IndicPiper habitat' }, { key: 'caution', label: 'non-IndicPiper habitat' }]
  const table = coverageTable(rows, text, parts)
  assert.deepEqual(table.columns, ['Information', 'Runs', 'Percent of runs'])
  assert.deepEqual(table.rows, [
    ['Location', 10, 50], ['IndicPiper', 8, 40],
    ['IndicPiper: IndicPiper habitat', 6, 30], ['IndicPiper: non-IndicPiper habitat', 2, 10],
    ['GOLD', null, null]
  ])
})

test('densityTable is one row per bin with a column per line', () => {
  const table = densityTable({
    xTitle: 'Known species fraction (%)',
    series: [
      { label: 'Host', histogram: { start: [0, 1], percent: [10, 90] } },
      { label: 'Eco', histogram: { start: [0, 1], percent: [60, 40] } }
    ]
  })
  assert.deepEqual(table, {
    columns: ['Known species fraction (%) from', 'to', 'Host (% of runs)', 'Eco (% of runs)'],
    rows: [[0, 1, 10, 60], [1, 2, 90, 40]]
  })
})

test('groupDensityTable stacks the groups of each kind, one row per group and bin', () => {
  const histogram = { start: [0, 1], percent: [25, 75], runs: 4 }
  const version = { host_groups: { human: histogram, pig: { ...histogram, runs: 9 } }, ecological_groups: { soil: histogram } }
  const kinds = [
    { type: 'Host-associated', key: 'host_groups', groups: [{ name: 'human', label: 'Human' }, { name: 'pig', label: 'Pig' }] },
    { type: 'Ecological', key: 'ecological_groups', groups: [{ name: 'soil', label: 'Soil' }, { name: 'marine', label: 'Marine' }] }
  ]
  const table = groupDensityTable(version, kinds, { xTitle: 'SPF (%)' })
  assert.deepEqual(table.columns, ['Sample type', 'Group', 'Runs', 'SPF (%) from', 'to', '% of runs'])
  assert.deepEqual(table.rows[0], ['Host-associated', 'Pig', 9, 0, 1, 25])
  assert.equal(table.rows.length, 6)
  assert.deepEqual(table.rows[4], ['Ecological', 'Soil', 4, 0, 1, 25])
})

test('phylumTable is one row per group with a column for every phylum', () => {
  const composition = {
    host_associated: { phyla: ['A', 'Other'], groups: [{ name: 'pig', runs: 5, percent: { A: 70, Other: 30 } }] },
    ecological: { phyla: ['B', 'Other'], groups: [{ name: 'soil', runs: 9, percent: { B: 80, Other: 20 } }] }
  }
  const table = phylumTable(composition, [['host_associated', 'Host-associated'], ['ecological', 'Ecological']])
  assert.deepEqual(table.columns, ['Sample type', 'Group', 'Runs', 'A (%)', 'Other (%)', 'B (%)'])
  assert.deepEqual(table.rows, [['Host-associated', 'Pig', 5, 70, 30, null], ['Ecological', 'Soil', 9, null, 20, 80]])
})

test('topTaxaTable says what it counts and breaks each taxon down by group or by sample type', () => {
  const context = { database: 'GTDB R232', level: 'Genus', runs: 'all 100 runs', total: 100 }
  const plain = topTaxaTable([{ name: 'g__Bacteroides', runs: 54, percent: 54, host: 40, ecological: 14 }], context)
  assert.deepEqual(plain.columns, ['Rank', 'Taxon', 'Runs', 'Percent of runs', 'Host-associated runs', 'Ecological runs', 'Taxonomy database', 'Level', 'Runs counted in'])
  assert.deepEqual(plain.rows[0], [1, 'Bacteroides', 54, 54, 40, 14, 'GTDB R232', 'Genus', 'all 100 runs'])
  const stacked = topTaxaTable([
    { name: 'g__A', runs: 5, percent: 5, segments: [{ label: 'Human', runs: 3 }, { label: 'Pig', runs: 2 }] },
    { name: 'g__B', runs: 4, percent: 4, segments: [{ label: 'Pig', runs: 4 }] }
  ], context)
  assert.deepEqual(stacked.columns.slice(4, 6), ['Human runs', 'Pig runs'])
  assert.deepEqual(stacked.rows[1].slice(0, 6), [2, 'B', 4, 4, 0, 4])
})

test('sampleTypeTaxaTable has the three counts, their total and the share in both', () => {
  const table = sampleTypeTaxaTable([{ label: 'Genus', host_only: 10, both: 60, ecological_only: 30, both_width: 60 }], 'GTDB R232')
  assert.deepEqual(table.columns, ['Level', 'Host-associated only', 'In both', 'Ecological only', 'All detected taxa', 'Percent in both', 'Taxonomy database'])
  assert.deepEqual(table.rows[0], ['Genus', 10, 60, 30, 100, 60, 'GTDB R232'])
})

test('indicpiperTable lists each habitat with its averages', () => {
  const table = indicpiperTable({ soil: { runs: 4, matched_runs: 2, mean_abundance: 0.1234, mean_genera: 3.456, mean_abundance_matched: 0.2, mean_genera_matched: 6 }, empty: { runs: 0 } })
  assert.deepEqual(table.rows, [['Soil', 4, 2, 12.34, 3.46, 20, 6]])
})

test('yearTrendTable has a mean and run count per line and year', () => {
  const series = [
    { label: 'Host', points: [{ year: 2020, mean: 50.5, runs: 10 }] },
    { label: 'Eco', points: [{ year: 2020, mean: 20, runs: 5 }, { year: 2021, mean: 30, runs: 6 }] }
  ]
  const table = yearTrendTable(series)
  assert.deepEqual(table.columns, ['Year', 'Host mean known species fraction (%)', 'Host runs', 'Eco mean known species fraction (%)', 'Eco runs'])
  assert.deepEqual(table.rows, [[2020, 50.5, 10, 20, 5], [2021, null, null, 30, 6]])
})

test('hexMapTable gives each hexagon’s centre and runs', () => {
  const table = hexMapTable({ hexes: [{ lat: 1, lon: 2, host_associated: 3, ecological: 4 }] })
  assert.deepEqual(table.rows, [[1, 2, 3, 4, 7]])
  assert.equal(table.columns[4], 'All runs')
})

test('databaseVersionsTable writes a dash as a blank', () => {
  const table = databaseVersionsTable([{ label: 'v2', released: null, gtdb: 'R232', globdb: 'R232', gold: null, metalog: null, indicpiper: null }])
  assert.deepEqual(table.rows[0], ['v2', null, 'R232', 'R232', null, null, null])
})

test('lagTable gives each call’s share of day-dated runs by month, the larger call first', () => {
  const summary = { counts: { host: { day: [1, 3] }, ecological: { day: [5, 5, 0] } } }
  const table = lagTable(summary, [{ call: 'host', label: 'Host-associated' }, { call: 'ecological', label: 'Ecological' }])
  assert.deepEqual(table.columns, ['Years from collection to release from', 'to', 'Ecological (% of runs)', 'Host-associated (% of runs)'])
  assert.deepEqual(table.rows[1], [0.0833, 0.1667, 50, 75])
})

test('densityLongTable has a row per measure, line and bin', () => {
  const table = densityLongTable([{ title: 'Size', series: [{ label: 'v1', histogram: { start: [0, 2], percent: [40, 60] } }] }], 'Version')
  assert.deepEqual(table, { columns: ['Measure', 'Version', 'Bin from', 'Bin to', '% of runs'], rows: [['Size', 'v1', 0, 2, 40], ['Size', 'v1', 2, 4, 60]] })
})

test('every sample group has its own colour token, and no two groups on a side share one', async () => {
  const { readFileSync } = await import('node:fs')
  const { HOST_GROUPS, ECOLOGICAL_GROUPS } = await import('../src/components/statistics/groupColours.js')
  const scss = readFileSync(new URL('../src/assets/scss/app.scss', import.meta.url), 'utf8')
  for (const side of [HOST_GROUPS, ECOLOGICAL_GROUPS]) {
    const values = side.map(item => (scss.match(new RegExp(`--color-group-${item.key}:\\s*([^;]+);`)) || [])[1])
    assert.ok(values.every(Boolean), 'a group has no colour token')
    assert.equal(new Set(values).size, side.length)
  }
})
