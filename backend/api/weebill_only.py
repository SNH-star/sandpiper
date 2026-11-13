"""Runs Weebill introduced: in the Weebill-integrated profile but with no SingleM marker-gene hits.

``sandpiper.weebill_only_load`` stores their run IDs in the small table ``weebill_only_runs``. It is
a table of its own, not a column of ``parsed_sample_attributes``, so a database built before the
stage was run (or without it) still works: the flag is then unknown (None) and a search on it
finds nothing, instead of every parsed-attribute query failing on a missing column.
"""
from typing import Optional, Set

from sqlalchemy import column, select, table, text

TABLE = 'weebill_only_runs'
_databases_with_table: Set[str] = set()


def runs_table():
    return table(TABLE, column('run_id'))


def run_ids():
    """A query for the run IDs of the Weebill-only runs."""
    return select(runs_table().c.run_id)


def is_available(connection) -> bool:
    """Whether the database has the table. Remembered once found; asked again while it is missing,
    so loading the stage while the API is running is noticed."""
    key = str(connection.engine.url)
    if key in _databases_with_table:
        return True
    found = connection.execute(text(
        'SELECT count(*) FROM information_schema.tables WHERE table_name = :name '
        'AND table_schema = current_schema() AND table_catalog = current_database()'), {'name': TABLE}).scalar() > 0
    if found:
        _databases_with_table.add(key)
    return found


def flag_for_run(connection, run_id: int) -> Optional[bool]:
    """True/False for a run, or None when the database has no Weebill-only table."""
    if not is_available(connection):
        return None
    runs = runs_table()
    query = select(runs.c.run_id).where(runs.c.run_id == run_id).limit(1)
    return connection.execute(query).first() is not None
