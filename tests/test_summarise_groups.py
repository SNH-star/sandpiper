import importlib.util
import os
import sys

import pandas as pd

BIN = os.path.join(os.path.dirname(__file__), '..', 'backend', 'bin')
sys.path.insert(0, BIN)
spec = importlib.util.spec_from_file_location('summarise_groups', os.path.join(BIN, 'summarise_groups.py'))
summarise_groups = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summarise_groups)


def test_weighted_line_recovers_an_exact_line():
    slope, intercept = summarise_groups.weighted_line([2010, 2011, 2012], [10.0, 20.0, 30.0], [5, 50, 500])
    assert round(slope, 6) == 10.0
    assert round(intercept + 10.0 * 2010, 6) == 10.0


def test_weighted_line_follows_the_larger_years():
    slope, _ = summarise_groups.weighted_line([1, 2, 3], [0.0, 10.0, 40.0], [1, 1, 1000])
    assert slope > 15


def test_yearly_trend_drops_thin_years_and_splits_by_call():
    rows = [('host', 2020, 80.0)] * 12 + [('host', 2021, 90.0)] * 12 + [('host', 2019, 5.0)] * 3 + [('ecological', 2020, 10.0)] * 11
    frame = pd.DataFrame(rows, columns=['host_or_not', 'year', 'known_species_fraction'])
    trend = summarise_groups.yearly_trend(frame)
    assert [p['year'] for p in trend['host_associated']['points']] == [2020, 2021]
    assert trend['ecological'] is None


def test_group_samples_need_exact_label_and_matching_call():
    frame = pd.DataFrame({
        'sample': ['a', 'b', 'c', 'd'],
        'organism': ['mouse metagenome', 'mouse gut metagenome', 'soil metagenome', 'soil metagenome'],
        'host_or_not': ['host', 'host', 'ecological', 'host']})
    assert summarise_groups.group_samples(frame) == {'a': ('host', 'mouse'), 'b': ('host', 'mouse'), 'c': ('ecological', 'soil')}


def test_composition_averages_per_run_and_folds_the_rest_into_other():
    groups = {'a': ('host', 'mouse'), 'b': ('host', 'mouse')}
    lines = ['a\tp__X\t75\t100', 'a\tunassigned\t25\t100', 'b\tp__X\t50\t100', 'b\tp__Y\t50\t100', 'z\tp__X\t1\t1']
    result = summarise_groups.aggregate_composition(lines, groups)['host_associated']
    mouse = result['groups'][0]
    assert mouse['runs'] == 2
    assert mouse['percent']['X'] == 62.5 and mouse['percent']['Y'] == 25.0
    assert round(sum(mouse['percent'].values()), 2) == 100.0


def _write_metadata(path, rows):
    pd.DataFrame(rows, columns=['accession', 'gtdb_taxonomy', 'ncbi_date']).to_csv(path, sep='\t', index=False, compression='gzip')


def test_species_first_years_takes_the_earliest_genome_of_each_species(tmp_path):
    path = tmp_path / 'meta.tsv.gz'
    _write_metadata(path, [
        ('A', 'd__Bacteria;g__X;s__X one', '2015-06-01'),
        ('B', 'd__Bacteria;g__X;s__X one', '2012-01-31'),
        ('C', 'd__Bacteria;g__Y;s__Y two', '2020-12-31'),
    ])
    assert summarise_groups.species_first_years([str(path)]) == {'X one': 2012, 'Y two': 2020}


def test_stream_condensed_counts_only_species_with_a_genome_the_year_before(tmp_path):
    condensed = tmp_path / 'condensed.tsv'
    condensed.write_text(
        'sample\tcoverage\ttaxonomy\n'
        'r1\t6.0\tRoot; d__Bacteria; p__P; c__C; o__O; f__F; g__G; s__Old sp\n'
        'r1\t2.0\tRoot; d__Bacteria; p__P; c__C; o__O; f__F; g__G; s__New sp\n'
        'r1\t2.0\tRoot; d__Bacteria; p__P; c__C\n'
    )
    groups = {'r1': ('host', 'human')}
    years = {'r1': 2018}
    first = {'Old sp': 2017, 'New sp': 2018}
    composition, known = summarise_groups.stream_condensed(str(condensed), groups, years, first, str(tmp_path))
    assert known['r1'] == 60.0
    assert composition['host_associated']['groups'][0]['name'] == 'human'


