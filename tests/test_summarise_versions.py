import importlib.util
import os

import numpy as np
import pandas as pd

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'backend', 'bin', 'summarise_versions.py')
spec = importlib.util.spec_from_file_location('summarise_versions', SCRIPT)
summarise_versions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summarise_versions)


def test_histogram_shares_sum_to_100_and_clip_the_top_bin():
    result = summarise_versions.histogram(pd.Series([1.0, 2.0, 50.0, 99.0, 500.0]), np.arange(0, 105, 5))
    assert round(sum(result['percent']), 1) == 100.0
    assert result['percent'][-1] == 40.0
    assert result['runs'] == 5


def test_histogram_of_missing_column_is_none():
    assert summarise_versions.histogram(pd.Series(dtype=float), np.arange(0, 11)) is None


def test_summarise_counts_calls_and_skips_absent_known_fraction():
    frame = pd.DataFrame({'host_or_not': ['host', 'ecological', None, 'host'],
                          'average_bacterial_archaeal_genome_size': [3e6] * 4,
                          'metagenome_size': [1e9] * 4})
    result = summarise_versions.summarise(frame)
    assert (result['runs'], result['host_associated'], result['ecological'], result['unclassified']) == (4, 2, 1, 1)
    assert result['known_species_fraction'] is None
    assert result['genome_size_mb']['median'] == 3.0


def test_old_spf_column_is_renamed():
    frame = pd.DataFrame({'singlem prokaryotic fraction (SPF)': [1.0], 'host_or_not': ['host']})
    assert summarise_versions.summarise(frame)['runs'] == 1


def test_keep_website_runs_drops_blacklisted_and_metadata_less_runs():
    frame = pd.DataFrame({'sample': ['A', 'B', 'C', 'D']})
    kept = summarise_versions.keep_website_runs(frame, {'B'}, {'A', 'B', 'D'})
    assert list(kept['sample']) == ['A', 'D']


def test_summarise_reports_rows_before_filtering():
    frame = pd.DataFrame({'host_or_not': ['host']})
    assert summarise_versions.summarise(frame, summary_rows=5)['summary_rows'] == 5


def test_groups_need_the_exact_label_and_the_matching_host_call():
    frame = pd.DataFrame({
        'organism': ['mouse metagenome', 'mouse gut metagenome', 'Mouse metagenome', 'mouse metagenome', 'soil metagenome'],
        'host_or_not': ['host', 'host', 'host', 'ecological', 'ecological'],
        'known_species_fraction': [90.0, 80.0, 70.0, 60.0, 10.0]})
    result = summarise_versions.summarise(frame)
    # "mouse gut metagenome" counts as mouse; "Mouse metagenome" (wrong case) and the wrong host call do not.
    assert result['host_groups']['mouse']['runs'] == 2
    assert result['host_groups']['mouse']['median'] == 85.0
    assert result['host_groups']['human'] is None
    assert result['ecological_groups']['soil']['runs'] == 1
    assert result['ecological_groups']['marine'] is None


def test_gut_label_counts_for_animal_groups_but_not_for_soil():
    frame = pd.DataFrame({
        'organism': ['soil gut metagenome', 'soil metagenome'],
        'host_or_not': ['ecological', 'ecological'],
        'known_species_fraction': [10.0, 20.0]})
    assert summarise_versions.summarise(frame)['ecological_groups']['soil']['runs'] == 1


def test_spf_is_summarised_per_group_with_the_same_rules_as_known_species():
    frame = pd.DataFrame({
        'organism': ['mouse metagenome', 'mouse gut metagenome', 'soil metagenome', 'soil metagenome'],
        'host_or_not': ['host', 'host', 'ecological', 'host'],
        'known_species_fraction': [90.0, 80.0, 10.0, 20.0],
        'singlem_prokaryotic_fraction': [40.0, 99.0, 70.0, 5.0]})
    result = summarise_versions.summarise(frame)
    assert result['spf_host_groups']['mouse']['runs'] == 2
    assert result['spf_host_groups']['mouse']['median'] == 69.5
    assert result['spf_host_groups']['human'] is None
    assert result['spf_ecological_groups']['soil']['median'] == 70.0
    # The known species histograms are unchanged by the new measure.
    assert result['host_groups']['mouse']['median'] == 85.0


def test_spf_groups_are_none_when_the_column_is_absent():
    frame = pd.DataFrame({'organism': ['mouse metagenome'], 'host_or_not': ['host'], 'known_species_fraction': [90.0]})
    result = summarise_versions.summarise(frame)
    assert all(value is None for value in result['spf_host_groups'].values())


