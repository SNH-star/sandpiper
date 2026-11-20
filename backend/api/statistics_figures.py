"""Figures for the Statistics page's year breakdown and sample map.

Each `*_payload` function is pure: it shapes rows already read from the database,
so it can be tested without one. The `query_*` functions do the reading.
"""
import math
from collections.abc import Iterable

from sqlalchemy import Integer, select
from sqlalchemy.sql import func

from .models import NcbiMetadata, ParsedSampleAttribute, Taxonomy

MAP_CELL_DEGREES = 5
# Width of a map hexagon, flat side to flat side, in degrees of longitude.
MAP_HEX_DEGREES = 2
HEX_ROW_RATIO = math.sqrt(3) / 2
COORDINATE_DECIMALS = 3
CALL_KEYS = {'host': 'host_associated', 'ecological': 'ecological'}
UNCLASSIFIED = 'unclassified'
TAXONOMY_LEVELS = ('domain', 'phylum', 'class', 'order', 'family', 'genus', 'species')
SAMPLE_TYPE_LEVELS = TAXONOMY_LEVELS[1:]


def year_breakdown_payload(call_rows):
    """Runs per release year split by sample call, with the running total.

    call_rows: (year, call, runs); rows without a year are skipped.
    """
    by_year = {}
    for year, call, runs in call_rows:
        if year is None:
            continue
        row = by_year.setdefault(int(year), {'host_associated': 0, 'ecological': 0, UNCLASSIFIED: 0})
        row[CALL_KEYS.get(call, UNCLASSIFIED)] += runs
    years, running = [], 0
    for year in sorted(by_year):
        running += sum(by_year[year].values())
        years.append({'year': year, **by_year[year], 'cumulative': running})
    return {'years': years}


def map_cells_payload(rows):
    """Runs per grid cell, with how many are host-associated or ecological and
    the mean known species fraction (0 to 100).

    rows: (latitude cell, longitude cell, runs, host runs, ecological runs, mean fraction or None).
    """
    return {
        'cell': MAP_CELL_DEGREES,
        'cells': [{'lat': lat, 'lon': lon, 'runs': runs, 'host_associated': host, 'ecological': ecological,
                   'known': None if mean is None else round(100 * mean, 1)}
                  for lat, lon, runs, host, ecological, mean in rows],
    }


def _round_half_up(value: float) -> int:
    """Nearest whole number, with halves going up, so a point on a shared edge always goes the same way."""
    return math.floor(value + 0.5)


def hex_index(lon: float, lat: float, width: float) -> tuple[int, int]:
    """(row, column) of the hexagon holding a point.

    The hexagons are pointy-topped and `width` degrees across. Rows of centres sit
    width * sqrt(3) / 2 apart, and every odd row is shifted half a hexagon east. A point
    on a hexagon's west edge belongs to it; one on its east edge belongs to its neighbour.
    """
    row_height = width * HEX_ROW_RATIO
    row_position = lat / row_height
    row = _round_half_up(row_position)
    column_position = lon / width - (row % 2) / 2
    column = _round_half_up(column_position)
    row_offset = row_position - row
    # Within a third of a row of the centre line the point is surely in this row;
    # further out it may belong to the neighbouring row, so take the nearer centre.
    if abs(row_offset) * 3 > 1:
        other_row = row + (1 if row_offset > 0 else -1)
        other_column_position = lon / width - (other_row % 2) / 2
        other_column = _round_half_up(other_column_position)
        here = ((column_position - column) * width) ** 2 + (row_offset * row_height) ** 2
        there = (((other_column_position - other_column) * width) ** 2
                 + ((row_position - other_row) * row_height) ** 2)
        if there < here:
            row, column = other_row, other_column
    return row, column


def hex_centre_of(row: int, column: int, width: float) -> tuple[float, float]:
    """Unrounded centre (lon, lat) of the hexagon at (row, column)."""
    return (column + (row % 2) / 2) * width, row * width * HEX_ROW_RATIO


def hex_centre(lon: float, lat: float, width: float) -> tuple[float, float]:
    """Centre (lon, lat) of the hexagon holding a point, rounded for the map (see `hex_index`)."""
    centre_lon, centre_lat = hex_centre_of(*hex_index(lon, lat, width), width)
    return round(centre_lon, COORDINATE_DECIMALS), round(centre_lat, COORDINATE_DECIMALS)