def test_species_first_in_the_release_year_do_not_count(tmp_path):
    condensed = tmp_path / 'condensed.tsv'
    condensed.write_text('r1\t5.0\tRoot; d__Bacteria; p__P; s__Same year\n')
    _, known = summarise_groups.stream_condensed(str(condensed), {}, {'r1': 2018}, {'Same year': 2018}, str(tmp_path))
    assert known['r1'] == 0.0


def test_yearly_trend_stores_the_fit_as_values_at_its_end_years():
    rows = [('host', 2011 + (i % 15), 20.0 + 3.1 * (i % 15) + (i % 7)) for i in range(450)]
    frame = pd.DataFrame(rows, columns=['host_or_not', 'year', 'known_species_fraction'])
    trend = summarise_groups.yearly_trend(frame)['host_associated']
    years = [p['year'] for p in trend['points']]
    slope, intercept = summarise_groups.weighted_line(years, [p['mean'] for p in trend['points']], [p['runs'] for p in trend['points']])
    first, last = trend['fit']
    assert (first['year'], last['year']) == (years[0], years[-1])
    assert abs(first['value'] - (slope * years[0] + intercept)) < 0.006
    assert abs(last['value'] - (slope * years[-1] + intercept)) < 0.006


def test_yearly_depth_gives_log10_percentiles_per_year_and_drops_thin_years():
    # 1e9 bases, 1e10 bases and a thin year; depth is reported as log10 bases.
    rows = [(2020, 1e9)] * 6 + [(2020, 1e10)] * 6 + [(2021, 1e9)] * 12 + [(2019, 1e9)] * 3
    frame = pd.DataFrame(rows, columns=['year', 'metagenome_size'])
    depth = summarise_groups.yearly_depth(frame)
    assert [row['year'] for row in depth] == [2020, 2021]
    first = depth[0]
    assert first['runs'] == 12
    assert first['p5'] == 9.0 and first['p95'] == 10.0
    assert first['q1'] <= first['median'] <= first['q3']
    assert depth[1]['median'] == 9.0


def test_yearly_depth_ignores_runs_without_a_year_or_a_positive_size():
    rows = [(2020, 1e9)] * 10 + [(None, 1e9)] * 5 + [(2020, 0)] * 5 + [(2020, None)] * 5
    frame = pd.DataFrame(rows, columns=['year', 'metagenome_size'])
    depth = summarise_groups.yearly_depth(frame)
    assert depth == [{'year': 2020, 'runs': 10, 'p5': 9.0, 'q1': 9.0, 'median': 9.0, 'q3': 9.0, 'p95': 9.0}]


def _group_frame():
    rows = ([('host', 'human metagenome', 2020, 80.0)] * 11 + [('host', 'human metagenome', 2021, 90.0)] * 11
            + [('host', 'human gut metagenome', 2020, 40.0)] * 11 + [('host', 'human gut metagenome', 2021, 50.0)] * 11
            + [('host', 'plant metagenome', 2020, 10.0)] * 11 + [('host', 'plant metagenome', 2021, 20.0)] * 3
            + [('ecological', 'soil metagenome', 2020, 5.0)] * 11 + [('ecological', 'soil metagenome', 2021, 15.0)] * 11
            + [('ecological', 'soil gut metagenome', 2020, 99.0)] * 30)
    return pd.DataFrame(rows, columns=['host_or_not', 'organism', 'year', 'known_species_fraction'])


def test_yearly_group_trends_keep_gut_runs_apart_from_their_host():
    trends = summarise_groups.yearly_group_trends(_group_frame())['host']
    assert [p['mean'] for p in trends['human']['points']] == [80.0, 90.0]
    assert [p['mean'] for p in trends['human_gut']['points']] == [40.0, 50.0]


def test_yearly_group_trends_leave_out_series_with_under_two_thick_years():
    host = summarise_groups.yearly_group_trends(_group_frame())['host']
    assert host['plant'] is None
    assert host['mouse'] is None


def test_yearly_group_trends_treat_ecological_groups_as_single_labels():
    ecological = summarise_groups.yearly_group_trends(_group_frame())['ecological']
    assert [p['mean'] for p in ecological['soil']['points']] == [5.0, 15.0]
    assert 'soil_gut' not in ecological
    assert set(ecological) == {'soil', 'sediment', 'marine', 'freshwater', 'aquatic'}


def test_yearly_group_trends_have_one_line_each_for_bovine_pig_and_plant():
    host = summarise_groups.yearly_group_trends(_group_frame())['host']
    assert set(host) == {'plant', 'bovine', 'pig', 'human', 'human_gut', 'mouse', 'mouse_gut'}


