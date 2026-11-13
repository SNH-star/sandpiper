"""GOLD (JGI) records read from the database's gold_* tables (api/gold_db.py)."""
import json
import os
import sys

import pytest
from sqlalchemy import create_engine, select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api import gold_db  # noqa: E402
from sandpiper import gold_load  # noqa: E402


def _write(directory, stem, entries):
    with open(os.path.join(str(directory), stem + '.jsonl'), 'w') as handle:
        for gold_id, record in entries:
            handle.write(json.dumps({'id': gold_id, 'record': record}) + '\n')


PROJECTS = [
    ('Gp1', {'projectGoldId': 'Gp1', 'projectName': 'Eye swab', 'biosampleGoldId': 'Gb1', 'studyGoldId': 'Gs1',
             'projectStatus': 'Permanent Draft', 'seqMethod': ['Illumina HiSeq'],
             'sequencingCenters': ['DOE Joint Genome Institute (JGI)'], 'jgiFundingYear': 2015,
             'genomePublications': [{'pubmedId': 1, 'doi': '10.1/a', 'title': 'Eyes', 'journalName': 'J', 'publicationDate': None}],
             'otherPublications': [], 'sraExperimentIds': ['SRX1']}),
    ('Gp2', {'projectGoldId': 'Gp2', 'projectName': 'Soil core', 'biosampleGoldId': 'Gb2', 'studyGoldId': 'Gs1',
             'projectStatus': 'Complete', 'seqMethod': ['NovaSeq'], 'sequencingCenters': ['JGI'], 'jgiFundingYear': 2020,
             'genomePublications': [], 'otherPublications': [], 'sraExperimentIds': []}),
    ('Gp3', {'projectGoldId': 'Gp3', 'projectName': 'Lone', 'biosampleGoldId': None, 'studyGoldId': 'Gs9'}),
    ('Gp4', None),
]
BIOSAMPLES = [
    ('Gb1', {'biosampleGoldId': 'Gb1', 'habitat': 'Human eye', 'ecosystem': 'Host-associated', 'ph': '7.1',
             'latitude': 40.5, 'longitude': -81.0, 'description': 'Swab of the conjunctiva',
             'envoMedium': {'id': 'ENVO_1', 'label': 'tears'}, 'sampleBodySite': 'Eye'}),
    ('Gb2', {'biosampleGoldId': 'Gb2', 'habitat': 'Grassland soil', 'ecosystem': 'Environmental', 'ph': '5.8',
             'latitude': None, 'longitude': None, 'description': 'Soil from Hopland', 'sampleBodySite': None}),
]
STUDIES = [('Gs1', {'studyGoldId': 'Gs1', 'studyName': 'Microbiomes of the eye and soil', 'description': 'A study.'})]
ANALYSIS = [('Gp1', [{'apGoldId': 'Ga1', 'apName': 'Eye assembly', 'assemblyMethod': 'MEGAHIT v1'}]), ('Gp2', [])]


@pytest.fixture
def engine(tmp_path):
    folder = tmp_path / 'gold'
    folder.mkdir()
    _write(folder, 'projects', PROJECTS)
    _write(folder, 'biosamples', BIOSAMPLES)
    _write(folder, 'studies', STUDIES)
    _write(folder, 'analysis_projects', ANALYSIS)
    db_path = str(tmp_path / 'db.duckdb')
    gold_load.load_gold(db_path, str(folder))
    eng = create_engine('duckdb:///' + db_path)
    yield eng
    eng.dispose()


@pytest.fixture
def connection(engine):
    with engine.connect() as conn:
        yield conn


def _ids(connection, query):
    return sorted(connection.execute(query).scalars().all()) if query is not None else None


# --- reading one project -------------------------------------------------------------------------

def test_a_summary_has_the_same_rows_publications_and_link_as_the_live_service_gave(connection):
    summary = gold_db.fetch_summary(connection, 'Gp1')
    by_key = {row['k']: row['v'] for row in summary['rows']}
    assert summary['project_id'] == 'Gp1'
    assert summary['url'] == 'https://gold.jgi.doe.gov/project?id=Gp1'
    assert by_key['GOLD habitat'] == 'Human eye'
    assert by_key['GOLD sequencing platform'] == 'Illumina HiSeq'       # list column read back from text
    assert by_key['GOLD ENVO medium'] == 'tears (ENVO_1)'              # object column read back from text
    assert by_key['GOLD study'] == 'Microbiomes of the eye and soil'
    assert [p['pubmed_id'] for p in summary['publications']] == ['1']


def test_empty_values_are_not_shown_as_rows(connection):
    by_key = {row['k'] for row in gold_db.fetch_summary(connection, 'Gp2')['rows']}
    assert 'GOLD coordinates' not in by_key and 'GOLD body site' not in by_key