def map_hexes_payload(rows: Iterable[tuple[float, float, int, int]], width: float = MAP_HEX_DEGREES) -> dict:
    """Host-associated and ecological runs per map hexagon, for hexagons holding either.

    rows: (latitude, longitude, host runs, ecological runs), one per distinct coordinate.
    """
    totals = {}
    for lat, lon, host, ecological in rows:
        if not host and not ecological:
            continue
        centre = hex_centre(lon, lat, width)
        seen_host, seen_ecological = totals.get(centre, (0, 0))
        totals[centre] = (seen_host + host, seen_ecological + ecological)
    return {
        'width': width,
        'hexes': [{'lon': lon, 'lat': lat, 'host_associated': host, 'ecological': ecological}
                  for (lon, lat), (host, ecological) in sorted(totals.items(), key=lambda item: item[0][::-1])],
    }


def query_year_breakdown(session):
    year = func.extract('year', NcbiMetadata.published)
    return year_breakdown_payload(session.execute(select(
        year, ParsedSampleAttribute.host_or_not_mature, func.count()).join(
        ParsedSampleAttribute, ParsedSampleAttribute.run_id == NcbiMetadata.id, isouter=True).group_by(
        year, ParsedSampleAttribute.host_or_not_mature)).all())


def query_map_cells(session):
    parsed = ParsedSampleAttribute
    lat = (func.floor(parsed.latitude / MAP_CELL_DEGREES) * MAP_CELL_DEGREES).cast(Integer)
    lon = (func.floor(parsed.longitude / MAP_CELL_DEGREES) * MAP_CELL_DEGREES).cast(Integer)
    return map_cells_payload(session.execute(select(
        lat, lon, func.count(),
        func.count().filter(parsed.host_or_not_mature == 'host'),
        func.count().filter(parsed.host_or_not_mature == 'ecological'),
        func.avg(parsed.known_species_fraction)).where(
        parsed.latitude.between(-90, 90), parsed.longitude.between(-180, 180)).group_by(lat, lon)).all())


def query_map_hexes(session):
    parsed = ParsedSampleAttribute
    return map_hexes_payload(session.execute(select(
        parsed.latitude, parsed.longitude,
        func.count().filter(parsed.host_or_not_mature == 'host'),
        func.count().filter(parsed.host_or_not_mature == 'ecological')).where(
        parsed.latitude.between(-90, 90), parsed.longitude.between(-180, 180)).group_by(
        parsed.latitude, parsed.longitude)).all())


def taxa_by_sample_type_payload(rows: Iterable[tuple[str, bool, bool, int]]) -> dict:
    """How many GTDB taxa are found in host-associated runs only, in ecological runs only, and in both, per level.

    Each row is (level, found in host-associated runs, found in ecological runs, number of taxa). Taxa found in
    neither are left out, and so is the domain level (there are only two domains).
    """
    counts: dict[str, dict[str, int]] = {}
    for level, host, ecological, taxa in rows:
        if level not in SAMPLE_TYPE_LEVELS or not (host or ecological):
            continue
        cell = counts.setdefault(level, {'host_only': 0, 'ecological_only': 0, 'both': 0})
        cell['both' if host and ecological else 'host_only' if host else 'ecological_only'] += taxa
    levels = [level for level in SAMPLE_TYPE_LEVELS if level in counts]
    return {'levels': levels, 'counts': {level: counts[level] for level in levels}}


def query_taxa_by_sample_type(session):
    """GTDB taxa by the kind of run they are found in, counted by the database: one row per level and pattern."""
    host = func.coalesce(Taxonomy.host_sample_count, 0) > 0
    ecological = func.coalesce(Taxonomy.ecological_sample_count, 0) > 0
    return taxa_by_sample_type_payload(session.execute(select(
        Taxonomy.taxonomy_level, host, ecological, func.count()).where(
        Taxonomy.taxonomy_type == 'gtdb', Taxonomy.taxonomy_level.in_(SAMPLE_TYPE_LEVELS)).group_by(
        Taxonomy.taxonomy_level, host, ecological)).all())