def test_series_of_puts_feces_with_gut_and_other_body_sites_with_non_gut():
    series_of = summarise_groups.series_of
    assert series_of('host', 'human gut metagenome') == 'human_gut'
    assert series_of('host', 'human feces metagenome') == 'human_gut'
    assert series_of('host', 'human metagenome') == 'human'
    assert series_of('host', 'human oral metagenome') == 'human'
    assert series_of('host', 'human viral metagenome') == 'human'
    assert series_of('host', 'mouse brain metagenome') == 'mouse'
    assert series_of('host', 'mouse feces metagenome') == 'mouse_gut'


def test_series_of_pools_bovine_and_pig_gut_with_the_rest():
    series_of = summarise_groups.series_of
    for name in ('bovine', 'pig'):
        assert series_of('host', f'{name} gut metagenome') == name
        assert series_of('host', f'{name} metagenome') == name
        assert series_of('host', f'{name} skin metagenome') == name


def test_series_of_ignores_viruses_generic_and_lookalike_labels():
    series_of = summarise_groups.series_of
    assert series_of('host', 'Human adenovirus 41') is None
    assert series_of('host', 'uncultured human fecal virus') is None
    assert series_of('host', 'gut metagenome') is None
    assert series_of('host', 'feces metagenome') is None
    assert series_of('host', 'pigeon metagenome') is None
    assert series_of('host', 'plant root metagenome') is None
    assert series_of('ecological', 'soil gut metagenome') is None
    assert series_of('ecological', 'soil metagenome') == 'soil'


def test_yearly_group_trends_pool_body_sites_into_non_gut():
    rows = ([('host', 'human oral metagenome', 2020, 20.0)] * 6 + [('host', 'human skin metagenome', 2020, 40.0)] * 6
            + [('host', 'human oral metagenome', 2021, 60.0)] * 12
            + [('host', 'human feces metagenome', 2020, 70.0)] * 12 + [('host', 'human gut metagenome', 2021, 80.0)] * 12)
    frame = pd.DataFrame(rows, columns=['host_or_not', 'organism', 'year', 'known_species_fraction'])
    host = summarise_groups.yearly_group_trends(frame)['host']
    assert host['human']['points'][0] == {'year': 2020, 'mean': 30.0, 'runs': 12}
    assert [p['runs'] for p in host['human_gut']['points']] == [12, 12]


def test_yearly_group_trends_skip_runs_without_an_organism_label():
    rows = [('host', None, 2020, 50.0)] * 12 + [('host', 'human gut metagenome', 2020, 80.0)] * 12 + [('host', 'human gut metagenome', 2021, 90.0)] * 12
    frame = pd.DataFrame(rows, columns=['host_or_not', 'organism', 'year', 'known_species_fraction'])
    assert summarise_groups.series_of('host', float('nan')) is None
    host = summarise_groups.yearly_group_trends(frame)['host']
    assert [p['runs'] for p in host['human_gut']['points']] == [12, 12]


# --- time from collection to release ---------------------------------------------------------------

import datetime as dt

import numpy as np
import pytest


@pytest.mark.parametrize('text, precision, expected', [
    ('2020-03-09', 'day', dt.date(2020, 3, 9)),
    ('2020-03-09T18:00Z', 'day', dt.date(2020, 3, 9)),
    ('2020-03-09 18:00:00', 'day', dt.date(2020, 3, 9)),
    # a run is placed at the middle of what was recorded: its day, the 15th of its month, 1 July of its year,
    # the midpoint of a range; a range counts as the precision of its start
    ('2020-03', 'month', dt.date(2020, 3, 15)),
    ('2020-02', 'month', dt.date(2020, 2, 15)),
    ('2020', 'year', dt.date(2020, 7, 1)),
    ('2019-01-15/2019-02-07', 'day', dt.date(2019, 1, 26)),
    ('2019-01-01/2019-01-31', 'day', dt.date(2019, 1, 16)),
    ('2021-06/2024-05', 'month', dt.date(2022, 11, 30)),
    ('2016/2019', 'year', dt.date(2017, 12, 31)),
])
def test_parse_collection_gives_the_precision_and_the_date_a_run_is_placed_at(text, precision, expected):
    assert summarise_groups.parse_collection(text) == (precision, expected)


