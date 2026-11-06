import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api.bioproject_similarity import compare_to_peers  # noqa: E402

RUN = {'Organism': 'soil metagenome', 'Depth': 5, 'Instrument': 'NovaSeq', 'Country': 'Chile'}


def test_identical_runs_share_everything():
    result = compare_to_peers(RUN, [dict(RUN), dict(RUN)])
    assert result == {'n_other_runs': 2, 'n_fields': 4, 'percent_shared': 100, 'unique_fields': [],
                      'only_here_fields': []}


def test_differing_field_is_unique():
    peers = [{**RUN, 'Depth': 10}, {**RUN, 'Depth': 10}]
    result = compare_to_peers(RUN, peers)
    assert result['unique_fields'] == ['Depth']
    assert result['percent_shared'] == 75


def test_run_with_no_peers_has_no_comparison():
    assert compare_to_peers(RUN, []) is None


def test_blank_values_are_not_comparable():
    run = {**RUN, 'Country': None, 'Depth': ' '}
    peers = [{**RUN, 'Country': 'Peru'}]
    result = compare_to_peers(run, peers)
    assert result['unique_fields'] == []
    assert result['n_fields'] == 2


def test_field_missing_on_every_peer_is_not_comparable():
    result = compare_to_peers(RUN, [{'Organism': 'soil metagenome'}])
    assert result['n_fields'] == 1
    assert result['percent_shared'] == 100


def test_matches_most_common_peer_value_ignoring_case_and_type():
    peers = [{'Depth': '5', 'Organism': 'Soil Metagenome'}, {'Depth': '5', 'Organism': 'other'},
             {'Depth': '9', 'Organism': 'other'}]
    result = compare_to_peers({'Depth': 5.0, 'Organism': 'soil metagenome'}, peers)
    assert result['unique_fields'] == ['Organism']  # 'other' is the most common peer value


def test_no_comparable_fields_returns_none():
    assert compare_to_peers({'Depth': None}, [{'Depth': 5}]) is None


def test_field_no_peer_has_is_only_here():
    result = compare_to_peers(RUN, [{'Organism': 'soil metagenome', 'Country': 'Chile'}])
    assert result['only_here_fields'] == ['Depth', 'Instrument']
    assert result['unique_fields'] == []


def test_only_here_fields_are_left_out_of_the_shared_percentage():
    result = compare_to_peers(RUN, [{'Organism': 'soil metagenome', 'Country': 'Peru'}])
    assert result['n_fields'] == 2
    assert result['percent_shared'] == 50


def test_run_with_only_only_here_fields_still_reports_them():
    result = compare_to_peers({'Depth': 5}, [{'Country': 'Peru'}])
    assert result['only_here_fields'] == ['Depth']
    assert result['percent_shared'] is None
