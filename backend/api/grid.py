"""
grid.py
- Shared parsing and SQL for the `grid:` search key (pick squares on the map).

A grid value is semicolon-separated "latitude/longitude" pairs, each the
south-west corner of one map square, e.g. "10/-60;15/-60". A pair may end in a
sample type ("30/115/host", "10/-60/ecological"): that square then only
matches runs of that type, so one search can mix host-associated and
ecological squares. A run matches when it falls in any listed square. Squares are half-open ([corner, corner + size))
so they use the same floor() binning as the statistics map, and a run on a
shared edge belongs to exactly one square.
"""
from typing import Optional

from sqlalchemy import and_, or_

from .statistics_figures import MAP_CELL_DEGREES

MAX_GRID_SQUARES = 200
SAMPLE_TYPES = ('host', 'ecological')
LAT_RANGE = (-90, 90)
LON_RANGE = (-180, 180)


def _parse_corner(text: str) -> Optional[tuple]:
    parts = text.strip().split('/')
    if len(parts) not in (2, 3):
        return None
    sample_type = parts[2] if len(parts) == 3 else None
    if sample_type is not None and sample_type not in SAMPLE_TYPES:
        return None
    try:
        lat, lon = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    on_grid = lat % MAP_CELL_DEGREES == 0 and lon % MAP_CELL_DEGREES == 0
    on_earth = LAT_RANGE[0] <= lat < LAT_RANGE[1] and LON_RANGE[0] <= lon < LON_RANGE[1]
    if not (on_grid and on_earth):
        return None
    return (lat, lon) if sample_type is None else (lat, lon, sample_type)


def parse_grid_squares(value: str) -> Optional[list]:
    """'10/-60;15/-60/host' -> [(10, -60), (15, -60, 'host')]. None when there is nothing to
    search or any square is malformed, so a typo never silently widens a search."""
    squares = []
    for raw in value.split(';'):
        if not raw.strip():
            continue
        corner = _parse_corner(raw)
        if corner is None:
            return None
        if corner not in squares:
            squares.append(corner)
    return squares[:MAX_GRID_SQUARES] or None


def _square_condition(parsed, square: tuple):
    size = MAP_CELL_DEGREES
    lat, lon, *sample_type = square
    parts = [parsed.latitude >= lat, parsed.latitude < lat + size,
             parsed.longitude >= lon, parsed.longitude < lon + size]
    if sample_type:
        parts.append(parsed.host_or_not_mature == sample_type[0])
    return and_(*parts)


def grid_condition(parsed, squares: list):
    """SQL matching runs inside any of `squares` (from parse_grid_squares); a
    square with a sample type also requires that type."""
    return or_(*(_square_condition(parsed, square) for square in squares))


def _describe_group(squares: list, label: str) -> str:
    size = MAP_CELL_DEGREES
    lats = [square[0] for square in squares]
    lons = [square[1] for square in squares]
    noun = f'{label}square' if not label else f'{label} square'
    return (f'{len(squares)} {noun}{"s" if len(squares) != 1 else ""} of {size}° '
            f'(latitude {min(lats)}° to {max(lats) + size}°, longitude {min(lons)}° to {max(lons) + size}°)')


def describe_grid(squares: list) -> str:
    """One kind of square reads 'grid: 2 host squares of 5° (...)'; a mix is listed
    per sample type, e.g. '(grid: 1 host square of 5° (...) OR 2 ecological squares of 5° (...))'."""
    groups = [(label, [q for q in squares if (q[2] if len(q) == 3 else '') == label])
              for label in ('', *SAMPLE_TYPES)]
    described = [_describe_group(members, label) for label, members in groups if members]
    if len(described) == 1:
        return f'grid: {described[0]}'
    return f'(grid: {" OR ".join(described)})'