@pytest.mark.parametrize('text', [
    '', 'missing', 'missing: data agreement established pre-2023', '2020-02-30', '2020-13', '1/13/15 0:00',
    '2019-02-07/2019-01-15', '2019/2020/2021', '0001', '3020',
])
def test_parse_collection_rejects_what_is_not_a_usable_date(text):
    assert summarise_groups.parse_collection(text) is None


def _write_chunk(folder, name, header, rows):
    (folder / name).write_text('\t'.join(header) + '\n' + '\n'.join('\t'.join(row) for row in rows) + '\n')


def test_collection_table_places_a_run_by_the_day_within_its_month(tmp_path):
    _write_chunk(tmp_path, '0.csv', ['run', 'collection_date', 'published'],
                 [['R1', '2020-01-01', '2021-02-04 10:00:00']])  # 400 days
    table = summarise_groups.collection_table(str(tmp_path), {'R1'})
    assert table.loc['R1', 'precision'] == 'day'
    assert 13.0 < table.loc['R1', 'months'] < 13.3


def test_collection_table_takes_the_most_precise_date_among_the_columns(tmp_path):
    _write_chunk(tmp_path, '0.csv', ['run', 'collection_date', 'collection date', 'published'],
                 [['R1', '2020-02', '2020-02-17', '2021-01-01 00:00:00'],
                  ['R2', '', '2020', '2021-01-01 00:00:00'],
                  ['R3', 'missing', '', '2021-01-01 00:00:00']])
    table = summarise_groups.collection_table(str(tmp_path), {'R1', 'R2', 'R3'})
    assert table.loc['R1', 'precision'] == 'day'
    assert table.loc['R2', 'precision'] == 'year'
    assert table.loc['R3', 'precision'] is None and np.isnan(table.loc['R3', 'months'])


def test_collection_table_copes_with_a_chunk_that_has_none_of_the_date_columns(tmp_path):
    _write_chunk(tmp_path, '0.csv', ['run', 'published'], [['R1', '2020-04-01 00:00:00']])
    _write_chunk(tmp_path, '1.csv', ['run', 'collection date', 'published'], [['R2', '2020-01-01', '2020-04-01 00:00:00']])
    table = summarise_groups.collection_table(str(tmp_path), {'R1', 'R2'})
    assert table.loc['R1', 'precision'] is None
    assert table.loc['R2', 'precision'] == 'day'


def test_collection_table_keeps_only_the_requested_runs(tmp_path):
    _write_chunk(tmp_path, '0.csv', ['run', 'collection_date', 'published'],
                 [['R1', '2020-01-01', '2020-04-01 00:00:00'], ['R2', '2020-01-01', '2020-04-01 00:00:00']])
    assert list(summarise_groups.collection_table(str(tmp_path), {'R1'}).index) == ['R1']


def test_collection_table_fails_loudly_when_a_chunk_has_no_published_column(tmp_path):
    _write_chunk(tmp_path, '0.csv', ['run', 'collection_date'], [['R1', '2020-01-01']])
    with pytest.raises(ValueError):
        summarise_groups.collection_table(str(tmp_path), {'R1'})


def _table(rows):
    return pd.DataFrame(rows, columns=['run', 'precision', 'months']).set_index('run')


def test_collection_summary_counts_runs_per_call_and_precision_in_monthly_bins():
    table = _table([('a', 'day', 0.5), ('b', 'day', 1.5), ('c', 'month', 1.6), ('d', 'year', 10.2), ('e', 'day', 3.0)])
    summary = summarise_groups.collection_summary(table, {'a': 'host', 'b': 'host', 'c': 'host', 'd': 'ecological', 'e': None}, 9)
    host = summary['counts']['host']
    assert host['day'][:3] == [1, 1, 0] and host['month'][:3] == [0, 1, 0]
    assert summary['counts']['ecological']['year'][10] == 1
    assert len(host['day']) == summarise_groups.LAG_MAX_MONTHS
    assert summary['months'] == summarise_groups.LAG_MAX_MONTHS


def test_collection_summary_drops_negative_lags_and_counts_those_beyond_the_axis():
    table = _table([('a', 'day', -2.0), ('b', 'day', 400.0), ('c', 'day', 5.0)])
    summary = summarise_groups.collection_summary(table, {'a': 'host', 'b': 'host', 'c': 'host'}, 3)
    assert sum(summary['counts']['host']['day']) == 1
    assert summary['beyond_axis']['host']['day'] == 1


