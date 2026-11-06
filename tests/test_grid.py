import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api.grid import MAX_GRID_SQUARES, parse_grid_squares  # noqa: E402


def test_squares_parse_from_lat_lon_pairs():
    assert parse_grid_squares('10/-60;15/-60') == [(10, -60), (15, -60)]


def test_squares_can_carry_a_sample_type():
    assert parse_grid_squares('10/-60/host;15/-60/ecological;20/-60') == [
        (10, -60, 'host'), (15, -60, 'ecological'), (20, -60)]


def test_the_same_square_can_be_picked_under_both_types():
    assert parse_grid_squares('10/-60/host;10/-60/ecological;10/-60/host') == [
        (10, -60, 'host'), (10, -60, 'ecological')]


def test_unknown_sample_type_rejects_the_value():
    assert parse_grid_squares('10/-60/soil') is None


def test_squares_drop_repeats_and_blanks():
    assert parse_grid_squares(' 10/-60 ;; 10/-60 ; ') == [(10, -60)]


def test_squares_must_sit_on_the_grid_and_on_earth():
    for bad in ('12/-60', '10/-62', '90/0', '-95/0', '10/180', '10/-185', 'a/b', '10', '10/20/30', '10/-60/host/x'):
        assert parse_grid_squares(bad) is None, bad


def test_one_bad_square_rejects_the_whole_value():
    assert parse_grid_squares('10/-60;12/-60') is None


def test_empty_value_is_not_a_condition():
    assert parse_grid_squares('') is None
    assert parse_grid_squares(' ; ') is None


def test_squares_are_capped():
    value = ';'.join(f'{-90 + 5 * (i // 72)}/{-180 + 5 * (i % 72)}' for i in range(MAX_GRID_SQUARES + 5))
    assert len(parse_grid_squares(value)) == MAX_GRID_SQUARES


def test_search_condition_is_an_or_of_half_open_squares():
    from api.api import _parse_search_condition
    cond, desc, needs_parsed, needs_condensed = _parse_search_condition('grid', '10/-60;15/-60')
    sql = str(cond.compile(compile_kwargs={'literal_binds': True})).lower()
    assert sql.count(' or ') == 1
    assert '>= 10' in sql and '< 15' in sql and '>= -60' in sql and '< -55' in sql
    assert desc == 'grid: 2 squares of 5° (latitude 10° to 20°, longitude -60° to -55°)'
    assert (needs_parsed, needs_condensed) == (True, False)


def test_typed_squares_are_described_per_sample_type():
    from api.grid import describe_grid
    squares = parse_grid_squares('30/115/host;10/-60/ecological;15/-60/ecological')
    assert describe_grid(squares) == (
        '(grid: 1 host square of 5° (latitude 30° to 35°, longitude 115° to 120°) OR '
        '2 ecological squares of 5° (latitude 10° to 20°, longitude -60° to -55°))')


def test_typed_square_condition_pairs_each_square_with_its_sample_type():
    from api.api import _parse_search_condition
    cond, desc, needs_parsed, _ = _parse_search_condition('grid', '30/115/host;10/-60/ecological')
    sql = str(cond.compile(compile_kwargs={'literal_binds': True})).lower()
    assert sql.count(' or ') == 1
    assert "'host'" in sql and "'ecological'" in sql
    assert needs_parsed


def test_search_condition_rejects_a_malformed_grid():
    from api.api import _parse_search_condition
    assert _parse_search_condition('grid', '12/-60')[0] is None


def test_search_condition_matches_the_map_binning_on_duckdb():
    """A run belongs to the square the statistics map puts it in: floor(x / 5) * 5."""
    from sqlalchemy import Column, Float, Integer, create_engine, select
    from sqlalchemy.orm import Session, declarative_base
    from api.grid import grid_condition

    Base = declarative_base()

    class Row(Base):
        __tablename__ = 'rows'
        id = Column(Integer, primary_key=True, autoincrement=False)
        latitude = Column(Float)
        longitude = Column(Float)

    engine = create_engine('duckdb:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([
            Row(id=1, latitude=10.0, longitude=-60.0),    # square (10, -60), lower edge
            Row(id=2, latitude=14.99, longitude=-55.01),  # square (10, -60), upper corner
            Row(id=3, latitude=15.0, longitude=-60.0),    # next square north
            Row(id=4, latitude=10.0, longitude=-55.0),    # next square east
            Row(id=5, latitude=-2.5, longitude=1.0),      # square (-5, 0)
        ])
        session.commit()
        rows = session.scalars(select(Row.id).where(grid_condition(Row, [(10, -60), (-5, 0)])).order_by(Row.id)).all()
    assert rows == [1, 2, 5]


def test_typed_squares_filter_by_their_own_sample_type_on_duckdb():
    from sqlalchemy import Column, Float, Integer, String, create_engine, select
    from sqlalchemy.orm import Session, declarative_base
    from api.grid import grid_condition

    Base = declarative_base()

    class Row(Base):
        __tablename__ = 'typed_rows'
        id = Column(Integer, primary_key=True, autoincrement=False)
        latitude = Column(Float)
        longitude = Column(Float)
        host_or_not_mature = Column(String)

    engine = create_engine('duckdb:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([
            Row(id=1, latitude=31.0, longitude=116.0, host_or_not_mature='host'),
            Row(id=2, latitude=31.0, longitude=116.0, host_or_not_mature='ecological'),
            Row(id=3, latitude=11.0, longitude=-59.0, host_or_not_mature='ecological'),
            Row(id=4, latitude=11.0, longitude=-59.0, host_or_not_mature='host'),
        ])
        session.commit()
        squares = [(30, 115, 'host'), (10, -60, 'ecological')]
        rows = session.scalars(select(Row.id).where(grid_condition(Row, squares)).order_by(Row.id)).all()
    assert rows == [1, 3]