def test_a_blank_host_call_falls_back_to_the_prediction_like_the_website():
    frame = pd.DataFrame({
        'host_or_not': ['host', None, None, None, 'ecological'],
        'prediction': ['ecological', 'host', 'ecological', None, 'host']})
    result = summarise_versions.summarise(frame)
    # The recorded call wins over the prediction; blanks take the prediction; no prediction stays unclassified.
    assert result['host_associated'] == 2
    assert result['ecological'] == 2
    assert result['unclassified'] == 1


def test_older_summaries_without_a_prediction_column_still_count_blanks_as_unclassified():
    frame = pd.DataFrame({'host_or_not': ['host', None]})
    result = summarise_versions.summarise(frame)
    assert (result['host_associated'], result['ecological'], result['unclassified']) == (1, 0, 1)


def test_old_summaries_take_the_known_fraction_from_species_coverage():
    # 1.1.9 stored the known species fraction as a 0-1 share in `species_coverage`.
    frame = pd.DataFrame({'host_or_not': ['host'] * 3, 'species_coverage': [0.5, 0.9, 1.0],
                          'root_coverage': [100.0, 200.0, 300.0]})
    result = summarise_versions.summarise(frame)
    assert result['known_species_fraction']['runs'] == 3
    assert result['known_species_fraction']['median'] == 90.0


def test_species_coverage_is_not_a_fraction_when_a_real_column_or_large_values_exist():
    # 1.1.10 and later hold coverage (values above 1) in `species_coverage`; the real column wins.
    coverage = pd.DataFrame({'host_or_not': ['host'], 'species_coverage': [250.0]})
    assert summarise_versions.summarise(coverage)['known_species_fraction'] is None
    both = pd.DataFrame({'host_or_not': ['host'], 'species_coverage': [0.5], 'known_species_fraction': [70.0]})
    assert summarise_versions.summarise(both)['known_species_fraction']['median'] == 70.0


def _previous(blacklist_sha='abc', labels=('2.0.0', '1.1.10')):
    return {'blacklist_sha256': blacklist_sha,
            'versions': [{'label': label, 'gtdb': 'R232', 'runs': 1} for label in labels]}


def test_earlier_versions_are_reused_when_label_gtdb_and_blacklist_match():
    reused = summarise_versions.reusable_versions(_previous(), 'abc', skip_label='2.2.0')
    assert set(reused) == {('2.0.0', 'R232'), ('1.1.10', 'R232')}


def test_nothing_is_reused_when_the_blacklist_changed_or_was_never_recorded():
    assert summarise_versions.reusable_versions(_previous('old'), 'new', skip_label='2.2.0') == {}
    assert summarise_versions.reusable_versions({'versions': _previous()['versions']}, 'new', skip_label='2.2.0') == {}


def test_the_new_build_is_never_reused_even_if_its_label_was_summarised_before():
    reused = summarise_versions.reusable_versions(_previous(labels=('2.2.0', '2.0.0')), 'abc', skip_label='2.2.0')
    assert set(reused) == {('2.0.0', 'R232')}


def test_main_computes_only_the_versions_that_are_not_reused(tmp_path, monkeypatch):
    import json
    blacklist = tmp_path / 'blacklist.csv'
    blacklist.write_text('')
    previous = tmp_path / 'previous.json'
    previous.write_text(json.dumps({
        'blacklist_sha256': summarise_versions.file_sha256(str(blacklist)),
        'versions': [{'label': '2.0.0', 'gtdb': 'R232', 'runs': 7, 'cached': True}]}))
    summary = tmp_path / 'summary.csv'
    pd.DataFrame({'sample': ['SRR1'], 'host_or_not': ['host']}).to_csv(summary, index=False)
    metadata = tmp_path / 'meta.tsv'
    pd.DataFrame({'run': ['SRR1']}).to_csv(metadata, sep='\t', index=False)
    out = tmp_path / 'out.json'
    summarise_versions.main(['x', str(out), str(blacklist), '--reuse', str(previous),
                             f'2.2.0:R232:{summary}:{metadata}', f'2.0.0:R232:/missing.csv:/missing.tsv'])
    written = json.loads(out.read_text())
    assert [v['label'] for v in written['versions']] == ['2.2.0', '2.0.0']
    assert written['versions'][1].get('cached') is True
    assert written['blacklist_sha256'] == summarise_versions.file_sha256(str(blacklist))