def test_collection_summary_counts_negative_lags_per_call_and_precision():
    table = _table([('a', 'day', -2.0), ('b', 'day', 5.0), ('c', 'year', -30.0), ('d', 'day', -0.5)])
    summary = summarise_groups.collection_summary(table, {'a': 'host', 'b': 'host', 'c': 'ecological', 'd': 'host'}, 4)
    assert summary['negative']['host']['day'] == 2
    assert summary['negative']['ecological']['year'] == 1
    assert summary['negative']['ecological']['day'] == 0


def test_collection_summary_reports_how_many_called_runs_have_each_precision_including_none():
    table = _table([('a', 'day', 1.0), ('b', 'day', 2.0), ('c', 'month', 1.0), ('d', 'year', 1.0), ('e', None, float('nan'))])
    calls = {'a': 'host', 'b': 'host', 'c': 'ecological', 'd': 'host', 'e': 'host', 'f': 'ecological'}
    summary = summarise_groups.collection_summary(table, calls, len(calls))
    assert summary['available'] == {'day': 2, 'month': 1, 'year': 1, 'none': 2}
    assert summary['database_runs'] == 6


def test_collection_summary_leaves_out_runs_without_a_host_or_ecological_call():
    table = _table([('a', 'day', 1.0), ('b', 'day', 2.0), ('c', 'month', 1.0), ('d', None, float('nan'))])
    calls = {'a': 'host', 'b': None, 'c': float('nan'), 'd': 'ecological'}
    summary = summarise_groups.collection_summary(table, calls, 2)
    assert summary['available'] == {'day': 1, 'month': 0, 'year': 0, 'none': 1}
    assert summary['database_runs'] == 2
    assert sum(summary['counts']['host']['day']) == 1


def test_collection_summary_accounts_for_every_called_run():
    table = _table([('a', 'day', 1.0), ('b', 'day', 400.0), ('c', 'day', -3.0), ('d', 'year', 20.0), ('e', None, float('nan'))])
    calls = {name: 'host' for name in 'abcde'}
    summary = summarise_groups.collection_summary(table, calls, 5)
    for precision in summarise_groups.PRECISIONS:
        drawn = sum(sum(summary['counts'][call][precision]) for call in summarise_groups.CALL_KEYS)
        beyond = sum(summary['beyond_axis'][call][precision] for call in summarise_groups.CALL_KEYS)
        negative = sum(summary['negative'][call][precision] for call in summarise_groups.CALL_KEYS)
        assert drawn + beyond + negative == summary['available'][precision]
    assert sum(summary['available'].values()) == summary['database_runs']


# --- most widely detected taxa, by group ---------------------------------------------------------------

GROUP_ROWS = [
    ('gtdb', 'genus', 'g__A', 5), ('gtdb', 'genus', 'g__B', 9), ('gtdb', 'genus', 'g__C', 7),
    ('gtdb', 'phylum', 'p__X', 3), ('globdb', 'genus', 'g__A', 4),
]


def test_group_top_taxa_sorts_each_taxonomy_and_level_by_runs():
    taxa = summarise_groups.group_top_taxa(GROUP_ROWS)
    assert [row['name'] for row in taxa['gtdb']['genus']] == ['g__B', 'g__C', 'g__A']
    assert taxa['gtdb']['genus'][0] == {'name': 'g__B', 'runs': 9}
    assert taxa['gtdb']['phylum'] == [{'name': 'p__X', 'runs': 3}]
    assert taxa['globdb']['genus'] == [{'name': 'g__A', 'runs': 4}]


def test_group_top_taxa_keeps_only_the_requested_number_of_taxa():
    taxa = summarise_groups.group_top_taxa(GROUP_ROWS, count=2)
    assert [row['name'] for row in taxa['gtdb']['genus']] == ['g__B', 'g__C']


def test_group_top_taxa_breaks_ties_by_name():
    taxa = summarise_groups.group_top_taxa([('gtdb', 'genus', 'g__Z', 5), ('gtdb', 'genus', 'g__A', 5)])
    assert [row['name'] for row in taxa['gtdb']['genus']] == ['g__A', 'g__Z']


def test_group_top_taxa_of_no_rows_is_empty():
    assert summarise_groups.group_top_taxa([]) == {}


