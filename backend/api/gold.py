"""JGI GOLD (https://gold.jgi.doe.gov/) details for runs whose sample carries a GOLD project ID.

Runs submitted through JGI record their GOLD project ID (``Gp0119859``) as the BioSample
``sample_alias``. This module turns GOLD's project, biosample and study records into the Sample
information rows, publications and CSV columns the run page shows (``build_*``, ``csv_pairs``),
and compares a run's rows with the related runs' (``tag_differences``). The records themselves
come from the database's gold_* tables (see ``gold_db``).

It also holds the client for GOLD's web service, used only by ``bin/fetch_gold.py`` to download
the records. GOLD allows roughly one request per second and answers only by GOLD ID, hence the
throttle. Contact names and email addresses in GOLD's records are never kept.
"""
import re
import threading
import time
from typing import Callable, Dict, List, Optional

import requests

from .bioproject_similarity import compare_to_peers
from .metagenome_similarity import is_expected_to_differ

GOLD_WS = 'https://gold-ws.jgi.doe.gov'
GOLD_SITE_PROJECT = 'https://gold.jgi.doe.gov/project?id={}'
PROJECT_ID = re.compile(r'^Gp\d{5,}$')
MIN_REQUEST_INTERVAL = 1.2
ACCESS_TOKEN_SECONDS = 11 * 3600
TIMEOUT_SECONDS = 20
SOURCE = 'gold'


class GoldUnavailable(Exception):
    """GOLD could not be asked or did not answer (no token, rate limited, down).

    ``status`` is the HTTP status when GOLD answered with one (404 = no such record, 429 = slow down).
    """

    def __init__(self, message: str = '', status: Optional[int] = None):
        super().__init__(message)
        self.status = status


def find_project_id(values) -> Optional[str]:
    """The first value that looks like a GOLD project ID."""
    for value in values:
        if isinstance(value, str) and PROJECT_ID.match(value.strip()):
            return value.strip()
    return None


# --- turning GOLD records into page content ------------------------------------------------------

def _text(value) -> Optional[str]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    return text if text and text.lower() not in ('null', 'none') else None


def _joined(values) -> Optional[str]:
    return ', '.join(item for item in (_text(v) for v in (values or [])) if item) or None


def _envo(term) -> Optional[str]:
    if not isinstance(term, dict) or not _text(term.get('label')):
        return None
    return '{} ({})'.format(term['label'], term['id']) if _text(term.get('id')) else term['label']


def _ecosystem(biosample: dict) -> Optional[str]:
    keys = ('ecosystem', 'ecosystemCategory', 'ecosystemType', 'ecosystemSubtype', 'specificEcosystem')
    return ' > '.join(item for item in (_text(biosample.get(k)) for k in keys) if item) or None


def _coordinates(biosample: dict) -> Optional[str]:
    lat, lon = _text(biosample.get('latitude')), _text(biosample.get('longitude'))
    return '{}, {}'.format(lat, lon) if lat and lon else None


def _metres(biosample: dict, key: str) -> Optional[str]:
    """A measurement in metres; GOLD stores a range as ``key`` and ``key`` + '2'."""
    low, high = _text(biosample.get(key)), _text(biosample.get(key + '2'))
    if low and high and high != low:
        return '{}-{} m'.format(low, high)
    value = low or high
    return value + ' m' if value else None


def _depth(biosample: dict) -> Optional[str]:
    return _metres(biosample, 'depthInMeters')


def _longhurst(biosample: dict) -> Optional[str]:
    province = biosample.get('longhurst')
    if not isinstance(province, dict) or not _text(province.get('code')):
        return None
    description = _text(province.get('description'))
    return '{} ({})'.format(province['code'], description) if description else province['code']


def _listed(value) -> Optional[str]:
    return _joined(value) if isinstance(value, list) else _text(value)


def _funding(project: dict) -> Optional[str]:
    return ' '.join(part for part in (_text(project.get('jgiFundingProgram')), _text(project.get('jgiFundingYear'))) if part) or None


