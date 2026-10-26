"""Answers of the query-search endpoints, checked against independent SQL.

These pin the behaviour that the speed-up work (one scan in /universal_search,
one combined count in /query_search_global_data) must not change. They run on
the small test database, so they check correctness, not speed.
"""
import os
import sys

os.environ['SANDPIPER_TESTING'] = '1'  # must be set before api.config is imported

import pytest  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api.application import create_app  # noqa: E402

@pytest.fixture(scope='module')
def app():
    return create_app()


@pytest.fixture(scope='module')
def client(app):
    return app.test_client()


@pytest.fixture(scope='module')
def raw(app):
    """Hand-written SQL through the app's own connection (DuckDB refuses a second,
    differently configured connection to the same file)."""
    from api.models import db
    with app.app_context():
        conn = db.engine.raw_connection()
        cursor = conn.cursor()

        class Raw:
            def execute(self, sql, params=()):
                cursor.execute(sql, list(params))
                return cursor

        yield Raw()
        conn.close()


def _accs(raw, where):
    return {r[0] for r in raw.execute(f'SELECT acc FROM ncbi_metadata WHERE {where}').fetchall()}


def _search(client, q, **extra):
    body = client.get('/api/universal_search', query_string={'q': q, **extra}).get_json()
    return body


QUERIES = {
    'country: USA': "geo_loc_name ILIKE '%USA%'",
    'country: Pacific': "geo_loc_name ILIKE '%Pacific%'",
    'country: Atlantis': "geo_loc_name ILIKE '%Atlantis%'",
}


@pytest.mark.parametrize('q,where', QUERIES.items())
def test_universal_search_count_matches_sql(client, raw, q, where):
    expected = _accs(raw, where)
    body = _search(client, q)
    assert body['count'] == len(expected)
    if expected:
        assert body['random_acc'] in expected
    else:
        assert body['random_acc'] is None


def test_universal_search_random_acc_never_the_excluded_run(client, raw):
    everything = _accs(raw, 'true')
    q = 'country:'  # every run with a location
    matching = _accs(raw, 'geo_loc_name IS NOT NULL')
    excluded = sorted(matching)[0]
    seen = {_search(client, q, exclude=excluded)['random_acc'] for _ in range(25)}
    assert excluded not in seen
    assert seen <= matching
    assert len(seen) > 1, 'random pick should vary across calls'
    assert matching <= everything


def test_universal_search_only_match_is_excluded_gives_no_random_run(client, raw):
    only = sorted(_accs(raw, "geo_loc_name ILIKE '%Pacific%'"))
    assert len(only) == 1
    body = _search(client, 'country: Pacific', exclude=only[0])
    assert body['count'] == 1          # count stays the full match total
    assert body['random_acc'] is None


def test_universal_search_taxonomy_join_does_not_double_count_runs(client, raw):
    name = raw.execute(
        'SELECT t.name FROM taxonomies t JOIN condensed_profiles_ctas1 c ON c.taxonomy_id = t.id '
        'GROUP BY t.name ORDER BY count(*) DESC LIMIT 1').fetchone()[0]
    expected = raw.execute(
        'SELECT count(DISTINCT c.run_id) FROM condensed_profiles_ctas1 c WHERE c.taxonomy_id IN '
        "(SELECT id FROM taxonomies WHERE lower(name) LIKE ? ESCAPE '\\')",
        [f'%{name.lower()}%']).fetchone()[0]
    assert expected > 0
    body = _search(client, f'taxonomy: {name}')
    assert body['count'] == expected


GLOBAL_COUNTS = '''
SELECT count(*),
       count(*) FILTER (WHERE p.host_or_not_mature = 'host'),
       count(*) FILTER (WHERE p.host_or_not_mature = 'ecological'),
       count(*) FILTER (WHERE p.low_complexity IS true),
       count(*) FILTER (WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL)
FROM ncbi_metadata n LEFT JOIN parsed_sample_attributes p ON p.run_id = n.id
WHERE {where}
'''


@pytest.mark.parametrize('q,where', [
    ('country:', 'n.geo_loc_name IS NOT NULL'),
    ('country: USA', "n.geo_loc_name ILIKE '%USA%'"),
    ('country: Atlantis', "n.geo_loc_name ILIKE '%Atlantis%'"),
])
def test_global_data_counts_match_sql(client, raw, q, where):
    total, host, eco, low, with_coords = raw.execute(GLOBAL_COUNTS.format(where=where)).fetchone()
    body = client.get('/api/query_search_global_data', query_string={'q': q}).get_json()
    assert body['total_num_results'] == total
    assert body['num_host_runs'] == host
    assert body['num_ecological_runs'] == eco
    assert body['num_low_complexity_runs'] == low
    assert body['total_lat_lon_runs'] == with_coords


def test_global_data_for_unmatched_taxonomy_is_all_zero(client):
    body = client.get('/api/query_search_global_data',
                      query_string={'q': 'taxonomy: zzzz_no_such_taxon'}).get_json()
    assert body['total_num_results'] == 0
    assert body['lat_lons'] == [] and body['total_lat_lon_runs'] == 0


def test_universal_search_random_pick_reaches_every_match(client, raw):
    matching = _accs(raw, 'geo_loc_name IS NOT NULL')
    seen = {_search(client, 'country:')['random_acc'] for _ in range(150)}
    assert seen == matching
