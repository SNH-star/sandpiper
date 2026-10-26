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
