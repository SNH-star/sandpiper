"""Concurrent requests for the same and for different queries share the cache safely."""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

os.environ['SANDPIPER_TESTING'] = '1'  # must be set before api.config is imported

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api.application import create_app  # noqa: E402

QUERIES = ['country: USA', 'country: Pacific', 'country:', 'country: Atlantis']
ENDPOINTS = [
    ('query_search_global_data', {}),
    ('query_search_run_data', {'sort_field': 'release_year', 'sort_direction': 'desc', 'page': 1, 'page_size': 50}),
]


def _fetch(app, q, endpoint, extra):
    response = app.test_client().get(f'/api/{endpoint}', query_string={'q': q, **extra})
    return response.status_code, response.get_json()


def test_concurrent_requests_match_the_single_threaded_answers():
    app = create_app()
    from api import api as api_module
    api_module.MATCH_CACHE.clear()
    api_module.MATCH_CACHE.enabled = False
    expected = {(q, e): _fetch(app, q, e, extra) for q in QUERIES for e, extra in ENDPOINTS}
    assert all(status == 200 for status, _ in expected.values())

    api_module.MATCH_CACHE.enabled = True
    jobs = [(q, e, extra) for _ in range(6) for q in QUERIES for e, extra in ENDPOINTS]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda job: (job, _fetch(app, *job)), jobs))
    for (q, endpoint, _extra), (status, body) in results:
        assert status == 200
        assert body == expected[(q, endpoint)][1]
    assert len(api_module.MATCH_CACHE) <= len(QUERIES)