def test_a_project_without_a_biosample_or_known_study_still_gives_a_summary(connection):
    summary = gold_db.fetch_summary(connection, 'Gp3')
    assert {row['k'] for row in summary['rows']} >= {'GOLD project ID', 'GOLD project name'}
    assert not any(row['k'].startswith('GOLD study') for row in summary['rows'])


def test_unknown_and_empty_projects_give_none(connection):
    assert gold_db.fetch_summary(connection, 'Gp404') is None
    assert gold_db.fetch_summary(connection, 'Gp4') is None   # GOLD had nothing for it


def test_several_projects_are_read_in_one_go_and_unknown_ones_left_out(connection):
    summaries = gold_db.fetch_summaries(connection, ['Gp1', 'Gp2', 'Gp404'])
    assert sorted(summaries) == ['Gp1', 'Gp2']
    assert gold_db.fetch_summaries(connection, []) == {}


def test_nothing_is_read_when_the_gold_tables_are_missing(tmp_path):
    eng = create_engine('duckdb:///' + str(tmp_path / 'empty.duckdb'))
    with eng.connect() as conn:
        assert gold_db.fetch_summary(conn, 'Gp1') is None
        assert gold_db.fetch_summaries(conn, ['Gp1']) == {}
        assert gold_db.load_schema(conn).is_empty
    eng.dispose()


# --- searching -----------------------------------------------------------------------------------

def test_the_schema_lists_every_searchable_field_once_whatever_table_it_is_in(connection):
    fields = gold_db.load_schema(connection).field_names()
    assert 'habitat' in fields and 'projectName' in fields and 'studyName' in fields and 'apName' in fields
    assert len(fields) == len(set(fields))
    assert fields == sorted(fields, key=str.lower)


def test_field_equals_value_matches_only_that_field(connection):
    schema = gold_db.load_schema(connection)
    assert _ids(connection, gold_db.matching_project_ids(schema, 'habitat=eye')) == ['Gp1']
    assert _ids(connection, gold_db.matching_project_ids(schema, 'habitat=soil')) == ['Gp2']
    # 'eye' is in a project name and a study name but not in these habitats
    assert _ids(connection, gold_db.matching_project_ids(schema, 'habitat=swab')) == []


def test_field_names_ignore_case_spaces_and_underscores(connection):
    schema = gold_db.load_schema(connection)
    for spelling in ('project_name=x', 'Project Name=x', 'PROJECTNAME=x', 'project-name=x'):
        assert gold_db.matching_project_ids(schema, spelling) is not None
    assert _ids(connection, gold_db.matching_project_ids(schema, 'Sample Body Site=eye')) == ['Gp1']


def test_a_field_in_the_study_table_finds_the_projects_of_that_study(connection):
    schema = gold_db.load_schema(connection)
    assert _ids(connection, gold_db.matching_project_ids(schema, 'studyName=soil')) == ['Gp1', 'Gp2']


def test_a_field_in_the_analysis_table_finds_its_project(connection):
    schema = gold_db.load_schema(connection)
    assert _ids(connection, gold_db.matching_project_ids(schema, 'assemblyMethod=megahit')) == ['Gp1']


def test_a_bare_word_matches_any_field_in_any_table_junk_included(connection):
    schema = gold_db.load_schema(connection)
    # 'eye' appears in a habitat, a project name, a study name, a body site and an analysis project name
    assert _ids(connection, gold_db.matching_project_ids(schema, 'eye')) == ['Gp1', 'Gp2']
    assert _ids(connection, gold_db.matching_project_ids(schema, 'hopland')) == ['Gp2']
    assert _ids(connection, gold_db.matching_project_ids(schema, 'NovaSeq')) == ['Gp2']   # inside a list column


def test_numbers_are_searched_as_text(connection):
    schema = gold_db.load_schema(connection)
    assert _ids(connection, gold_db.matching_project_ids(schema, 'latitude=40.5')) == ['Gp1']
    assert _ids(connection, gold_db.matching_project_ids(schema, 'jgiFundingYear=2020')) == ['Gp2']


def test_an_unknown_field_matches_nothing_and_says_so(connection):
    schema = gold_db.load_schema(connection)
    assert gold_db.matching_project_ids(schema, 'nonsense=eye') is None


def test_percent_and_underscore_in_the_value_are_taken_literally(connection):
    schema = gold_db.load_schema(connection)
    assert _ids(connection, gold_db.matching_project_ids(schema, 'habitat=%')) == []
    assert _ids(connection, gold_db.matching_project_ids(schema, 'habitat=_')) == []


def test_a_value_is_never_treated_as_sql(connection):
    schema = gold_db.load_schema(connection)
    assert _ids(connection, gold_db.matching_project_ids(schema, "habitat=x'; DROP TABLE gold_projects; --")) == []
    assert gold_db.fetch_summary(connection, 'Gp1') is not None


