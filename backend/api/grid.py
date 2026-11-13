"""
grid.py
- Shared parsing and SQL for the `grid:` search key (pick areas on the map).

A grid value is semicolon-separated areas, and a run matches when it falls in any of them.
Two kinds of area can be mixed in one value:

- A square, written "latitude/longitude": the south-west corner of one 5 degree map square,
  e.g. "10/-60;15/-60". Squares are half-open ([corner, corner + size)) so they use the same
  floor() binning as the statistics map's latitude bars, and a run on a shared edge belongs
  to exactly one square.
- A hexagon, written "h<latitude>/<longitude>": the centre of one hexagon of the statistics
  map, e.g. "h51.962/-2". The centre may be rounded as the map rounds it; it is snapped to
  the exact centre, and a value that is not a centre is rejected.

Either may end in a sample type ("30/115/host", "h0/0/ecological"): that area then only
matches runs of that type, so one search can mix host-associated and ecological areas.
"""
import math
from typing import NamedTuple, Optional, Union

from sqlalchemy import and_, func, or_

from .statistics_figures import MAP_CELL_DEGREES, MAP_HEX_DEGREES, hex_centre_of, hex_index

MAX_GRID_SQUARES = 200
SAMPLE_TYPES = ('host', 'ecological')
LAT_RANGE = (-90, 90)
LON_RANGE = (-180, 180)
HEXAGON_PREFIX = 'h'
# How far a written hexagon centre may be from the exact one: the map rounds centres to three decimals.
HEXAGON_CENTRE_TOLERANCE = 0.001
SQRT_3 = math.sqrt(3)


class Hexagon(NamedTuple):
    """One map hexagon, by its exact centre; `sample_type` None matches every type."""
    lat: float
    lon: float
    sample_type: Optional[str]


Area = Union[tuple, Hexagon]


def _split_area(text: str) -> Optional[tuple[str, str, Optional[str]]]:
    """'10/-60/host' -> ('10', '-60', 'host'); None unless it is two numbers and an optional known type."""
    parts = text.strip().split('/')
    if len(parts) not in (2, 3):
        return None
    sample_type = parts[2] if len(parts) == 3 else None
    if sample_type is not None and sample_type not in SAMPLE_TYPES:
        return None
    return parts[0], parts[1], sample_type


def _parse_corner(text: str) -> Optional[tuple]:
    parts = _split_area(text)
    if parts is None:
        return None
    try:
        lat, lon = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    sample_type = parts[2]
    on_grid = lat % MAP_CELL_DEGREES == 0 and lon % MAP_CELL_DEGREES == 0
    on_earth = LAT_RANGE[0] <= lat < LAT_RANGE[1] and LON_RANGE[0] <= lon < LON_RANGE[1]
    if not (on_grid and on_earth):
        return None
    return (lat, lon) if sample_type is None else (lat, lon, sample_type)


def _parse_hexagon(text: str) -> Optional[Hexagon]:
    parts = _split_area(text.strip()[len(HEXAGON_PREFIX):])
    if parts is None:
        return None
    try:
        lat, lon = float(parts[0]), float(parts[1])
    except ValueError:
        return None
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return None
    if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]):
        return None
    centre_lon, centre_lat = hex_centre_of(*hex_index(lon, lat, MAP_HEX_DEGREES), MAP_HEX_DEGREES)
    if max(abs(centre_lat - lat), abs(centre_lon - lon)) > HEXAGON_CENTRE_TOLERANCE:
        return None
    return Hexagon(centre_lat, centre_lon, parts[2])


def parse_grid_squares(value: str) -> Optional[list[Area]]:
    """'10/-60;15/-60/host;h0/0' -> [(10, -60), (15, -60, 'host'), Hexagon(0.0, 0.0, None)]. None when
    there is nothing to search or any area is malformed, so a typo never silently widens a search."""
    areas = []
    for raw in value.split(';'):
        if not raw.strip():
            continue
        is_hexagon = raw.strip().startswith(HEXAGON_PREFIX)
        area = _parse_hexagon(raw) if is_hexagon else _parse_corner(raw)
        if area is None:
            return None
        if area not in areas:
            areas.append(area)
    return areas[:MAX_GRID_SQUARES] or None


def _square_condition(parsed, square: tuple):
    size = MAP_CELL_DEGREES
    lat, lon, *sample_type = square
    parts = [parsed.latitude >= lat, parsed.latitude < lat + size,
             parsed.longitude >= lon, parsed.longitude < lon + size]
    if sample_type:
        parts.append(parsed.host_or_not_mature == sample_type[0])
    return and_(*parts)


def _hexagon_condition(parsed, hexagon: Hexagon):
    """Inside a pointy-topped hexagon: between its west edge (included) and east edge (not), and under
    the two sloping edges on each of its top and bottom. This is the binning of `hex_index`."""
    half_width = MAP_HEX_DEGREES / 2
    radius = MAP_HEX_DEGREES / SQRT_3
    east = parsed.longitude - hexagon.lon
    north = parsed.latitude - hexagon.lat
    parts = [east >= -half_width, east < half_width, func.abs(north) <= radius - func.abs(east) / SQRT_3]
    if hexagon.sample_type:
        parts.append(parsed.host_or_not_mature == hexagon.sample_type)
    return and_(*parts)


def grid_condition(parsed, squares: list[Area]):
    """SQL matching runs inside any of `squares` (from parse_grid_squares, so hexagons too); an
    area with a sample type also requires that type."""
    return or_(*(_hexagon_condition(parsed, area) if isinstance(area, Hexagon) else _square_condition(parsed, area)
                 for area in squares))


def _counted(count: int, label: str, noun: str) -> str:
    """'2 host squares', '1 hexagon'."""
    return f'{count} {label + " " if label else ""}{noun}{"s" if count != 1 else ""}'


def _describe_squares(squares: list, label: str) -> str:
    size = MAP_CELL_DEGREES
    lats = [square[0] for square in squares]
    lons = [square[1] for square in squares]
    return (f'{_counted(len(squares), label, "square")} of {size}° '
            f'(latitude {min(lats)}° to {max(lats) + size}°, longitude {min(lons)}° to {max(lons) + size}°)')


def _describe_hexagons(hexagons: list[Hexagon], label: str) -> str:
    def span(values: list[float]) -> str:
        """'0° to 1.7°', or just '52°' when every hexagon shares it."""
        low, high = (f'{round(value, 1) + 0.0:g}°' for value in (min(values), max(values)))
        return low if low == high else f'{low} to {high}'
    lats = [hexagon.lat for hexagon in hexagons]
    lons = [hexagon.lon for hexagon in hexagons]
    return (f'{_counted(len(hexagons), label, "hexagon")} of {MAP_HEX_DEGREES}° '
            f'(centred latitude {span(lats)}, longitude {span(lons)})')


def describe_grid(squares: list[Area]) -> str:
    """One kind of area reads 'grid: 2 host squares of 5° (...)'; a mix is listed per kind and
    sample type, e.g. '(grid: 1 host square of 5° (...) OR 2 ecological hexagons of 2° (...))'."""
    described = []
    for label in ('', *SAMPLE_TYPES):
        plain = [area for area in squares
                 if not isinstance(area, Hexagon) and (area[2] if len(area) == 3 else '') == label]
        hexagons = [area for area in squares if isinstance(area, Hexagon) and (area.sample_type or '') == label]
        if plain:
            described.append(_describe_squares(plain, label))
        if hexagons:
            described.append(_describe_hexagons(hexagons, label))
    if len(described) == 1:
        return f'grid: {described[0]}'
    return f'(grid: {" OR ".join(described)})'
