import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api.indicpiper_warnings import classify_organism, mapped_organisms, count_cautions  # noqa: E402
from api.api import statistics_payload  # noqa: E402


def test_organism_naming_a_covered_habitat_expects_that_habitat():
    assert classify_organism('soil metagenome') == ('expected', 'soil')
    assert classify_organism('Human_Gut  metagenome') == ('expected', 'mammalian gut')
    assert classify_organism('human skin metagenome extra words') == ('expected', 'human skin')


def test_organism_outside_the_habitat_list_is_uncovered():
    assert classify_organism('plant metagenome') == ('uncovered', None)
    assert classify_organism('mouse gut metagenome') == ('uncovered', None)


def test_missing_or_unspecified_organism_gives_no_warning():
    for organism in (None, '', '   ', 'unspecified', float('nan')):
        assert classify_organism(organism) == ('none', None)


def test_mapped_organisms_keep_only_those_with_an_expected_habitat():
    counts = {'soil metagenome': 5, 'plant metagenome': 3, None: 2, 'Soil Metagenome': 1}
    assert mapped_organisms(counts) == {'soil metagenome': 'soil', 'Soil Metagenome': 'soil'}


def test_cautions_count_uncovered_runs_and_mismatches():
    counts = {'soil metagenome': 5, 'plant metagenome': 3, None: 2}
    # 3 uncovered runs, plus 2 of the 5 soil runs whose strongest signal is another habitat.
    assert count_cautions(counts, mismatched_runs=2) == 5


def test_coverage_row_for_indicpiper_splits_clear_and_caution_runs():
    payload = statistics_payload(
        total_runs=1000, bioprojects=1, terabases=1.0, host_counts={}, release_years=[],
        coverage_counts={'indicpiper': 900}, top_taxa={}, indicpiper_caution=300)
    row = next(item for item in payload['coverage'] if item['key'] == 'indicpiper')
    assert (row['clear_runs'], row['caution_runs']) == (600, 300)
    assert (row['clear_percent'], row['caution_percent']) == (60.0, 30.0)


def test_other_coverage_rows_have_no_split():
    payload = statistics_payload(
        total_runs=1000, bioprojects=1, terabases=1.0, host_counts={}, release_years=[],
        coverage_counts={'coordinates': 500}, top_taxa={}, indicpiper_caution=300)
    row = next(item for item in payload['coverage'] if item['key'] == 'coordinates')
    assert 'caution_runs' not in row


def test_indicpiper_split_is_absent_when_the_caution_count_is_unknown():
    payload = statistics_payload(
        total_runs=1000, bioprojects=1, terabases=1.0, host_counts={}, release_years=[],
        coverage_counts={'indicpiper': 900}, top_taxa={})
    row = next(item for item in payload['coverage'] if item['key'] == 'indicpiper')
    assert 'caution_runs' not in row
