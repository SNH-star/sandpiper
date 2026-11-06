"""Figures for the Statistics page's year breakdown and sample map.

Each `*_payload` function is pure: it shapes rows already read from the database,
so it can be tested without one. The `query_*` functions do the reading.
"""
from sqlalchemy import Integer, select
from sqlalchemy.sql import func

from .models import NcbiMetadata, ParsedSampleAttribute

MAP_CELL_DEGREES = 5
CALL_KEYS = {'host': 'host_associated', 'ecological': 'ecological'}
UNCLASSIFIED = 'unclassified'


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
