"""The matching-run id cache: a query's matching ids are found once and then
shared by every endpoint (and request) that filters on that query."""
import os
import sys

os.environ['SANDPIPER_TESTING'] = '1'  # must be set before api.config is imported

import pytest  # noqa: E402
from sqlalchemy import event, select  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api.application import create_app  # noqa: E402
from api.match_cache import MatchCache  # noqa: E402
from api.models import NcbiMetadata, db  # noqa: E402

# The small test database predates the pH/temperature columns, so the Niche
# options and map endpoints cannot run on it; the full-database benchmark covers them.
ENDPOINTS = {
    'query_search_global_data': {},
    'query_search_run_data': {'sort_field': 'release_year', 'sort_direction': 'desc', 'page': 1, 'page_size': 50},
}
Q = 'country:'  # every run with a location


@pytest.fixture(scope='module')
def app():
    return create_app()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def raw_sql(app):
    """Hand-written SQL through the app's own connection."""
    def run(sql):
        with app.app_context():
            return db.session.execute(db.text(sql)).fetchall()
    return run


@pytest.fixture()
def statements(app):
    """SQL text of every statement the engine runs while the test executes."""
    seen = []

    def record(conn, cursor, statement, params, context, executemany):
        seen.append(statement)

    with app.app_context():
        engine = db.engine
    event.listen(engine, 'before_cursor_execute', record)
    yield seen
    event.remove(engine, 'before_cursor_execute', record)


@pytest.fixture()
def api_cache(app):
    """The cache the endpoints use, emptied and re-enabled for each test."""
    from api import api as api_module
    with app.app_context():
        api_module.MATCH_CACHE.clear()
    api_module.MATCH_CACHE.enabled = True
    yield api_module.MATCH_CACHE
    api_module.MATCH_CACHE.enabled = True


def _get(client, endpoint, q=Q):
    response = client.get(f'/api/{endpoint}', query_string={'q': q, **ENDPOINTS[endpoint]})
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.get_json()


def _scans(statements):
    return [s for s in statements if 'ILIKE' in s.upper() or 'LIKE' in s.upper()]


def test_second_request_for_the_same_query_does_not_rescan(client, statements, api_cache):
    first = _get(client, 'query_search_global_data')
    scans_after_first = len(_scans(statements))
    second = _get(client, 'query_search_global_data')
    assert scans_after_first >= 1                          # the first request searched the text once
    assert len(_scans(statements)) == scans_after_first   # nothing new scanned
    assert first == second


def test_other_endpoints_reuse_the_ids_found_by_the_first(client, statements, api_cache):
    _get(client, 'query_search_global_data')
    searched = len(_scans(statements))
    assert searched >= 1
    _get(client, 'query_search_run_data')
    assert len(_scans(statements)) == searched, 'the runs table re-ran the text search'


@pytest.mark.parametrize('endpoint', list(ENDPOINTS))
def test_answers_are_the_same_with_and_without_the_cache(client, api_cache, endpoint):
    api_cache.enabled = False
    expected = _get(client, endpoint)
    api_cache.enabled = True
    assert _get(client, endpoint) == expected          # built from the query
    assert _get(client, endpoint) == expected          # served from the cache


def test_cache_is_keyed_by_query(client, api_cache):
    a = _get(client, 'query_search_global_data', 'country: USA')
    b = _get(client, 'query_search_global_data', 'country: Pacific')
    assert a['total_num_results'] != b['total_num_results']
    assert _get(client, 'query_search_global_data', 'country: USA') == a


def _build(q):
    return lambda: select(NcbiMetadata.id).where(NcbiMetadata.geo_loc_name.ilike(f'%{q}%'))


def test_least_recently_used_entry_is_evicted_at_the_entry_limit(app):
    cache = MatchCache(max_entries=2)
    with app.app_context():
        for q in ('a', 'e', 'o'):
            assert cache.ids_select(q, _build(q), db.session) is not None
            cache.release()
    assert len(cache) == 2 and 'a' not in cache and 'o' in cache