def test_a_search_on_a_database_without_gold_tables_matches_nothing(tmp_path):
    eng = create_engine('duckdb:///' + str(tmp_path / 'empty.duckdb'))
    with eng.connect() as conn:
        assert gold_db.matching_project_ids(gold_db.load_schema(conn), 'eye') is None
    eng.dispose()


def test_the_result_can_be_used_inside_a_larger_query(connection):
    schema = gold_db.load_schema(connection)
    project_ids = gold_db.matching_project_ids(schema, 'habitat=eye')
    # the way api.py uses it: ``BiosampleAttribute.v.in_(project_ids)``
    from sqlalchemy import literal
    query = select(literal('x')).where(literal('Gp1').in_(project_ids))
    assert connection.execute(query).scalars().all() == ['x']


# --- partly loaded or empty tables (found in review) ---------------------------------------------

def _database(tmp_path, **files):
    """A database loaded from the given jsonl entries (stem -> entries); stems left out are empty files."""
    folder = tmp_path / 'gold'
    folder.mkdir()
    for stem in ('projects', 'biosamples', 'studies', 'analysis_projects'):
        _write(folder, stem, files.get(stem, []))
    db_path = str(tmp_path / 'partial.duckdb')
    gold_load.load_gold(db_path, str(folder))
    return create_engine('duckdb:///' + db_path)


def test_an_empty_biosample_table_does_not_break_summaries_or_searches(tmp_path):
    eng = _database(tmp_path, projects=PROJECTS, studies=STUDIES, analysis_projects=ANALYSIS)
    with eng.connect() as conn:
        assert gold_db.fetch_summary(conn, 'Gp1')['project_id'] == 'Gp1'
        schema = gold_db.load_schema(conn)
        assert _ids(conn, gold_db.matching_project_ids(schema, 'eye')) == ['Gp1', 'Gp2']
        assert gold_db.matching_project_ids(schema, 'habitat=eye') is None
    eng.dispose()


def test_an_empty_study_table_does_not_break_summaries_or_searches(tmp_path):
    eng = _database(tmp_path, projects=PROJECTS, biosamples=BIOSAMPLES)
    with eng.connect() as conn:
        assert gold_db.fetch_summary(conn, 'Gp1') is not None
        assert _ids(conn, gold_db.matching_project_ids(gold_db.load_schema(conn), 'habitat=eye')) == ['Gp1']
    eng.dispose()


def test_an_empty_project_table_means_there_is_no_gold_data(tmp_path):
    eng = _database(tmp_path, biosamples=BIOSAMPLES, studies=STUDIES)
    with eng.connect() as conn:
        schema = gold_db.load_schema(conn)
        assert schema.is_empty
        assert gold_db.matching_project_ids(schema, 'eye') is None
        assert gold_db.fetch_summaries(conn, ['Gp1']) == {}
    eng.dispose()


def test_a_database_with_only_a_study_table_matches_nothing(tmp_path):
    path = str(tmp_path / 'studies_only.duckdb')
    import duckdb
    con = duckdb.connect(path)
    con.execute("CREATE TABLE gold_studies AS SELECT 'Gs1' AS \"studyGoldId\", 'eye' AS \"studyName\"")
    con.close()
    eng = create_engine('duckdb:///' + path)
    with eng.connect() as conn:
        schema = gold_db.load_schema(conn)
        assert schema.is_empty and gold_db.matching_project_ids(schema, 'eye') is None
    eng.dispose()


def test_a_schema_read_before_the_tables_existed_is_not_remembered(tmp_path):
    path = str(tmp_path / 'late.duckdb')
    eng = create_engine('duckdb:///' + path)
    with eng.connect() as conn:
        assert gold_db.get_schema(conn).is_empty
    eng.dispose()
    folder = tmp_path / 'gold'
    folder.mkdir()
    for stem, entries in (('projects', PROJECTS), ('biosamples', BIOSAMPLES), ('studies', STUDIES), ('analysis_projects', ANALYSIS)):
        _write(folder, stem, entries)
    gold_load.load_gold(path, str(folder))
    eng = create_engine('duckdb:///' + path)
    with eng.connect() as conn:
        assert not gold_db.get_schema(conn).is_empty
    eng.dispose()


def test_tables_of_the_same_name_in_another_schema_are_ignored(tmp_path):
    import duckdb
    path = str(tmp_path / 'two_schemas.duckdb')
    con = duckdb.connect(path)
    con.execute('CREATE SCHEMA other')
    con.execute('CREATE TABLE other.gold_projects AS SELECT 1 AS "somethingElse"')
    con.close()
    eng = create_engine('duckdb:///' + path)
    with eng.connect() as conn:
        assert gold_db.load_schema(conn).is_empty
    eng.dispose()