# (label, description, function of the record). Order is the order shown on the page.
PROJECT_FIELDS = [
    ('GOLD project ID', "the project's identifier in the JGI Genomes OnLine Database (GOLD).", lambda r: _text(r.get('projectGoldId'))),
    ('GOLD project name', 'the name GOLD gives this sequencing project.', lambda r: _text(r.get('projectName'))),
    ('GOLD project status', "GOLD's status for this project, such as Permanent Draft.", lambda r: _text(r.get('projectStatus'))),
    ('GOLD sequencing status', "whether GOLD records the project's sequencing as complete.", lambda r: _text(r.get('sequencingStatus'))),
    ('GOLD sequencing strategy', 'the kind of sequencing GOLD records for this project, such as Metagenome.', lambda r: _text(r.get('sequencingStrategy'))),
    ('GOLD sequencing platform', 'the sequencing instrument(s) GOLD records for this project.', lambda r: _joined(r.get('seqMethod'))),
    ('GOLD sequencing centre', 'the centre(s) that sequenced the sample, according to GOLD.', lambda r: _joined(r.get('sequencingCenters'))),
    ('GOLD JGI funding program', 'the JGI programme and year that funded this sequencing, according to GOLD.', _funding),
]
BIOSAMPLE_FIELDS = [
    ('GOLD ecosystem path', "GOLD's curated habitat classification, from the broad ecosystem down to the specific one.", _ecosystem),
    ('GOLD habitat', 'the habitat GOLD records for the sample.', lambda r: _text(r.get('habitat'))),
    ('GOLD sample collection site', 'the kind of site the sample was collected from, according to GOLD.', lambda r: _text(r.get('sampleCollectionSite'))),
    ('GOLD biosample ID', "the sample's identifier in GOLD.", lambda r: _text(r.get('biosampleGoldId'))),
    ('GOLD location', 'where the sample was collected, according to GOLD.', lambda r: _text(r.get('geographicLocation'))),
    ('GOLD coordinates', 'the latitude and longitude GOLD records for the sample.', _coordinates),
    ('GOLD collection date', 'the date the sample was collected, according to GOLD.', lambda r: _text(r.get('dateCollected'))),
    ('GOLD depth', 'the depth the sample was collected from, in metres, according to GOLD.', _depth),
    ('GOLD elevation', 'the elevation of the sampling site above sea level, according to GOLD.', lambda r: _metres(r, 'elevationInMeters')),
    ('GOLD altitude', 'the altitude of the sampling site, according to GOLD.', lambda r: _metres(r, 'altitudeInMeters')),
    ('GOLD subsurface depth', 'the depth below the surface from which the sample was taken, according to GOLD.', lambda r: _metres(r, 'subsurfaceDepthInMeters')),
    ('GOLD Longhurst province', "the Longhurst biogeochemical province of an ocean sample, according to GOLD.", _longhurst),
    ('GOLD country', 'the ISO country code GOLD records for the sampling location.', lambda r: _text(r.get('isoCountry'))),
    ('GOLD host', 'the host organism GOLD records for the sample.', lambda r: _text(r.get('hostName'))),
    ('GOLD host NCBI taxon ID', "the NCBI taxonomy ID of the sample's host, according to GOLD.", lambda r: _text(r.get('hostNcbiTaxid'))),
    ('GOLD host sex', "the host's sex, according to GOLD.", lambda r: _text(r.get('hostGender'))),
    ('GOLD host diseases', 'diseases of the host recorded by GOLD.', lambda r: _listed(r.get('hostDiseases'))),
    ('GOLD body site', 'the host body site the sample was taken from, according to GOLD.', lambda r: _text(r.get('sampleBodySite'))),
    ('GOLD body subsite', 'the more specific host body site the sample was taken from, according to GOLD.', lambda r: _text(r.get('sampleBodySubsite'))),
    ('GOLD oxygen', 'the oxygen concentration GOLD records for the sample.', lambda r: _text(r.get('oxygenConcentration'))),
    ('GOLD pressure', 'the pressure GOLD records for the sample.', lambda r: _text(r.get('pressure'))),
    ('GOLD visit number', 'the visit number GOLD records for repeat sampling.', lambda r: _text(r.get('visitNum'))),
    ('GOLD pH', 'the pH GOLD records for the sample.', lambda r: _text(r.get('ph'))),
    ('GOLD salinity', 'the salinity GOLD records for the sample.', lambda r: _text(r.get('salinityConcentration'))),
    ('GOLD collection temperature', 'the temperature at collection, according to GOLD.', lambda r: _text(r.get('sampleCollectionTemperature'))),
    ('GOLD nitrate', 'the nitrate concentration GOLD records for the sample.', lambda r: _text(r.get('nitrateConcentration'))),
    ('GOLD description', "GOLD's free-text description of the sample.", lambda r: _text(r.get('description'))),
    ('GOLD ENVO broad scale', 'the ENVO term for the broad-scale environmental context of the sample.', lambda r: _envo(r.get('envoBroadScale'))),
    ('GOLD ENVO local scale', 'the ENVO term for the local environmental context of the sample.', lambda r: _envo(r.get('envoLocalScale'))),
    ('GOLD ENVO medium', 'the ENVO term for the environmental medium the sample was taken from.', lambda r: _envo(r.get('envoMedium'))),
    ('GOLD MIxS package', 'the MIxS environmental package GOLD records for the sample.', lambda r: _text(r.get('mixsPackage'))),
    ('GOLD NCBI taxon', 'the NCBI taxon GOLD records for the sample.', lambda r: _text(r.get('ncbiTaxName'))),
]
STUDY_FIELDS = [
    ('GOLD study', 'the name of the GOLD study this project belongs to.', lambda r: _text(r.get('studyName'))),
    ('GOLD study description', "GOLD's description of the study this project belongs to.", lambda r: _text(r.get('description'))),
]