def _taxa_database(path):
    """A tiny copy of the website database: three pig runs (one with a gut label), a soil run with a
    host call (so not soil), a soil run, and a run of no group."""
    duckdb = pytest.importorskip('duckdb')
    con = duckdb.connect(str(path))
    con.execute('CREATE TABLE ncbi_metadata (id INTEGER, taxon_name VARCHAR)')
    con.execute('CREATE TABLE parsed_sample_attributes (run_id INTEGER, host_or_not_mature VARCHAR)')
    con.execute('CREATE TABLE taxonomies (id INTEGER, taxonomy_type VARCHAR, taxonomy_level VARCHAR, name VARCHAR, '
                'host_sample_count INTEGER, ecological_sample_count INTEGER)')
    con.execute('CREATE TABLE condensed_profiles (run_id INTEGER, taxonomy_id INTEGER)')
    con.execute("INSERT INTO ncbi_metadata VALUES (1,'pig metagenome'),(2,'pig gut metagenome'),(3,'pig gut metagenome'),"
                "(4,'soil metagenome'),(5,'soil metagenome'),(6,'wastewater metagenome')")
    con.execute("INSERT INTO parsed_sample_attributes VALUES (1,'host'),(2,'host'),(3,'host'),(4,'host'),(5,'ecological'),(6,'ecological')")
    con.execute("INSERT INTO taxonomies VALUES (10,'gtdb','genus','g__Pig',4,0),(11,'gtdb','phylum','p__Bacillota',2,0),"
                "(12,'gtdb','family','f__Ignored',1,0),(13,'globdb','genus','g__Pig',1,0),(14,'gtdb','genus','g__Soil',0,2)")
    # g__Pig is in runs 1,2,3 (and, wrongly for pig, run 4); p__Bacillota in 1,2; the family is never reported
    con.execute("INSERT INTO condensed_profiles VALUES (1,10),(2,10),(3,10),(4,10),(1,11),(2,11),(1,12),(1,13),(5,14),(6,14)")
    con.close()


def test_top_taxa_by_group_counts_runs_of_the_group_and_its_side_only(tmp_path):
    db = tmp_path / 'site.duckdb'
    _taxa_database(db)
    result = summarise_groups.top_taxa_by_group(str(db))
    pig = result['pig']
    assert pig['call'] == 'host' and pig['runs'] == 3
    assert pig['taxa']['gtdb']['genus'] == [{'name': 'g__Pig', 'runs': 3}]
    assert pig['taxa']['gtdb']['phylum'] == [{'name': 'p__Bacillota', 'runs': 2}]
    assert pig['taxa']['globdb']['genus'] == [{'name': 'g__Pig', 'runs': 1}]
    assert 'family' not in pig['taxa']['gtdb']
    assert result['soil']['call'] == 'ecological' and result['soil']['runs'] == 1
    assert result['soil']['taxa']['gtdb']['genus'] == [{'name': 'g__Soil', 'runs': 1}]


def test_top_taxa_by_group_leaves_out_groups_with_no_runs(tmp_path):
    db = tmp_path / 'site.duckdb'
    _taxa_database(db)
    result = summarise_groups.top_taxa_by_group(str(db))
    assert 'marine' not in result and 'human' not in result


def test_taxa_group_breakdown_splits_each_sides_top_taxa_by_group(tmp_path):
    db = tmp_path / 'site.duckdb'
    _taxa_database(db)
    result = summarise_groups.taxa_group_breakdown(str(db))
    # g__Pig: 4 host runs, 3 of them pig; the fourth is a host run in no named group
    assert result['host']['gtdb']['genus'] == [{'name': 'g__Pig', 'runs': 4, 'groups': {'pig': 3}}]
    assert result['host']['gtdb']['phylum'] == [{'name': 'p__Bacillota', 'runs': 2, 'groups': {'pig': 2}}]
    assert result['host']['globdb']['genus'] == [{'name': 'g__Pig', 'runs': 1, 'groups': {'pig': 1}}]
    assert result['ecological']['gtdb']['genus'] == [{'name': 'g__Soil', 'runs': 2, 'groups': {'soil': 1}}]
    assert 'family' not in result['host']['gtdb']


def test_taxa_group_breakdown_leaves_out_taxa_no_run_of_the_side_has(tmp_path):
    db = tmp_path / 'site.duckdb'
    _taxa_database(db)
    result = summarise_groups.taxa_group_breakdown(str(db))
    assert all(row['name'] != 'g__Soil' for row in result['host']['gtdb']['genus'])


# --- the database's host / ecological call -------------------------------------------------------------

