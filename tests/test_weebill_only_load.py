"""sandpiper.weebill_only_load: the weebill_only_runs table of runs Weebill introduced."""
import os
import sys

import duckdb
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sandpiper import weebill_only_load  # noqa: E402


def _query(db_path, sql):
    connection = duckdb.connect(db_path, read_only=True)
    try:
        return connection.execute(sql).fetchall()
    finally:
        connection.close()


@pytest.fixture
def database(tmp_path):
    path = str(tmp_path / 'db.duckdb')
    connection = duckdb.connect(path)
    connection.execute('CREATE TABLE ncbi_metadata (id INTEGER PRIMARY KEY, acc VARCHAR)')
    connection.execute("INSERT INTO ncbi_metadata VALUES (1,'SRR1'),(2,'SRR2'),(3,'SRR3'),(4,'SRR4')")
    connection.close()
    return path


@pytest.fixture
def accessions(tmp_path):
    path = tmp_path / 'only.txt'
    path.write_text('SRR2\nSRR4\nNOT_IN_THE_DATABASE\n\nSRR2\n')
    return str(path)


def test_the_table_holds_the_run_ids_of_the_listed_runs(database, accessions):
    weebill_only_load.load_weebill_only(database, accessions)
    assert _query(database, 'SELECT run_id FROM weebill_only_runs ORDER BY run_id') == [(2,), (4,)]


def test_the_counts_say_how_many_were_listed_flagged_and_unknown(database, accessions):
    assert weebill_only_load.load_weebill_only(database, accessions) == {
        'listed': 3, 'flagged': 2, 'unknown': 1, 'runs': 4}


def test_running_it_again_gives_the_same_result_and_a_new_list_replaces_the_old(database, accessions, tmp_path):
    weebill_only_load.load_weebill_only(database, accessions)
    weebill_only_load.load_weebill_only(database, accessions)
    assert _query(database, 'SELECT count(*) FROM weebill_only_runs')[0][0] == 2
    other = tmp_path / 'other.txt'
    other.write_text('SRR1\n')
    weebill_only_load.load_weebill_only(database, str(other))
    assert _query(database, 'SELECT run_id FROM weebill_only_runs') == [(1,)]


def test_no_other_table_is_changed(database, accessions):
    weebill_only_load.load_weebill_only(database, accessions)
    assert _query(database, 'SELECT id, acc FROM ncbi_metadata ORDER BY id') == [(1, 'SRR1'), (2, 'SRR2'), (3, 'SRR3'), (4, 'SRR4')]


def test_a_missing_list_file_is_an_error_and_makes_no_table(database, tmp_path):
    with pytest.raises(FileNotFoundError):
        weebill_only_load.load_weebill_only(database, str(tmp_path / 'nope.txt'))
    assert _query(database, "SELECT count(*) FROM information_schema.tables WHERE table_name = 'weebill_only_runs'")[0][0] == 0


def test_an_empty_list_is_refused_because_it_would_clear_every_flag(database, accessions, tmp_path):
    weebill_only_load.load_weebill_only(database, accessions)
    empty = tmp_path / 'empty.txt'
    empty.write_text('\n')
    with pytest.raises(ValueError, match='empty'):
        weebill_only_load.load_weebill_only(database, str(empty))
    assert _query(database, 'SELECT count(*) FROM weebill_only_runs')[0][0] == 2   # the earlier result is kept