def build_rows(project: dict, biosample: Optional[dict], study: Optional[dict]) -> List[dict]:
    """Sample information rows (tagged ``source: 'gold'``) from the three GOLD records."""
    rows = []
    for record, fields in ((project, PROJECT_FIELDS), (biosample, BIOSAMPLE_FIELDS), (study, STUDY_FIELDS)):
        for label, description, value_of in fields if record else []:
            value = value_of(record)
            if value is not None:
                rows.append({'k': label, 'v': value, 'description': description, 'is_custom': False,
                             'raw_k': label, 'source': SOURCE})
    return rows


def build_publications(project: dict) -> List[dict]:
    """The project's publications, one per PubMed ID or DOI."""
    seen, publications = set(), []
    for pub in (project.get('genomePublications') or []) + (project.get('otherPublications') or []):
        pubmed, doi = _text(pub.get('pubmedId')), _text(pub.get('doi'))
        key = pubmed or (doi or '').lower() or _text(pub.get('title'))
        if not key or key in seen:
            continue
        seen.add(key)
        publications.append({'pubmed_id': pubmed, 'doi': doi, 'title': _text(pub.get('title')),
                             'journal': _text(pub.get('journalName')), 'date': _text(pub.get('publicationDate'))})
    return publications


def build_summary(project: dict, biosample: Optional[dict], study: Optional[dict]) -> dict:
    project_id = project['projectGoldId']
    return {'project_id': project_id, 'url': GOLD_SITE_PROJECT.format(project_id),
            'rows': build_rows(project, biosample, study), 'publications': build_publications(project)}


# --- comparing with the rest of the BioProject ---------------------------------------------------

def _values_of(rows: List[dict]) -> Dict[str, str]:
    return {row['k']: row['v'] for row in rows}


def _is_expected(label: str) -> bool:
    return is_expected_to_differ(label[len('GOLD '):] if label.startswith('GOLD ') else label)


