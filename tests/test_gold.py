import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api import gold  # noqa: E402

PROJECT = {
    'projectGoldId': 'Gp0119859', 'projectName': 'Utica-2', 'studyGoldId': 'Gs0114675', 'biosampleGoldId': 'Gb0119269',
    'ncbiBioProjectAccession': 'PRJNA375207', 'ncbiBioSampleAccession': 'SAMN06343775',
    'projectStatus': 'Permanent Draft', 'sequencingStatus': 'Complete', 'seqMethod': ['Illumina HiSeq 2500-1TB'],
    'sequencingCenters': ['DOE Joint Genome Institute (JGI)'], 'jgiFundingProgram': 'CSP', 'jgiFundingYear': 2015,
    'contacts': [{'name': 'A PI', 'email': 'pi@example.org', 'roles': ['PI']}],
    'genomePublications': [{'pubmedId': 30510171, 'doi': '10.1038/s41564-018-0312-6', 'title': 'Viruses control.',
                            'journalName': 'Nat Microbiol', 'publicationDate': '2019-02-01'}],
    'otherPublications': [],
}
BIOSAMPLE = {
    'biosampleGoldId': 'Gb0119269', 'ecosystem': 'Environmental', 'ecosystemCategory': 'Aquatic',
    'ecosystemType': 'Deep subsurface', 'ecosystemSubtype': 'Shale gas/oil reservoir', 'specificEcosystem': None,
    'geographicLocation': 'USA: Ohio', 'latitude': 40.178, 'longitude': -81.073, 'dateCollected': '2014-12-03',
    'depthInMeters': 2000, 'ph': '5.8', 'salinityConcentration': '148300 mg/L', 'sampleCollectionTemperature': '65 C',
    'envoMedium': {'id': 'ENVO_00002194', 'label': 'oil field production water'}, 'contacts': [{'email': 'x@y.z'}],
}
STUDY = {'studyGoldId': 'Gs0114675', 'studyName': 'Deep subsurface shale', 'description': 'Long description.'}


def test_project_id_is_found_among_attribute_values_and_junk_is_ignored():
    assert gold.find_project_id(['APXWU', 'Gp0119859', 'PRJNA1']) == 'Gp0119859'
    assert gold.find_project_id(['gp0119859x', 'Gp12', 'Gb0119269', '', None]) is None
    assert gold.find_project_id([]) is None


def test_rows_are_blue_tagged_gold_rows_with_descriptions_and_no_empty_values():
    rows = gold.build_rows(PROJECT, BIOSAMPLE, STUDY)
    by_key = {row['k']: row for row in rows}
    assert all(row['source'] == 'gold' and row['description'] and row['is_custom'] is False for row in rows)
    assert by_key['GOLD ecosystem path']['v'] == 'Environmental > Aquatic > Deep subsurface > Shale gas/oil reservoir'
    assert by_key['GOLD pH']['v'] == '5.8'
    assert by_key['GOLD depth']['v'] == '2000 m'
    assert by_key['GOLD ENVO medium']['v'] == 'oil field production water (ENVO_00002194)'
    assert by_key['GOLD study']['v'] == 'Deep subsurface shale'
    assert 'GOLD specific ecosystem' not in by_key  # empty in GOLD, so not shown


def test_rows_never_carry_contact_names_or_emails():
    text = repr(gold.build_rows(PROJECT, BIOSAMPLE, STUDY))
    assert 'example.org' not in text and 'x@y.z' not in text and 'A PI' not in text


def test_rows_tolerate_missing_biosample_and_study():
    rows = gold.build_rows(PROJECT, None, None)
    assert {row['k'] for row in rows} >= {'GOLD project ID', 'GOLD project status'}


def test_publications_are_deduplicated_and_link_to_pubmed_and_doi():
    project = {**PROJECT, 'otherPublications': PROJECT['genomePublications'] + [{'pubmedId': None, 'doi': '10.1/x', 'title': 'T'}]}
    pubs = gold.build_publications(project)
    assert [p['pubmed_id'] for p in pubs] == ['30510171', None]
    assert pubs[0]['doi'] == '10.1038/s41564-018-0312-6' and pubs[0]['journal'] == 'Nat Microbiol'
    assert pubs[1]['doi'] == '10.1/x'


