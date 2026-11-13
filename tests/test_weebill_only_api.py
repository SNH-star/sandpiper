"""api.weebill_only: reading the weebill_only_runs table, and coping with a database that has none."""
import os
import sys

import duckdb
import pytest
from sqlalchemy import create_engine, select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api import weebill_only  # noqa: E402


def _engine(tmp_path, with_table):
    path = str(tmp_path / ('with.duckdb' if with_table else 'without.duckdb'))
    connection = duckdb.connect(path)
    connection.execute('CREATE TABLE ncbi_metadata (id INTEGER PRIMARY KEY, acc VARCHAR)')
    if with_table:
        connection.execute('CREATE TABLE weebill_only_runs (run_id INTEGER PRIMARY KEY)')
        connection.execute('INSERT INTO weebill_only_runs VALUES (2), (4)')
    connection.close()
    return create_engine('duckdb:///' + path)


def test_a_run_is_flagged_when_it_is_in_the_table_and_not_flagged_when_it_is_not(tmp_path):
    engine = _engine(tmp_path, with_table=True)
    with engine.connect() as conn:
        assert weebill_only.flag_for_run(conn, 2) is True
        assert weebill_only.flag_for_run(conn, 1) is False
        assert sorted(conn.execute(weebill_only.run_ids()).scalars().all()) == [2, 4]
    engine.dispose()


def test_a_database_without_the_table_gives_no_answer_instead_of_failing(tmp_path):
    engine = _engine(tmp_path, with_table=False)
    with engine.connect() as conn:
        assert weebill_only.is_available(conn) is False
        assert weebill_only.flag_for_run(conn, 2) is None
    engine.dispose()


def test_a_table_loaded_while_the_api_is_running_is_noticed(tmp_path):
    path = str(tmp_path / 'late.duckdb')
    connection = duckdb.connect(path)
    connection.execute('CREATE TABLE ncbi_metadata (id INTEGER PRIMARY KEY, acc VARCHAR)')
    connection.close()
    engine = create_engine('duckdb:///' + path)
    with engine.connect() as conn:
        assert weebill_only.is_available(conn) is False
    engine.dispose()
    connection = duckdb.connect(path)
    connection.execute('CREATE TABLE weebill_only_runs (run_id INTEGER PRIMARY KEY)')
    connection.close()
    engine = create_engine('duckdb:///' + path)
    with engine.connect() as conn:
        assert weebill_only.is_available(conn) is True
    engine.dispose()


def test_the_run_ids_work_as_the_search_conditions_yes_and_no(tmp_path):
    from sqlalchemy import column, table
    engine = _engine(tmp_path, with_table=True)
    connection = duckdb.connect(str(tmp_path / 'with.duckdb'))
    connection.execute("INSERT INTO ncbi_metadata VALUES (1,'SRR1'),(2,'SRR2'),(3,'SRR3'),(4,'SRR4')")
    connection.close()
    runs = table('ncbi_metadata', column('id'))
    flagged = weebill_only.run_ids().scalar_subquery()
    with engine.connect() as conn:
        yes = conn.execute(select(runs.c.id).where(runs.c.id.in_(flagged)).order_by(runs.c.id)).scalars().all()
        no = conn.execute(select(runs.c.id).where(runs.c.id.notin_(flagged)).order_by(runs.c.id)).scalars().all()
    assert yes == [2, 4] and no == [1, 3]
    engine.dispose()