def tag_differences(rows: List[dict], peer_summaries: List[dict]) -> List[dict]:
    """Copies of ``rows`` tagged ``difference`` against other samples of the same BioProject.

    Same meaning as the NCBI rows: 'only_here' (no other sample has the field), 'differs' (a
    value the others do not share) or 'expected' (identifier-like fields that differ by design).
    """
    peers = [_values_of(summary['rows']) for summary in peer_summaries if summary]
    if not peers:
        return rows
    values = _values_of(rows)
    expected = {k: v for k, v in values.items() if _is_expected(k)}
    informative = {k: v for k, v in values.items() if k not in expected}
    plain = compare_to_peers(informative, peers) or {}
    by_id = compare_to_peers(expected, peers) or {}
    flagged = {}
    for label in plain.get('only_here_fields', []):
        flagged[label] = 'only_here'
    for label in plain.get('unique_fields', []):
        flagged[label] = 'differs'
    for label in by_id.get('only_here_fields', []) + by_id.get('unique_fields', []):
        flagged[label] = 'expected'
    return [{**row, 'difference': flagged[row['k']]} if row['k'] in flagged else dict(row) for row in rows]


# --- talking to GOLD -----------------------------------------------------------------------------

class Throttle:
    """Spaces calls to :meth:`wait` at least ``interval`` seconds apart, across threads."""

    def __init__(self, interval: float, now: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        self.interval, self._now, self._sleep = interval, now, sleep
        self._next = float('-inf')
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = self._now()
            start = max(now, self._next)
            self._next = start + self.interval
        if start > now:
            self._sleep(start - now)


class GoldClient:
    """Asks the GOLD web service for records, exchanging the offline token as needed."""

    def __init__(self, offline_token: str, throttle: Optional[Throttle] = None):
        self.offline_token = (offline_token or '').strip()
        self.throttle = throttle or Throttle(MIN_REQUEST_INTERVAL)
        self._access, self._access_until = None, 0.0
        self._lock = threading.Lock()

    def _access_token(self, refresh: bool = False) -> str:
        with self._lock:
            if refresh or self._access is None or time.monotonic() >= self._access_until:
                self.throttle.wait()
                try:
                    response = requests.get(GOLD_WS + '/exchange', params={'offlineToken': self.offline_token},
                                            timeout=TIMEOUT_SECONDS)
                    response.raise_for_status()
                except requests.RequestException as error:
                    raise GoldUnavailable('token exchange failed: {}'.format(error))
                self._access = response.text.strip().strip('"')
                self._access_until = time.monotonic() + ACCESS_TOKEN_SECONDS
            return self._access

    def fetch(self, path: str, **params) -> list:
        if not self.offline_token:
            raise GoldUnavailable('no GOLD token is configured')
        for attempt in (0, 1):
            token = self._access_token(refresh=attempt == 1)
            self.throttle.wait()
            try:
                response = requests.get('{}/api/v1/{}'.format(GOLD_WS, path), params=params, timeout=TIMEOUT_SECONDS,
                                        headers={'Accept': 'application/json', 'Authorization': 'Bearer ' + token})
            except requests.RequestException as error:
                raise GoldUnavailable(str(error))
            if response.status_code == 401 and attempt == 0:
                continue
            if response.status_code != 200:
                raise GoldUnavailable('GOLD answered HTTP {}'.format(response.status_code), status=response.status_code)
            try:
                return response.json()
            except ValueError as error:
                raise GoldUnavailable(str(error))
        raise GoldUnavailable('GOLD rejected the access token')


# --- saved copies --------------------------------------------------------------------------------

def csv_pairs(summary: dict) -> List[tuple]:
    """(column, value) pairs for the run's Additional Run Metadata CSV: every row, the project link, and publications."""
    pairs = [(row['k'], row['v']) for row in summary['rows']]
    pairs.append(('GOLD project URL', summary['url']))
    pubmed = '; '.join(p['pubmed_id'] for p in summary['publications'] if p['pubmed_id'])
    dois = '; '.join(p['doi'] for p in summary['publications'] if p['doi'])
    if pubmed:
        pairs.append(('GOLD publication PubMed IDs', pubmed))
    if dois:
        pairs.append(('GOLD publication DOIs', dois))
    return pairs
