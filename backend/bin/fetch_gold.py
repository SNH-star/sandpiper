#!/usr/bin/env python3
"""Download everything JGI GOLD holds about the projects our runs link to.

Runs sequenced by JGI carry a GOLD project ID (``Gp0...``) as the BioSample ``sample_alias``.
For every such project this saves GOLD's full, unfiltered JSON for the project, its biosample,
its study and its analysis projects, one JSON-lines file per record type in ``--out-dir``.
Contact names and emails are dropped before anything is written.

GOLD answers only by its own IDs and asks for about one request a second, so this is slow and
deliberately gentle: requests are spaced ``--interval`` seconds apart (default 1.5), a 429 or
5xx makes it back off and wait, and it stops by itself after repeated failures instead of
pushing on. It is resumable: rerun the same command and it carries on where it stopped;
records that failed are retried, records GOLD does not know are remembered.

    fetch_gold.py --out-dir /path/to/gold_download [--limit 50] [--max-hours 40]

Needs the offline token as the environment variable GOLD_OFFLINE_TOKEN.
"""
import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from typing import Callable, Dict, Iterable, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from api.gold import GoldClient, GoldUnavailable, Throttle  # noqa: E402

log = logging.getLogger('fetch_gold')

DEFAULT_INTERVAL_SECONDS = 1.5
BACKOFF_SECONDS = (60, 120, 300, 900)
SLOW_DOWN_STATUSES = (429, 502, 503, 504)
MAX_CONSECUTIVE_FAILURES = 5
LOG_EVERY = 500
DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db', 'sandpiper_43.duckdb')

# record type -> (GOLD endpoint, filter parameter)
ENDPOINTS = {
    'projects': ('projects', 'projectGoldId'),
    'biosamples': ('biosamples', 'biosampleGoldId'),
    'studies': ('studies', 'studyGoldId'),
    'analysis_projects': ('analysis_projects', 'projectGoldId'),
}


class Stop(Exception):
    """Raised to end the run early (time budget spent or GOLD keeps failing)."""


def strip_contacts(value):
    """A copy of a GOLD record without any ``contacts`` key, at any depth."""
    if isinstance(value, dict):
        return {k: strip_contacts(v) for k, v in value.items() if k != 'contacts'}
    if isinstance(value, list):
        return [strip_contacts(item) for item in value]
    return value


def _path(out_dir: str, kind: str) -> str:
    return os.path.join(out_dir, kind + '.jsonl')


def read_records(out_dir: str, kind: str) -> Dict[str, Optional[object]]:
    """Saved records by ID (None = GOLD does not know the ID). Later lines win."""
    records: Dict[str, Optional[object]] = {}
    path = _path(out_dir, kind)
    if not os.path.exists(path):
        return records
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:  # a half-written last line from a killed run
                continue
            records[entry['id']] = entry['record']
    return records


class Fetcher:
    """Asks GOLD politely and appends answers to the output files."""

    def __init__(self, client, out_dir: str, max_seconds: Optional[float],
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic):
        self.client, self.out_dir, self.max_seconds = client, out_dir, max_seconds
        self._sleep, self._clock = sleep, clock
        self._started = clock()
        self.failures_in_a_row = 0
        self.counts = {'fetched': 0, 'failed': 0}

    def _check_budget(self) -> None:
        if self.max_seconds is not None and self._clock() - self._started >= self.max_seconds:
            raise Stop('time budget spent')
        if self.failures_in_a_row >= MAX_CONSECUTIVE_FAILURES:
            raise Stop('{} failures in a row, GOLD may be unhappy: stopping'.format(self.failures_in_a_row))

    def _ask(self, kind: str, gold_id: str) -> list:
        """The list GOLD returns; [] if it has no such record. Backs off when told to slow down."""
        endpoint, parameter = ENDPOINTS[kind]
        for wait in BACKOFF_SECONDS + (None,):
            try:
                return self.client.fetch(endpoint, **{parameter: gold_id})
            except GoldUnavailable as error:
                if error.status == 404:
                    return []
                if error.status not in SLOW_DOWN_STATUSES or wait is None:
                    raise
                log.warning('GOLD said %s for %s %s; waiting %ss', error.status, kind, gold_id, wait)
                self._sleep(wait)
        raise GoldUnavailable('unreachable')

    def get(self, kind: str, gold_id: str, saved: Dict[str, Optional[object]]) -> Optional[object]:
        """The record, saving it. Returns None (and saves nothing) if the request failed."""
        if gold_id in saved:
            return saved[gold_id]
        self._check_budget()
        try:
            answer = self._ask(kind, gold_id)
        except GoldUnavailable as error:
            self.failures_in_a_row += 1
            self.counts['failed'] += 1
            log.warning('%s %s failed: %s', kind, gold_id, error)
            return None
        self.failures_in_a_row = 0
        record = strip_contacts(answer if kind == 'analysis_projects' else (answer[0] if answer else None))
        if kind == 'analysis_projects' and not answer:
            record = []
        saved[gold_id] = record
        with open(_path(self.out_dir, kind), 'a') as handle:
            handle.write(json.dumps({'id': gold_id, 'record': record}) + '\n')
        self.counts['fetched'] += 1
        if self.counts['fetched'] % LOG_EVERY == 0:
            log.info('%d fetched, %d failed so far', self.counts['fetched'], self.counts['failed'])
        return record


