"""
match_cache.py
- Shares the run ids matching a search query between the endpoints that
  filter on it.

A results page asks for the summary, the runs table and the map of one
query. Each used to search the text columns again (about a second apiece on
the full database). The first request now keeps the
matching ids as a small array in this process; every later request registers
that array on its own DuckDB connection and filters on it, which costs
milliseconds.

The database is opened read-only, so a stored id set never goes stale. Memory
is bounded by entry and id-count limits (a few MB in total). When the cache
cannot serve a query (disabled, result too large, any error) the caller gets
None and runs the original subquery, so answers never depend on the cache.
"""
import hashlib
import logging
import threading
from collections import OrderedDict

import numpy as np
from flask import g
from sqlalchemy import column, select, table

MAX_ENTRIES = 32
MAX_TOTAL_IDS = 4_000_000   # ~16 MB of int32 ids
MAX_ENTRY_IDS = 1_000_000   # larger than the whole database (~913k runs)
MAX_UNCACHEABLE_KEYS = 256


class MatchCache:
    def __init__(self, max_entries=MAX_ENTRIES, max_total_ids=MAX_TOTAL_IDS, max_entry_ids=MAX_ENTRY_IDS):
        self.enabled = True
        self.max_entries = max_entries
        self.max_total_ids = max_total_ids
        self.max_entry_ids = max_entry_ids
        self._entries: OrderedDict[str, np.ndarray] = OrderedDict()
        # Queries that were too large to keep or failed to build, so later
        # requests skip straight to the uncached path instead of trying again.
        self._uncacheable: OrderedDict[str, None] = OrderedDict()
        self._lock = threading.Lock()         # guards the two dicts; never held while building
        self._build_lock = threading.Lock()   # one id set is built at a time
        self._registered_attr = f'_match_cache_registered_{id(self)}'

    def __len__(self):
        return len(self._entries)

    def __contains__(self, key):
        return key in self._entries

    def ids_select(self, key, build_select, session):
        """SELECT id over the stored ids for `key` (`build_select()` returns the
        SELECT that finds them, run only on a miss), or None when the cache
        cannot serve this query. The ids are registered on the request's
        connection; call release() when the request ends."""
        if not self.enabled:
            return None
        try:
            ids = self._ids_for(key, build_select, session)
            if ids is None:
                return None
            name = 'm_' + hashlib.sha1(key.encode()).hexdigest()[:20]
            connection = session.connection().connection.driver_connection
            connection.register(name, {'id': ids})
        except Exception:
            logging.warning('Match cache could not serve a search; running it uncached', exc_info=True)
            session.rollback()
            return None
        registered = getattr(g, self._registered_attr, None)
        if registered is None:
            registered = []
            setattr(g, self._registered_attr, registered)
        registered.append((connection, name))
        return select(table(name, column('id')).c.id)

    def release(self):
        """Unregister what the current request registered on its connection."""
        registered = getattr(g, self._registered_attr, None) or []
        setattr(g, self._registered_attr, [])
        for connection, name in registered:
            try:
                connection.unregister(name)
            except Exception:
                logging.warning('Could not unregister %s', name, exc_info=True)

    def clear(self):
        with self._lock:
            self._entries.clear()
            self._uncacheable.clear()

    def _ids_for(self, key, build_select, session):
        with self._lock:
            ids = self._lookup(key)
        if ids is not None or key in self._uncacheable:
            return ids
        # Misses are built one at a time (the machine only has two threads for
        # it anyway, and two requests for one query should not both build it),
        # but hits above never wait on a build.
        with self._build_lock:
            with self._lock:
                ids = self._lookup(key)
                if ids is not None or key in self._uncacheable:
                    return ids
            try:
                # One row past the limit is enough to know it will not fit.
                found = session.execute(build_select().limit(self.max_entry_ids + 1)).scalars().all()
            except Exception:
                logging.warning('Could not find the runs matching a search for the cache; will not retry it',
                                exc_info=True)
                session.rollback()
                found = None
            with self._lock:
                if found is None or len(found) > self.max_entry_ids:
                    self._mark_uncacheable(key)
                    return None
                ids = np.array(found, dtype=np.int32)
                self._entries[key] = ids
                self._evict()
                return ids

    def _lookup(self, key):
        """The stored ids for `key` (marking them recently used), or None. Needs self._lock."""
        ids = self._entries.get(key)
        if ids is not None:
            self._entries.move_to_end(key)
        return ids

    def _mark_uncacheable(self, key):
        self._uncacheable[key] = None
        while len(self._uncacheable) > MAX_UNCACHEABLE_KEYS:
            self._uncacheable.popitem(last=False)

    def _evict(self):
        """Drop least-recently-used entries until the limits hold (the newest stays)."""
        while len(self._entries) > self.max_entries or (
                len(self._entries) > 1 and sum(len(v) for v in self._entries.values()) > self.max_total_ids):
            self._entries.popitem(last=False)