def test_summary_has_rows_publications_and_a_gold_link():
    summary = gold.build_summary(PROJECT, BIOSAMPLE, STUDY)
    assert summary['project_id'] == 'Gp0119859'
    assert summary['url'] == 'https://gold.jgi.doe.gov/project?id=Gp0119859'
    assert summary['rows'] and summary['publications']


def test_client_without_a_token_is_unavailable():
    with pytest.raises(gold.GoldUnavailable):
        gold.GoldClient('').fetch('projects', projectGoldId='Gp1')


def test_throttle_spaces_requests_by_the_minimum_interval():
    clock = {'now': 100.0, 'slept': []}
    throttle = gold.Throttle(1.0, now=lambda: clock['now'], sleep=lambda s: clock['slept'].append(s))
    throttle.wait()
    clock['now'] += 0.25
    throttle.wait()
    assert clock['slept'] == [pytest.approx(0.75)]


def _rows(**values):
    return [{'k': k.replace('_', ' '), 'v': v, 'source': 'gold'} for k, v in values.items()]


def _peer(**values):
    return {'rows': _rows(**values)}


def test_rows_are_tagged_like_the_other_sample_information_rows():
    rows = _rows(GOLD_pH='5.8', GOLD_habitat='soil', GOLD_ENVO_medium='water', GOLD_project_ID='Gp1')
    peers = [_peer(GOLD_pH='7.1', GOLD_habitat='soil', GOLD_project_ID='Gp2'),
             _peer(GOLD_pH='7.1', GOLD_habitat='soil', GOLD_project_ID='Gp3')]
    tagged = {row['k']: row.get('difference') for row in gold.tag_differences(rows, peers)}
    assert tagged == {'GOLD pH': 'differs', 'GOLD habitat': None, 'GOLD ENVO medium': 'only_here', 'GOLD project ID': 'expected'}


def test_nothing_is_tagged_without_peers_and_the_rows_are_untouched():
    rows = _rows(GOLD_pH='5.8')
    assert gold.tag_differences(rows, []) == rows
    assert 'difference' not in rows[0]


def test_tagging_returns_new_rows_and_leaves_the_inputs_alone():
    rows = _rows(GOLD_pH='5.8')
    tagged = gold.tag_differences(rows, [_peer(GOLD_pH='7.1')])
    assert tagged[0]['difference'] == 'differs' and 'difference' not in rows[0]


def test_host_body_site_and_other_extra_fields_are_included():
    biosample = {**BIOSAMPLE, 'hostName': 'Homo sapiens', 'hostGender': 'female', 'sampleBodySite': 'Gastrointestinal tract',
                 'oxygenConcentration': '2 mg/L', 'elevationInMeters': 10, 'elevationInMeters2': 20,
                 'longhurst': {'code': 'NADR', 'description': 'North Atlantic Drift'}, 'hostDiseases': ['asthma', 'flu'],
                 'isoCountry': 'USA'}
    by_key = {row['k']: row['v'] for row in gold.build_rows(PROJECT, biosample, STUDY)}
    assert by_key['GOLD host'] == 'Homo sapiens' and by_key['GOLD host sex'] == 'female'
    assert by_key['GOLD body site'] == 'Gastrointestinal tract' and by_key['GOLD oxygen'] == '2 mg/L'
    assert by_key['GOLD elevation'] == '10-20 m' and by_key['GOLD Longhurst province'] == 'NADR (North Atlantic Drift)'
    assert by_key['GOLD host diseases'] == 'asthma, flu' and by_key['GOLD country'] == 'USA'


def test_csv_pairs_list_every_row_and_the_publications():
    summary = gold.build_summary(PROJECT, BIOSAMPLE, STUDY)
    pairs = dict(gold.csv_pairs(summary))
    assert pairs['GOLD pH'] == '5.8' and pairs['GOLD ecosystem path'].startswith('Environmental > Aquatic')
    assert pairs['GOLD publication PubMed IDs'] == '30510171'
    assert pairs['GOLD publication DOIs'] == '10.1038/s41564-018-0312-6'
    assert pairs['GOLD project URL'] == 'https://gold.jgi.doe.gov/project?id=Gp0119859'


def test_csv_pairs_leave_out_publication_columns_when_there_are_none():
    summary = gold.build_summary({**PROJECT, 'genomePublications': []}, BIOSAMPLE, STUDY)
    labels = [label for label, _ in gold.csv_pairs(summary)]
    assert 'GOLD publication PubMed IDs' not in labels and 'GOLD publication DOIs' not in labels
