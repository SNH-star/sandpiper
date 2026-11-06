import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api.keywords import MAX_KEYWORD_TERMS, like_pattern, parse_keyword_terms  # noqa: E402


def test_terms_split_on_commas_and_keep_phrases():
    assert parse_keyword_terms('sponge reef, coral') == ['sponge reef', 'coral']


def test_terms_drop_blanks_and_duplicates():
    assert parse_keyword_terms(' Sponge ,, sponge ,  ,coral') == ['Sponge', 'coral']


def test_terms_empty_value_gives_no_terms():
    assert parse_keyword_terms('') == []
    assert parse_keyword_terms(' , ,') == []


def test_terms_are_capped():
    value = ', '.join(f'w{i}' for i in range(MAX_KEYWORD_TERMS + 5))
    assert len(parse_keyword_terms(value)) == MAX_KEYWORD_TERMS


def test_like_pattern_escapes_wildcards():
    assert like_pattern('50%_x!') == '%50!%!_x!!%'



def test_metagenome_condition_is_one_or_per_term_anded():
    from api.api import _parse_search_condition
    cond, desc, p_join, c_join = _parse_search_condition('keywords', 'sponge reef, coral')
    sql = str(cond.compile(compile_kwargs={'literal_binds': True})).lower()
    assert sql.count(' and ') == 1          # two terms joined by AND
    for column in ('study_title', 'study_abstract', 'geo_loc_name', 'taxon_name', 'bioproject'):
        assert sql.count(column) >= 2        # each term checked against each column
    assert '%sponge reef%' in sql and '%coral%' in sql
    assert desc == 'keywords: sponge reef AND coral'
    assert (p_join, c_join) == (False, False)


def test_metagenome_empty_keywords_is_not_a_condition():
    from api.api import _parse_search_condition
    assert _parse_search_condition('keywords', ' , ')[0] is None


def test_metagenome_condition_runs_on_duckdb():
    """The compiled SQL (including ESCAPE) must be accepted by DuckDB itself."""
    from sqlalchemy import Column, Integer, String, create_engine, select
    from sqlalchemy.orm import Session, declarative_base
    from api import api as api_module

    Base = declarative_base()

    class Row(Base):
        __tablename__ = 'rows'
        id = Column(Integer, primary_key=True, autoincrement=False)
        study_title = Column(String)
        study_abstract = Column(String)
        geo_loc_name = Column(String)
        taxon_name = Column(String)
        bioproject = Column(String)
        sra_study = Column(String)

    engine = create_engine('duckdb:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([
            Row(id=1, study_title='Sponge microbiome', study_abstract='A sponge reef survey', geo_loc_name='Pacific'),
            Row(id=2, study_title='Soil', study_abstract='50% moisture_x', geo_loc_name='Peru'),
        ])
        session.commit()

        def ids(value):
            columns = (Row.study_title, Row.study_abstract, Row.geo_loc_name)
            cond = api_module._keywords_condition(parse_keyword_terms(value), columns)
            return sorted(session.scalars(select(Row.id).where(cond)))

        assert ids('sponge reef, pacific') == [1]   # two columns/terms, one row
        assert ids('sponge, peru') == []
        assert ids('50%') == [2] and ids('%') == [2]
        assert ids('moisture_x') == [2] and ids('moisture-x') == []


def _sql(condition):
    return str(condition.compile(compile_kwargs={'literal_binds': True})).lower()


def test_full_accession_has_an_exact_and_a_prefix_condition():
    from api.api import _accession_conditions
    exact, prefix, desc = _accession_conditions('ERR1950668')
    assert 'ncbi_metadata.acc = ' in _sql(exact) and "'err1950668'" in _sql(exact)
    assert 'like' in _sql(prefix) and "'err1950668%'" in _sql(prefix)
    assert desc == 'run accession starting ERR1950668'


def test_partial_accession_and_bare_prefix_are_accepted():
    from api.api import _accession_conditions
    assert _accession_conditions('ERR12564') is not None
    assert _accession_conditions('err') is not None
    assert _accession_conditions(' srr123 ') is not None


def test_run_biosample_and_bioproject_accessions_use_their_columns():
    from api.api import _accession_conditions
    for token, column in (('SRR1', 'acc'), ('SAMN123', 'biosample'), ('SAMEA123', 'biosample'),
                          ('PRJNA123', 'bioproject'), ('PRJEB', 'bioproject')):
        exact, _, _ = _accession_conditions(token)
        assert f'ncbi_metadata.{column} =' in _sql(exact), token


def test_experiment_sample_and_study_accessions_search_the_raw_biosample_attributes():
    """Those NCBI columns are empty in the database; the values live in the
    biosample attributes under these keys."""
    from api.api import _accession_conditions
    for token, key in (('SRX123', 'experiment_accession'), ('ERX2016395', 'experiment_accession'),
                       ('ERS1696253', 'sample_accession'), ('DRS1', 'sample_accession'),
                       ('SRP123', 'study_accession'), ('ERP022611', 'study_accession')):
        exact, prefix, _ = _accession_conditions(token)
        for condition in (exact, prefix):
            sql = _sql(condition)
            assert 'biosample_attributes' in sql and f"k = '{key}'" in sql, token


def test_keyed_identifier_searches_use_the_raw_attributes_too():
    from api.api import _parse_search_condition
    for key, attribute in (('sample_acc', 'sample_accession'), ('experiment', 'experiment_accession'),
                           ('sra_study', 'study_accession')):
        sql = _sql(_parse_search_condition(key, 'xyz')[0])
        assert f"k = '{attribute}'" in sql and 'biosample_attributes' in sql, key


def test_ordinary_words_are_not_accessions():
    from api.api import _accession_conditions
    for token in ('coral', 'soil sample', 'ERR12x', 'Pacific Ocean', 'SAM', 'PRJ', 'errors'):
        assert _accession_conditions(token) is None, token


def test_sample_name_is_searched_by_free_text_and_keywords():
    from api.api import parse_universal_query
    sql = _sql(parse_universal_query('Sample3_Uganda').conditions[0])
    assert 'sample_name' in sql
    from api.api import _parse_search_condition
    assert 'sample_name' in _sql(_parse_search_condition('keywords', 'uganda')[0])
