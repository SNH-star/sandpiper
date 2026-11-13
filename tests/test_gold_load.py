import json
import os
import sys

import duckdb
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sandpiper import gold_load  # noqa: E402


def _write(directory, stem, entries):
    with open(os.path.join(str(directory), stem + '.jsonl'), 'w') as handle:
        for gold_id, record in entries:
            handle.write(json.dumps({'id': gold_id, 'record': record}) + '\n')


def _rows(db_path, sql):
    connection = duckdb.connect(db_path, read_only=True)
    try:
        return connection.execute(sql).fetchall()
    finally:
        connection.close()


@pytest.fixture
def download(tmp_path):
    folder = tmp_path / 'gold'
    folder.mkdir()
    _write(folder, 'projects', [('Gp1', {'projectGoldId': 'Gp1', 'seqMethod': ['Illumina'], 'jgiFundingYear': 2016}),
                                ('Gp2', {'projectGoldId': 'Gp2', 'jgiFundingYear': 2017, 'newField': 'x'}),
                                ('Gp3', None)])
    _write(folder, 'biosamples', [('Gb1', {'biosampleGoldId': 'Gb1', 'ph': 7.5, 'latitude': '1.0'})])
    _write(folder, 'studies', [('Gs1', {'studyGoldId': 'Gs1', 'studyName': 'S'})])
    _write(folder, 'analysis_projects', [('Gp1', [{'apGoldId': 'Ga1'}, {'apGoldId': 'Ga2'}]), ('Gp2', [])])
    return str(folder)


def test_every_gold_field_becomes_a_column_and_unknown_projects_are_skipped(tmp_path, download):
    db = str(tmp_path / 'x.duckdb')
    counts = gold_load.load_gold(db, download)
    assert counts == {'gold_projects': 2, 'gold_biosamples': 1, 'gold_studies': 1, 'gold_analysis_projects': 2}
    columns = {row[0] for row in _rows(db, 'DESCRIBE gold_projects')}
    assert {'gold_project_id', 'projectGoldId', 'seqMethod', 'jgiFundingYear', 'newField'} <= columns


def test_numbers_stay_numeric_and_lists_are_json_text(tmp_path, download):
    db = str(tmp_path / 'x.duckdb')
    gold_load.load_gold(db, download)
    assert _rows(db, "SELECT typeof(ph) FROM gold_biosamples") == [('DOUBLE',)]
    assert _rows(db, "SELECT seqMethod FROM gold_projects WHERE gold_project_id = 'Gp1'") == [('["Illumina"]',)]
    assert _rows(db, "SELECT typeof(jgiFundingYear) FROM gold_projects LIMIT 1")[0][0] in ('BIGINT', 'INTEGER')


def test_analysis_projects_get_one_row_each_keyed_by_project(tmp_path, download):
    db = str(tmp_path / 'x.duckdb')
    gold_load.load_gold(db, download)
    assert _rows(db, 'SELECT gold_project_id, apGoldId FROM gold_analysis_projects ORDER BY apGoldId') == [
        ('Gp1', 'Ga1'), ('Gp1', 'Ga2')]


def test_loading_twice_replaces_the_tables(tmp_path, download):
    db = str(tmp_path / 'x.duckdb')
    gold_load.load_gold(db, download)
    gold_load.load_gold(db, download)
    assert _rows(db, 'SELECT count(*) FROM gold_projects') == [(2,)]


def test_empty_download_gives_empty_tables_not_an_error(tmp_path):
    folder = tmp_path / 'empty'
    folder.mkdir()
    db = str(tmp_path / 'x.duckdb')
    assert set(gold_load.load_gold(db, str(folder)).values()) == {0}


def test_missing_directory_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        gold_load.load_gold(str(tmp_path / 'x.duckdb'), str(tmp_path / 'nope'))