def test_database_calls_reads_each_runs_mature_call(tmp_path):
    duckdb = pytest.importorskip('duckdb')
    con = duckdb.connect(str(tmp_path / 'site.duckdb'))
    con.execute('CREATE TABLE ncbi_metadata (id INTEGER, acc VARCHAR)')
    con.execute('CREATE TABLE parsed_sample_attributes (run_id INTEGER, host_or_not_mature VARCHAR)')
    con.execute("INSERT INTO ncbi_metadata VALUES (1,'SRR1'),(2,'SRR2'),(3,'SRR3')")
    con.execute("INSERT INTO parsed_sample_attributes VALUES (1,'host'),(2,'ecological'),(3,NULL)")
    con.close()
    calls = summarise_groups.database_calls(str(tmp_path / 'site.duckdb'))
    assert calls == {'SRR1': 'host', 'SRR2': 'ecological', 'SRR3': None}


def test_with_database_calls_replaces_the_summarys_call_and_leaves_unknown_runs_uncalled():
    frame = pd.DataFrame({'sample': ['a', 'b', 'c'], 'host_or_not': ['host', 'host', 'ecological'], 'organism': ['x', 'y', 'z']})
    result = summarise_groups.with_database_calls(frame, {'a': 'ecological', 'b': 'host'})
    assert result['host_or_not'].tolist()[:2] == ['ecological', 'host']
    assert pd.isna(result['host_or_not'].iloc[2])
    assert result['organism'].tolist() == ['x', 'y', 'z']
    assert frame['host_or_not'].tolist() == ['host', 'host', 'ecological']  # the input is not changed


# --- IndicPiper indicator averages per habitat ---------------------------------------------------------

def _indicpiper_database(path):
    """Soil: four runs (labels spelled differently), two matched; gut: one run, matched; one run of no habitat.
    Marine water has scores but no run is recorded as it."""
    duckdb = pytest.importorskip('duckdb')
    con = duckdb.connect(str(path))
    con.execute('CREATE TABLE ncbi_metadata (id INTEGER, taxon_name VARCHAR)')
    con.execute('CREATE TABLE indicator_habitat_scores (run_id INTEGER, habitat VARCHAR, score DOUBLE)')
    con.execute('CREATE TABLE indicator_habitat_genus_scores (run_id INTEGER, habitat VARCHAR, genus VARCHAR, '
                'relative_abundance DOUBLE)')
    con.execute("INSERT INTO ncbi_metadata VALUES (1,'soil metagenome'),(2,'Soil_Metagenome'),(3,'rhizosphere metagenome'),"
                "(4,'soil metagenome'),(5,'pig gut metagenome'),(6,'mystery metagenome'),(7,'soil metagenome')")
    con.execute("INSERT INTO indicator_habitat_scores VALUES (1,'soil',0.4),(2,'soil',0.2),(5,'mammalian gut',0.5),"
                "(6,'soil',0.9),(7,'marine water',0.3)")
    con.execute("INSERT INTO indicator_habitat_genus_scores VALUES (1,'soil','A',0.3),(1,'soil','B',0.1),"
                "(2,'soil','A',0.2),(5,'mammalian gut','C',0.5),(6,'soil','A',0.9),(7,'marine water','D',0.3)")
    con.close()


def test_indicpiper_by_habitat_averages_over_every_run_of_the_group_zeros_included(tmp_path):
    db = tmp_path / 'site.duckdb'
    _indicpiper_database(db)
    soil = summarise_groups.indicpiper_by_habitat(str(db))['soil']
    # runs 1, 2, 3, 4 and 7 are recorded as soil; 1 and 2 matched (run 6 has no habitat, so it is not counted)
    assert soil['runs'] == 5 and soil['matched_runs'] == 2
    assert soil['mean_abundance'] == pytest.approx((0.4 + 0.2) / 5)
    assert soil['mean_genera'] == pytest.approx(3 / 5)
    assert soil['mean_abundance_matched'] == pytest.approx(0.3)
    assert soil['mean_genera_matched'] == pytest.approx(1.5)


def test_indicpiper_by_habitat_pools_host_guts_into_mammalian_gut(tmp_path):
    db = tmp_path / 'site.duckdb'
    _indicpiper_database(db)
    gut = summarise_groups.indicpiper_by_habitat(str(db))['mammalian gut']
    assert gut['runs'] == 1 and gut['matched_runs'] == 1 and gut['mean_genera'] == 1


def test_indicpiper_by_habitat_lists_a_habitat_with_scores_but_no_recorded_runs(tmp_path):
    db = tmp_path / 'site.duckdb'
    _indicpiper_database(db)
    water = summarise_groups.indicpiper_by_habitat(str(db))['marine water']
    assert water['runs'] == 0 and water['matched_runs'] == 0
    assert water['mean_abundance'] is None and water['mean_abundance_matched'] is None