def fetch_all(project_ids: Iterable[str], client, out_dir: str, max_seconds: Optional[float],
              sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic) -> dict:
    """Fetch projects, then their biosamples and studies, then analysis projects.

    Core records come first so an interrupted run still has the most useful data.
    """
    os.makedirs(out_dir, exist_ok=True)
    ids: List[str] = list(project_ids)
    fetcher = Fetcher(client, out_dir, max_seconds, sleep, clock)
    saved = {kind: read_records(out_dir, kind) for kind in ENDPOINTS}
    stopped = None
    try:
        projects = {pid: fetcher.get('projects', pid, saved['projects']) for pid in ids}
        for kind, key in (('biosamples', 'biosampleGoldId'), ('studies', 'studyGoldId')):
            wanted = sorted({p[key] for p in projects.values() if p and p.get(key)})
            for gold_id in wanted:
                fetcher.get(kind, gold_id, saved[kind])
        for pid in ids:
            if projects.get(pid):
                fetcher.get('analysis_projects', pid, saved['analysis_projects'])
    except Stop as stop:
        stopped = str(stop)
        log.warning('stopped early: %s', stopped)
    return {'fetched': fetcher.counts['fetched'], 'failed': fetcher.counts['failed'],
            'stopped_early': stopped is not None, 'reason': stopped}


PROJECT_ID = re.compile(r'^Gp\d{5,}$')


def project_ids_from_chunks(file_list_path: str) -> List[str]:
    """GOLD project IDs in the ``sample_alias`` column of the Kingfisher metadata chunk files.

    ``file_list_path`` lists one chunk file (tab separated, with a header) per line, as written by
    the pipeline's gather_kingfisher_metadata rule, so this works before any database exists.
    """
    csv.field_size_limit(sys.maxsize)
    found = set()
    with open(file_list_path) as listing:
        chunk_paths = [line.strip() for line in listing if line.strip()]
    for chunk_path in chunk_paths:
        with open(chunk_path, newline='') as handle:
            for row in csv.DictReader(handle, delimiter='\t'):
                alias = (row.get('sample_alias') or '').strip()
                if PROJECT_ID.match(alias):
                    found.add(alias)
    return sorted(found)


def project_ids_from_database(db_path: str) -> List[str]:
    import duckdb
    connection = duckdb.connect(db_path, read_only=True)
    try:
        rows = connection.execute("SELECT DISTINCT v FROM biosample_attributes WHERE k = 'sample_alias' "
                                  "AND regexp_matches(v, '^Gp[0-9]{5,}$') ORDER BY v").fetchall()
    finally:
        connection.close()
    return [row[0] for row in rows]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out-dir', required=True, help='directory for the .jsonl files (created if missing)')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--db', default=DEFAULT_DB, help='DuckDB to read the GOLD project IDs from (default)')
    source.add_argument('--kingfisher-file-list', help='file listing the Kingfisher metadata chunks to read the IDs from '
                                                      '(used by the pipeline, before the database exists)')
    parser.add_argument('--interval', type=float, default=DEFAULT_INTERVAL_SECONDS,
                        help='seconds between requests (default %(default)s; do not go below 1.0)')
    parser.add_argument('--limit', type=int, help='only the first N project IDs (for a trial run)')
    parser.add_argument('--max-hours', type=float, help='stop cleanly after this long')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    if args.interval < 1.0:
        parser.error('--interval below 1.0 s gets rate limited by GOLD')
    from api.config import BaseConfig
    token = (os.environ.get('GOLD_OFFLINE_TOKEN') or BaseConfig.GOLD_OFFLINE_TOKEN or '').strip()
    if not token:
        log.error('Set GOLD_OFFLINE_TOKEN in the environment.')
        return 2
    ids = project_ids_from_chunks(args.kingfisher_file_list) if args.kingfisher_file_list else project_ids_from_database(args.db)
    if args.limit:
        ids = ids[:args.limit]
    log.info('%d GOLD projects to fetch into %s', len(ids), args.out_dir)
    client = GoldClient(token, Throttle(args.interval))
    report = fetch_all(ids, client, args.out_dir, args.max_hours * 3600 if args.max_hours else None)
    log.info('done: %s', report)
    return 1 if report['stopped_early'] and report['reason'] != 'time budget spent' else 0


if __name__ == '__main__':
    sys.exit(main())
