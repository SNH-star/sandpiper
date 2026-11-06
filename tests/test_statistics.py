import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api.api import statistics_payload  # noqa: E402

HOST = {'host': 600, 'ecological': 300, None: 100}
YEARS = [('2021', 10), ('2020', 5), (None, 3), ('2022', 20)]
TOP_TAXA = {'gtdb': {'genus': [('g__Small', 10, 5), ('g__Big', 400, 100), ('g__Gap', None, 50)]}}
COVERAGE = {'coordinates': 500, 'metalog': 150, 'indicpiper': 900, 'low_complexity': 80}


def _payload(**overrides):
    args = dict(total_runs=1000, bioprojects=40, terabases=12.34, host_counts=HOST,
                release_years=YEARS, coverage_counts=COVERAGE, top_taxa=TOP_TAXA)
    return statistics_payload(**{**args, **overrides})


def test_totals_are_passed_through():
    totals = _payload()['totals']
    assert totals == {'runs': 1000, 'bioprojects': 40, 'terabases': 12.3}


def test_host_split_is_ordered_with_one_decimal_percentages():
    split = _payload()['sample_types']
    assert [row['key'] for row in split] == ['host_associated', 'ecological', 'unclassified']
    assert [row['runs'] for row in split] == [600, 300, 100]
    assert [row['percent'] for row in split] == [60.0, 30.0, 10.0]


def test_release_years_are_sorted_and_skip_missing_years():
    assert _payload()['release_years'] == [
        {'year': 2020, 'runs': 5}, {'year': 2021, 'runs': 10}, {'year': 2022, 'runs': 20}]


def test_coverage_rows_carry_count_and_percent_in_a_fixed_order():
    rows = _payload()['coverage']
    assert [row['key'] for row in rows] == ['coordinates', 'metalog', 'indicpiper', 'low_complexity']
    assert [row['percent'] for row in rows] == [50.0, 15.0, 90.0, 8.0]


def test_missing_coverage_count_is_reported_as_unavailable_not_zero():
    rows = _payload(coverage_counts={**COVERAGE, 'indicpiper': None})['coverage']
    indicpiper = next(row for row in rows if row['key'] == 'indicpiper')
    assert indicpiper['runs'] is None and indicpiper['percent'] is None


def test_empty_database_does_not_divide_by_zero():
    payload = _payload(total_runs=0, host_counts={}, release_years=[], coverage_counts={})
    assert all(row['percent'] == 0 for row in payload['sample_types'])
    assert payload['release_years'] == []


def test_top_taxa_are_sorted_by_runs_with_host_and_ecological_parts():
    rows = _payload()['top_taxa']['gtdb']['genus']
    assert [row['name'] for row in rows] == ['g__Big', 'g__Gap', 'g__Small']
    assert rows[0] == {'name': 'g__Big', 'host': 400, 'ecological': 100, 'runs': 500, 'percent': 50.0}


def test_missing_taxon_counts_are_treated_as_zero():
    gap = next(row for row in _payload()['top_taxa']['gtdb']['genus'] if row['name'] == 'g__Gap')
    assert (gap['host'], gap['ecological'], gap['runs']) == (0, 50, 50)


from api.api import known_species_payload  # noqa: E402

KSF_HISTOGRAM = [(0, 'host', 30), (1, 'host', 70), (19, 'ecological', 10), (0, 'ecological', 10), (5, None, 99)]


def _distribution(**overrides):
    args = dict(histogram_rows=KSF_HISTOGRAM, bins=20)
    return known_species_payload(**{**args, **overrides})['distribution']


def test_distribution_is_the_share_of_each_groups_runs_in_every_band():
    distribution = _distribution()
    assert distribution['bin_width'] == 5
    host = distribution['host_associated']
    assert len(host) == 20 and host[0] == {'start': 0, 'percent': 30.0} and host[1] == {'start': 5, 'percent': 70.0}
    assert sum(row['percent'] for row in host) == 100
    ecological = distribution['ecological']
    assert ecological[0]['percent'] == 50.0 and ecological[19] == {'start': 95, 'percent': 50.0}


def test_runs_with_no_host_or_ecological_call_are_left_out_of_the_distribution():
    distribution = _distribution()
    assert all(row['percent'] == 0 for row in distribution['host_associated'][5:6])


def test_distribution_of_an_empty_group_is_all_zero():
    distribution = _distribution(histogram_rows=[(3, 'host', 5)])
    assert all(row['percent'] == 0 for row in distribution['ecological'])


from api.statistics_figures import map_cells_payload, year_breakdown_payload  # noqa: E402


def test_year_breakdown_accumulates_and_skips_missing_years():
    calls = [(2020, 'host', 5), (2020, None, 5), (2021, 'ecological', 10), (None, 'host', 99)]
    years = year_breakdown_payload(calls)['years']
    assert [row['cumulative'] for row in years] == [10, 20]
    assert years[0] == {'year': 2020, 'host_associated': 5, 'ecological': 0, 'unclassified': 5, 'cumulative': 10}


def test_map_cells_carry_sample_type_counts_and_percent_known():
    cells = map_cells_payload([(10, 20, 10, 6, 3, 0.456), (0, 0, 1, 0, 0, None)])['cells']
    assert cells[0] == {'lat': 10, 'lon': 20, 'runs': 10, 'host_associated': 6, 'ecological': 3, 'known': 45.6}
    assert cells[1]['known'] is None


def test_database_versions_report_metalog_date_and_indicpiper_version():
    from api.api import database_versions
    assert database_versions('2026-03-03T10:15:00+10:00', '2') == {
        'metalog_collected_date': '3 March 2026', 'indicpiper_version': '2'}


def test_database_versions_leave_missing_values_null():
    from api.api import database_versions
    assert database_versions(None, None) == {'metalog_collected_date': None, 'indicpiper_version': None}
    assert database_versions('not a date', '2')['metalog_collected_date'] is None