def test_a_request_keeps_reading_an_entry_evicted_meanwhile(app):
    cache = MatchCache(max_entries=1)
    with app.app_context():
        held = cache.ids_select('a', _build('a'), db.session)
        expected = db.session.execute(select(held.subquery().c.id)).scalars().all()
        assert cache.ids_select('e', _build('e'), db.session) is not None   # evicts 'a'
        assert 'a' not in cache
        assert db.session.execute(select(held.subquery().c.id)).scalars().all() == expected
        cache.release()


def test_result_too_large_to_cache_falls_back(app):
    cache = MatchCache(max_entry_ids=1)
    with app.app_context():
        assert cache.ids_select('a', _build('a'), db.session) is None
    assert len(cache) == 0


def test_disabled_cache_serves_nothing(app):
    cache = MatchCache()
    cache.enabled = False
    with app.app_context():
        assert cache.ids_select('a', _build('a'), db.session) is None


def test_release_unregisters_so_the_connection_is_clean(app):
    cache = MatchCache()
    with app.app_context():
        cache.ids_select('a', _build('a'), db.session)
        cache.release()
        names = db.session.execute(db.text("SELECT view_name FROM duckdb_views() WHERE view_name LIKE 'm\\_%' ESCAPE '\\'")).fetchall()
        assert names == []


def test_building_never_pulls_more_than_one_row_past_the_limit(app, statements):
    cache = MatchCache(max_entry_ids=3)
    with app.app_context():
        assert cache.ids_select('everything', _build(''), db.session) is None   # 12 matches > 3
    assert any('LIMIT' in s.upper() for s in statements)
    assert len(cache) == 0


def test_a_result_found_too_large_is_not_searched_for_again(app):
    cache = MatchCache(max_entry_ids=3)
    runs = []

    def build():
        runs.append(1)
        return _build('')()

    with app.app_context():
        assert cache.ids_select('everything', build, db.session) is None
        assert cache.ids_select('everything', build, db.session) is None
    assert len(runs) == 1


def test_taxonomy_query_counts_each_run_once_and_is_cached(client, raw_sql, statements, api_cache):
    name = raw_sql(
        'SELECT t.name FROM taxonomies t JOIN condensed_profiles_ctas1 c ON c.taxonomy_id = t.id '
        'GROUP BY t.name ORDER BY count(*) DESC LIMIT 1')[0][0]
    q = f'taxonomy: {name}'
    first = _get(client, 'query_search_global_data', q)
    # The big profiles table is joined once to find the runs, then not again.
    joins = lambda: sum('condensed_profiles_ctas1' in s for s in statements)  # noqa: E731
    joined = joins()
    assert joined >= 1
    second = _get(client, 'query_search_global_data', q)
    assert first == second and first['total_num_results'] > 0
    assert joins() == joined
    assert len(api_cache) == 1
    ids_cached = next(iter(api_cache._entries.values()))
    assert len(ids_cached) == len(set(ids_cached.tolist())) == first['total_num_results']


def test_a_cache_hit_is_not_held_up_by_another_query_being_built(app):
    import threading
    cache = MatchCache()
    with app.app_context():
        assert cache.ids_select('warm', _build('a'), db.session) is not None
        cache.release()

    building, finish = threading.Event(), threading.Event()

    def slow_build():
        building.set()
        assert finish.wait(10)
        return _build('e')()

    def cold_request():
        with app.app_context():
            cache.ids_select('cold', slow_build, db.session)
            cache.release()

    thread = threading.Thread(target=cold_request)
    thread.start()
    assert building.wait(10)
    try:
        hit = {}

        def warm_request():
            with app.app_context():
                hit['select'] = cache.ids_select('warm', _build('a'), db.session)
                cache.release()

        warm = threading.Thread(target=warm_request)
        warm.start()
        warm.join(timeout=5)
        assert not warm.is_alive(), 'a cache hit waited for an unrelated build'
        assert hit['select'] is not None
    finally:
        finish.set()
        thread.join(10)


def test_a_build_that_fails_is_not_retried_for_every_request(app):
    cache = MatchCache()
    runs = []

    def failing():
        runs.append(1)
        raise RuntimeError('boom')

    with app.app_context():
        assert cache.ids_select('bad', failing, db.session) is None
        assert cache.ids_select('bad', failing, db.session) is None
        # The session is still usable afterwards.
        assert db.session.execute(select(NcbiMetadata.id).limit(1)).first() is not None
    assert len(runs) == 1
