import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'bin'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import fetch_gold  # noqa: E402
from api.gold import GoldUnavailable  # noqa: E402


class FakeClient:
    """Answers from a dict keyed by (endpoint, id); raises for ids listed in ``broken``."""

    def __init__(self, records, broken=(), slow_once=()):
        self.records, self.broken, self.calls = records, set(broken), []
        self.slow_once = set(slow_once)

    def fetch(self, path, **params):
        (_, gold_id), = params.items()
        self.calls.append((path, gold_id))
        if gold_id in self.broken:
            raise GoldUnavailable('GOLD answered HTTP 500', status=500)
        if gold_id in self.slow_once:
            self.slow_once.discard(gold_id)
            raise GoldUnavailable('GOLD answered HTTP 429', status=429)
        record = self.records.get((path, gold_id))
        if path == 'analysis_projects':
            return record or []
        return [record] if record else []


def test_strip_contacts_removes_contacts_at_any_depth():
    record = {'projectGoldId': 'Gp1', 'contacts': [{'email': 'a@b'}],
              'genomePublications': [{'title': 't', 'contacts': ['x']}]}
    assert fetch_gold.strip_contacts(record) == {'projectGoldId': 'Gp1', 'genomePublications': [{'title': 't'}]}


def test_fetch_all_saves_every_record_type_and_all_fields(tmp_path):
    records = {
        ('projects', 'Gp1'): {'projectGoldId': 'Gp1', 'biosampleGoldId': 'Gb1', 'studyGoldId': 'Gs1',
                              'extraField': 'kept', 'contacts': [{'email': 'a@b'}]},
        ('biosamples', 'Gb1'): {'biosampleGoldId': 'Gb1', 'ph': '7'},
        ('studies', 'Gs1'): {'studyGoldId': 'Gs1', 'studyName': 'S'},
    }
    client = FakeClient(records)
    fetch_gold.fetch_all(['Gp1'], client, str(tmp_path), max_seconds=None)
    saved = fetch_gold.read_records(str(tmp_path), 'projects')
    assert saved['Gp1']['extraField'] == 'kept' and 'contacts' not in saved['Gp1']
    assert fetch_gold.read_records(str(tmp_path), 'biosamples')['Gb1']['ph'] == '7'
    assert fetch_gold.read_records(str(tmp_path), 'studies')['Gs1']['studyName'] == 'S'


def test_second_run_resumes_without_refetching(tmp_path):
    records = {('projects', 'Gp1'): {'projectGoldId': 'Gp1'}}
    fetch_gold.fetch_all(['Gp1'], FakeClient(records), str(tmp_path), max_seconds=None)
    again = FakeClient(records)
    fetch_gold.fetch_all(['Gp1'], again, str(tmp_path), max_seconds=None)
    assert again.calls == []


def test_shared_study_is_fetched_once(tmp_path):
    records = {('projects', 'Gp1'): {'projectGoldId': 'Gp1', 'studyGoldId': 'Gs1'},
               ('projects', 'Gp2'): {'projectGoldId': 'Gp2', 'studyGoldId': 'Gs1'},
               ('studies', 'Gs1'): {'studyGoldId': 'Gs1'}}
    client = FakeClient(records)
    fetch_gold.fetch_all(['Gp1', 'Gp2'], client, str(tmp_path), max_seconds=None)
    assert client.calls.count(('studies', 'Gs1')) == 1


def test_failed_id_is_retried_on_next_run_and_not_lost(tmp_path):
    records = {('projects', 'Gp1'): {'projectGoldId': 'Gp1'}, ('projects', 'Gp2'): {'projectGoldId': 'Gp2'}}
    report = fetch_gold.fetch_all(['Gp1', 'Gp2'], FakeClient(records, broken=['Gp1']), str(tmp_path), max_seconds=None)
    assert report['failed'] == 1
    assert set(fetch_gold.read_records(str(tmp_path), 'projects')) == {'Gp2'}
    fetch_gold.fetch_all(['Gp1', 'Gp2'], FakeClient(records), str(tmp_path), max_seconds=None)
    assert set(fetch_gold.read_records(str(tmp_path), 'projects')) == {'Gp1', 'Gp2'}


def test_project_unknown_to_gold_is_remembered_as_missing(tmp_path):
    fetch_gold.fetch_all(['Gp9'], FakeClient({}), str(tmp_path), max_seconds=None)
    again = FakeClient({})
    fetch_gold.fetch_all(['Gp9'], again, str(tmp_path), max_seconds=None)
    assert again.calls == []
    with open(os.path.join(str(tmp_path), 'projects.jsonl')) as handle:
        assert json.loads(handle.readline()) == {'id': 'Gp9', 'record': None}


def test_stops_when_time_budget_is_spent(tmp_path):
    records = {('projects', 'Gp%d' % i): {'projectGoldId': 'Gp%d' % i} for i in range(5)}
    report = fetch_gold.fetch_all(['Gp%d' % i for i in range(5)], FakeClient(records), str(tmp_path), max_seconds=0)
    assert report['stopped_early'] is True


def test_analysis_projects_are_saved_with_contacts_removed(tmp_path):
    records = {('projects', 'Gp1'): {'projectGoldId': 'Gp1'},
               ('analysis_projects', 'Gp1'): [{'apGoldId': 'Ga1', 'contacts': [{'email': 'a@b'}]}]}
    fetch_gold.fetch_all(['Gp1'], FakeClient(records), str(tmp_path), max_seconds=None)
    assert fetch_gold.read_records(str(tmp_path), 'analysis_projects')['Gp1'] == [{'apGoldId': 'Ga1'}]


def test_backs_off_and_retries_when_told_to_slow_down(tmp_path):
    waits = []
    records = {('projects', 'Gp1'): {'projectGoldId': 'Gp1'}}
    client = FakeClient(records, slow_once=['Gp1'])
    fetch_gold.fetch_all(['Gp1'], client, str(tmp_path), max_seconds=None, sleep=waits.append)
    assert waits == [fetch_gold.BACKOFF_SECONDS[0]]
    assert 'Gp1' in fetch_gold.read_records(str(tmp_path), 'projects')


def test_stops_after_repeated_failures_instead_of_pushing_on(tmp_path):
    ids = ['Gp%d' % i for i in range(20)]
    client = FakeClient({}, broken=ids)
    report = fetch_gold.fetch_all(ids, client, str(tmp_path), max_seconds=None)
    assert report['stopped_early'] and len(client.calls) == fetch_gold.MAX_CONSECUTIVE_FAILURES


def test_project_ids_are_read_from_the_sample_alias_column_of_chunk_files(tmp_path):
    chunk = tmp_path / '0.csv'
    chunk.write_text('run\tsample_alias\nSRR1\tGp0000123\nSRR2\tsomething\nSRR3\tGp0000123\nSRR4\tGp0000456\n')
    listing = tmp_path / 'list'
    listing.write_text(str(chunk) + '\n')
    assert fetch_gold.project_ids_from_chunks(str(listing)) == ['Gp0000123', 'Gp0000456']