def test_indicpiper_by_habitat_counts_marine_and_seawater_labels_as_marine_water(tmp_path):
    duckdb = pytest.importorskip('duckdb')
    db = tmp_path / 'site.duckdb'
    con = duckdb.connect(str(db))
    con.execute('CREATE TABLE ncbi_metadata (id INTEGER, taxon_name VARCHAR)')
    con.execute('CREATE TABLE indicator_habitat_scores (run_id INTEGER, habitat VARCHAR, score DOUBLE)')
    con.execute('CREATE TABLE indicator_habitat_genus_scores (run_id INTEGER, habitat VARCHAR, genus VARCHAR, relative_abundance DOUBLE)')
    con.execute("INSERT INTO ncbi_metadata VALUES (1,'marine metagenome'),(2,'seawater metagenome'),(3,'marine metagenome'),"
                "(4,'canine gut metagenome')")
    con.execute("INSERT INTO indicator_habitat_scores VALUES (1,'marine water',0.4),(2,'marine water',0.2)")
    con.execute("INSERT INTO indicator_habitat_genus_scores VALUES (1,'marine water','A',0.4),(2,'marine water','A',0.2)")
    con.close()
    result = summarise_groups.indicpiper_by_habitat(str(db))
    water = result['marine water']
    assert water['runs'] == 3 and water['matched_runs'] == 2
    assert water['mean_abundance'] == pytest.approx((0.4 + 0.2) / 3)
    # Table S4 has no canine gut label, so those runs belong to no habitat.
    assert result['mammalian gut']['runs'] == 0


def test_indicpiper_by_habitat_uses_the_map_shared_with_the_site():
    labels = summarise_groups.indicpiper_label_habitats()
    assert labels['soil metagenome'] == 'soil' and labels['pig gut metagenome'] == 'mammalian gut'


@pytest.mark.parametrize('label, expected', [
    ('soil metagenome', 'soil metagenome'),
    ('Soil_Metagenome', 'soil metagenome'),
    ('  soil   metagenome  ', 'soil metagenome'),
    ('soil metagenome from a field', 'soil metagenome'),
    ('', ''),
    ('uncultured bacterium', 'uncultured bacterium'),
])
def test_canonical_organism_matches_the_websites_comparison(label, expected):
    assert summarise_groups.canonical_organism(label) == expected


def test_indicpiper_by_habitat_ignores_runs_without_a_label_and_takes_a_custom_map(tmp_path):
    duckdb = pytest.importorskip('duckdb')
    db = tmp_path / 'site.duckdb'
    con = duckdb.connect(str(db))
    con.execute('CREATE TABLE ncbi_metadata (id INTEGER, taxon_name VARCHAR)')
    con.execute('CREATE TABLE indicator_habitat_scores (run_id INTEGER, habitat VARCHAR, score DOUBLE)')
    con.execute('CREATE TABLE indicator_habitat_genus_scores (run_id INTEGER, habitat VARCHAR, genus VARCHAR, relative_abundance DOUBLE)')
    con.execute("INSERT INTO ncbi_metadata VALUES (1,'cave metagenome'),(2,NULL)")
    con.execute("INSERT INTO indicator_habitat_scores VALUES (1,'cave',0.5)")
    con.execute("INSERT INTO indicator_habitat_genus_scores VALUES (1,'cave','A',0.5)")
    con.close()
    result = summarise_groups.indicpiper_by_habitat(str(db), {'cave metagenome': 'cave'})
    assert result['cave']['runs'] == 1 and result['cave']['mean_abundance'] == pytest.approx(0.5)


def test_indicpiper_genera_are_grouped_by_habitat_strongest_first():
    sys.path.insert(0, BIN)
    from export_indicpiper_genera import genera_by_habitat
    rows = [{'Taxonomy': 'Bacteria; P1; C; O; F; Aaa', 'Habitat': 'soil', 'IndVal_mean': '0.4'},
            {'Taxonomy': 'Bacteria; P2; C; O; F; Bbb', 'Habitat': 'soil', 'IndVal_mean': '0.61234'},
            {'Taxonomy': 'Archaea; P3; C; O; F; Ccc', 'Habitat': 'glacier', 'IndVal_mean': '0.5'}]
    result = genera_by_habitat(rows)
    assert list(result) == ['glacier', 'soil']
    assert result['soil'] == [{'genus': 'Bbb', 'phylum': 'P2', 'indval': 0.612}, {'genus': 'Aaa', 'phylum': 'P1', 'indval': 0.4}]
