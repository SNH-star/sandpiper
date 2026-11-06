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
