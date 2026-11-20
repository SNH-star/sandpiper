#!/usr/bin/env python3
"""Figures for the Statistics page that need more than the per-run summary:
the yearly trend in known species fraction, and the phylum composition of each
group of runs. Writes a small JSON so the page never loads the inputs.

Usage: summarise_groups.py [--db DATABASE.duckdb] OUTPUT.json BLACKLIST.csv SUMMARY PARSED_METADATA CHUNK_DIR CONDENSED GTDB_METADATA...

SUMMARY is the newest per_acc_summary; PARSED_METADATA and BLACKLIST decide
which of its runs the website holds (as in summarise_versions.py). CHUNK_DIR
holds the kingfisher metadata chunks, whose `published` column gives each run's
release year. CONDENSED is the condensed profile table (sample, coverage,
taxonomy), which may be gzipped. GTDB_METADATA are the bac120 and ar53 metadata
tables of the GTDB release the table was profiled against; their `ncbi_date`
gives the year each species first had a genome. The yearly trend follows the
Sandpiper paper: a run counts only the species whose first genome predates its
release year.

With --db, the website database (opened read-only) also gives each run's
host/ecological call (replacing the summary file's, so every figure agrees with
Types of sample) and, for each group, the taxa found in the most of its runs, for
the Statistics page's "Most widely detected taxa". Without it that part is left
out and the page hides its group menu.
"""
import datetime as dt
import functools
import glob
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from summarise_versions import GROUP_NAMES, group_labels, keep_website_runs  # noqa: E402

MIN_YEAR_RUNS = 10
TOP_PHYLA = 10
UNASSIGNED = 'unassigned'
OTHER = 'Other'
CALL_KEYS = {'host': 'host_associated', 'ecological': 'ecological'}
# Time from collection to release is binned by month out to this many months (15 years).
LAG_MAX_MONTHS = 180
DAYS_PER_MONTH = 30.4375
# How precisely a collection date is recorded, most precise first. Whatever the precision, a run
# is placed at the middle of what was recorded: its day, the 15th of its month, 1 July of its
# year. A range is placed at its midpoint and counts as the precision of its start.
PRECISIONS = ('day', 'month', 'year')
# Where a run is placed for a date written to each precision, from the first day of what was written.
MIDDLE_OF = {
    'day': lambda first: first,
    'month': lambda first: first.replace(day=15),
    'year': lambda first: first.replace(month=7),
}
FIRST_YEAR, LAST_YEAR = 1900, 2100
# Submitters name the collection date in more than one way, and each chunk only has the columns
# its runs use, so a run's date can be in any of these.
COLLECTION_COLUMNS = ['collection_date', 'collection date', 'collection_timestamp', 'collection_datetime']
# A year, optionally with a month, optionally with a day (and then optionally a time).
PERIOD = re.compile(r'^(\d{4})(?:-(\d{2})(?:-(\d{2})(?:[T ].*)?)?)?$')

# One pass over the condensed table. Reads the group file (sample, kind, name),
# the run years file (sample, year) and the species file (species, year of its
# first genome), then the table on stdin. Prints, per group run, its coverage by
# phylum (the third rank of the taxonomy, "Root; d__Bacteria; p__Name") beside
# its total (lines "P"), and, per run with a year, the coverage in species whose
# first genome came out before that year beside its total (lines "K").
AWK_PROGRAM = r'''
BEGIN { FS = "\t" }
FILENAME == ARGV[1] { wanted[$1] = 1; next }
FILENAME == ARGV[2] { released[$1] = $2; next }
FILENAME == ARGV[3] { first[$1] = $2; next }
FNR == 1 && $1 == "sample" { next }
{
  n = split($3, rank, "; ")
  if ($1 in wanted) {
    phylum = (n >= 3) ? rank[3] : "''' + UNASSIGNED + r'''"
    total[$1] += $2
    part[$1 SUBSEP phylum] += $2
  }
  if ($1 in released) {
    all[$1] += $2
    species = (rank[n] ~ /^s__/) ? substr(rank[n], 4) : ""
    if (species in first && first[species] < released[$1]) known[$1] += $2
  }
}
END {
  for (key in part) {
    split(key, pair, SUBSEP)
    print "P\t" pair[1] "\t" pair[2] "\t" part[key] "\t" total[pair[1]]
  }
  for (sample in all) print "K\t" sample "\t" known[sample] + 0 "\t" all[sample]
}
'''


def weighted_line(years: List[float], means: List[float], runs: List[int]) -> Tuple[float, float]:
    """Least-squares line through yearly means, each weighted by its run count.
    Returns (slope, intercept)."""
    slope, intercept = np.polyfit(years, means, 1, w=np.sqrt(runs))
    return float(slope), float(intercept)


def _trend(rows: pd.DataFrame, column: str) -> Optional[dict]:
    """Yearly means of `column` with a weighted trend line, or None when fewer
    than two years have MIN_YEAR_RUNS runs."""
    yearly = rows.groupby('year')[column].agg(['mean', 'size'])
    yearly = yearly[yearly['size'] >= MIN_YEAR_RUNS]
    if len(yearly) < 2:
        return None
    years = [int(year) for year in yearly.index]
    means = [round(float(mean), 2) for mean in yearly['mean']]
    runs = [int(size) for size in yearly['size']]
    slope, intercept = weighted_line(years, means, runs)
    return {
        'points': [{'year': y, 'mean': m, 'runs': r} for y, m, r in zip(years, means, runs)],
        'slope': round(slope, 3),
        # The line as its values at the first and last year: a rounded slope times a year near 2000 is off by a point.
        'fit': [{'year': y, 'value': round(slope * y + intercept, 2)} for y in (years[0], years[-1])],
    }


def yearly_trend(frame: pd.DataFrame, column: str = 'known_species_fraction') -> dict:
    """Mean known species fraction (percent) per release year for each host call.

    frame: columns host_or_not, year and `column` (percent).
    Years with fewer than MIN_YEAR_RUNS runs are left out.
    """
    result = {}
    for call, key in CALL_KEYS.items():
        rows = frame[(frame['host_or_not'] == call) & frame[column].notna() & frame['year'].notna()]
        result[key] = _trend(rows, column)
    return result


GUT_SUFFIXES = ('gut', 'feces')
# Hosts with enough runs for separate gut and non-gut lines. Bovine and pig are too small to split.
SPLIT_GUT_GROUPS = ('human', 'mouse')
POOLED_HOST_GROUPS = ('bovine', 'pig')


def series_of(kind: str, organism: str) -> Optional[str]:
    """The year-chart series an organism label belongs to, or None.

    Only "<host> ... metagenome" labels count (viruses and host-less labels
    such as "gut metagenome" do not). For the hosts in SPLIT_GUT_GROUPS a gut
    or feces label is "<host>_gut" and every other body site is "<host>"; for
    those in POOLED_HOST_GROUPS every such label is "<host>"; other groups
    take only their exact "<name> metagenome" label.
    """
    if not isinstance(organism, str):
        return None
    for name in GROUP_NAMES[kind]:
        if organism == f'{name} metagenome':
            return name
        if name in SPLIT_GUT_GROUPS + POOLED_HOST_GROUPS and organism.startswith(f'{name} ') and organism.endswith(' metagenome'):
            site = organism[len(name) + 1:-len(' metagenome')]
            return f'{name}_gut' if name in SPLIT_GUT_GROUPS and site in GUT_SUFFIXES else name
    return None


def series_keys(kind: str) -> List[str]:
    """Every series key of a call, gut series after their host."""
    keys = []
    for name in GROUP_NAMES[kind]:
        keys.append(name)
        if name in SPLIT_GUT_GROUPS:
            keys.append(f'{name}_gut')
    return keys


def yearly_group_trends(frame: pd.DataFrame, column: str = 'known_species_fraction') -> dict:
    """yearly_trend for each named series of each call: {kind: {series: trend or None}}."""
    result = {}
    for kind in GROUP_NAMES:
        in_kind = frame[(frame['host_or_not'] == kind) & frame[column].notna() & frame['year'].notna()]
        series = in_kind['organism'].map({label: series_of(kind, label) for label in in_kind['organism'].unique()})
        result[kind] = {key: _trend(in_kind[series == key], column) for key in series_keys(kind)}
    return result


DEPTH_PERCENTILES = (('p5', 5), ('q1', 25), ('median', 50), ('q3', 75), ('p95', 95))


def yearly_depth(frame: pd.DataFrame) -> List[dict]:
    """Sequencing depth (log10 bases) percentiles for each release year, for a boxplot.

    frame: columns year and metagenome_size (bases). Runs without a year or a
    positive size are left out, as are years with fewer than MIN_YEAR_RUNS runs.
    """
    rows = frame[frame['year'].notna() & (frame['metagenome_size'] > 0)]
    depth = np.log10(rows['metagenome_size'])
    result = []
    for year, values in depth.groupby(rows['year'].astype(int)):
        if len(values) < MIN_YEAR_RUNS:
            continue
        result.append({'year': int(year), 'runs': int(len(values)),
                       **{name: round(float(np.percentile(values, q)), 3) for name, q in DEPTH_PERCENTILES}})
    return result


def group_samples(frame: pd.DataFrame) -> Dict[str, Tuple[str, str]]:
    """sample -> (kind, group name) for runs whose organism label is one of the
    group's (see group_labels) and whose host call is the group's kind."""
    groups = {}
    for kind, names in GROUP_NAMES.items():
        in_kind = frame[frame['host_or_not'] == kind]
        for name in names:
            for sample in in_kind.loc[in_kind['organism'].isin(group_labels(name)), 'sample']:
                groups[sample] = (kind, name)
    return groups


def aggregate_composition(lines: Iterable[str], groups: Dict[str, Tuple[str, str]]) -> dict:
    """Mean relative abundance (percent) of each phylum in each group.

    lines: "sample<TAB>phylum<TAB>coverage<TAB>run total". Each run counts once,
    whatever its depth. The `p__` prefix is dropped from phylum names.
    """
    sums: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    seen: Dict[Tuple[str, str], set] = defaultdict(set)
    for line in lines:
        sample, phylum, part, total = line.rstrip('\n').split('\t')
        if sample not in groups or float(total) <= 0:
            continue
        sums[groups[sample]][phylum.removeprefix('p__')] += float(part) / float(total)
        seen[groups[sample]].add(sample)
    result = {}
    for kind, names in GROUP_NAMES.items():
        rows = []
        for name in names:
            runs = len(seen[(kind, name)])
            if not runs:
                continue
            rows.append({'name': name, 'runs': runs,
                         'phyla': {phylum: 100 * value / runs for phylum, value in sums[(kind, name)].items()}})
        result[CALL_KEYS[kind]] = fold_to_top_phyla(rows)
    return result


def fold_to_top_phyla(rows: List[dict]) -> dict:
    """Keep the phyla with the highest mean abundance across the rows and fold
    the rest (and unassigned) into Other, so every row sums to 100."""
    overall: Dict[str, float] = defaultdict(float)
    for row in rows:
        for phylum, value in row['phyla'].items():
            if phylum != UNASSIGNED:
                overall[phylum] += value / len(rows)
    top = [phylum for phylum, _ in sorted(overall.items(), key=lambda item: -item[1])[:TOP_PHYLA]]
    return {
        'phyla': top + [OTHER],
        'groups': [{
            'name': row['name'], 'runs': row['runs'],
            'percent': {**{phylum: round(row['phyla'].get(phylum, 0), 2) for phylum in top},
                        OTHER: round(100 - sum(row['phyla'].get(phylum, 0) for phylum in top), 2)},
        } for row in rows],
    }


def release_years(chunk_dir: str, samples: set) -> pd.Series:
    """Release year of each run, from the `published` column of the chunks."""
    frames = [pd.read_csv(path, sep='\t', usecols=['run', 'published'], dtype=str)
              for path in sorted(glob.glob(os.path.join(chunk_dir, '*.csv')))]
    published = pd.concat(frames)
    published = published[published['run'].isin(samples)].drop_duplicates('run').set_index('run')['published']
    return pd.to_numeric(published.str[:4], errors='coerce')


def _period_bounds(text: str) -> Optional[Tuple[dt.date, dt.date, str]]:
    """First day, last day and precision ('day', 'month' or 'year') of a date written as
    YYYY, YYYY-MM or YYYY-MM-DD (with an optional time); None if it is not one or is impossible."""
    match = PERIOD.match(text)
    if not match:
        return None
    year = int(match[1])
    month = int(match[2]) if match[2] else None
    day = int(match[3]) if match[3] else None
    if not FIRST_YEAR <= year <= LAST_YEAR:
        return None
    try:
        if day:
            date = dt.date(year, month, day)
            return date, date, 'day'
        if month:
            first = dt.date(year, month, 1)
            following = dt.date(year + (month == 12), month % 12 + 1, 1)
            return first, following - dt.timedelta(days=1), 'month'
        return dt.date(year, 1, 1), dt.date(year, 12, 31), 'year'
    except ValueError:
        return None


@functools.lru_cache(maxsize=None)
def parse_collection(text: str) -> Optional[Tuple[str, dt.date]]:
    """(precision, date a run is placed at) for a recorded collection date, or None if unusable.

    A run is placed at the middle of what was recorded: a full date is used as it is (so its day
    places the run within its month), a month alone is taken as its 15th, a year alone as 1 July,
    and a range ('2019-01-15/2019-02-07') at the midpoint between the first day of its start and the
    last day of its end, with the precision of its start (here a day; '2021-06/2024-05' is a month
    and '2016/2019' a year). Placeholders such as 'missing', ranges the wrong way round and
    impossible dates give None.
    """
    text = text.strip()
    if '/' in text:
        parts = text.split('/')
        bounds = [_period_bounds(part.strip()) for part in parts] if len(parts) == 2 else [None]
        if None in bounds or bounds[1][1] < bounds[0][0]:
            return None
        return bounds[0][2], bounds[0][0] + (bounds[1][1] - bounds[0][0]) // 2
    bounds = _period_bounds(text)
    if bounds is None:
        return None
    first, _, precision = bounds
    return precision, MIDDLE_OF[precision](first)


def _released_on(text) -> Optional[dt.date]:
    try:
        return dt.date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def collection_table(chunk_dir: str, runs: set) -> pd.DataFrame:
    """For each of `runs`, how precisely its collection date is recorded and its months to release.

    Reads the chunks' collection date columns (see COLLECTION_COLUMNS, any of which may be absent from
    a chunk) and `published`. A run with several dates takes the most precise. `precision` is None
    and `months` NaN for a run with no usable date.
    """
    required = ['run', 'published']
    wanted = set(required) | set(COLLECTION_COLUMNS)
    frames = []
    for path in sorted(glob.glob(os.path.join(chunk_dir, '*.csv'))):
        frame = pd.read_csv(path, sep='\t', usecols=lambda column: column in wanted, dtype=str)
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise ValueError('{} has no {} column'.format(path, ', '.join(missing)))
        frames.append(frame[frame['run'].isin(runs)])
    chunks = pd.concat(frames).drop_duplicates('run')
    date_columns = [chunks[column] for column in COLLECTION_COLUMNS if column in chunks.columns]
    rows = []
    for run, published, *texts in zip(chunks['run'], chunks['published'], *date_columns):
        best = None
        for text in texts:
            parsed = parse_collection(text) if isinstance(text, str) else None
            if parsed and (best is None or PRECISIONS.index(parsed[0]) < PRECISIONS.index(best[0])):
                best = parsed
        released = _released_on(published)
        months = (released - best[1]).days / DAYS_PER_MONTH if best and released else float('nan')
        rows.append((run, best[0] if best else None, months))
    return pd.DataFrame(rows, columns=['run', 'precision', 'months']).set_index('run')


def collection_summary(table: pd.DataFrame, calls: Dict[str, str], database_runs: int) -> dict:
    """The Statistics page's collection-to-release figure, from collection_table's output.

    Only runs called host-associated or ecological (the keys of CALL_KEYS in `calls`) are counted,
    and `database_runs` is how many such runs there are. `counts` holds, per call and precision,
    how many runs fall in each one-month bin (the page adds up the precisions the reader picks).
    Lags past the axis are counted in `beyond_axis` rather than piled into the last bin, and
    negative lags (collected after release) in `negative`, so for each precision the drawn, beyond
    and negative runs add up to `available`. `available` says how many called runs have each
    precision; `none` have no usable date.
    """
    call_of = table.index.map(calls)
    table = table[pd.Series(call_of, index=table.index).isin(list(CALL_KEYS)).to_numpy()]
    call_of = table.index.map(calls)
    counts = {call: {} for call in CALL_KEYS}
    beyond = {call: {} for call in CALL_KEYS}
    negative = {call: {} for call in CALL_KEYS}
    for call in CALL_KEYS:
        for precision in PRECISIONS:
            months = table.loc[(call_of == call) & (table['precision'] == precision), 'months'].dropna()
            negative[call][precision] = int((months < 0).sum())
            months = months[months >= 0]
            beyond[call][precision] = int((months > LAG_MAX_MONTHS).sum())
            counts[call][precision] = np.histogram(months[months <= LAG_MAX_MONTHS], bins=np.arange(0, LAG_MAX_MONTHS + 1))[0].tolist()
    available = {precision: int((table['precision'] == precision).sum()) for precision in PRECISIONS}
    available['none'] = database_runs - sum(available.values())
    return {'months': LAG_MAX_MONTHS, 'counts': counts, 'beyond_axis': beyond, 'negative': negative,
            'available': available, 'database_runs': int(database_runs)}


def database_calls(db_path: str) -> Dict[str, Optional[str]]:
    """run accession -> the website database's host/ecological call ('host', 'ecological' or None).

    This is the call the rest of the Statistics page counts (`host_or_not_mature`), so figures that
    use it agree with Types of sample. Reads the database read-only.
    """
    import duckdb
    connection = duckdb.connect(db_path, read_only=True)
    try:
        return dict(connection.execute(
            'SELECT n.acc, p.host_or_not_mature FROM ncbi_metadata n '
            'JOIN parsed_sample_attributes p ON p.run_id = n.id').fetchall())
    finally:
        connection.close()


def with_database_calls(frame: pd.DataFrame, calls: Dict[str, Optional[str]]) -> pd.DataFrame:
    """A copy of the per-run frame whose host_or_not is the database's call; runs it does not hold are uncalled."""
    result = frame.copy()
    result['host_or_not'] = result['sample'].map(calls)
    return result


TAXA_LEVELS = ('phylum', 'genus', 'species')
TOP_TAXA_COUNT = 10


def group_top_taxa(rows: Iterable[Tuple[str, str, str, int]], count: int = TOP_TAXA_COUNT) -> dict:
    """The `count` taxa found in the most runs of one group, per taxonomy database and level.

    rows: (taxonomy type, level, name, runs) for every taxon detected in the group's runs.
    Returns type -> level -> [{name, runs}], most runs first, ties by name.
    """
    found: Dict[str, Dict[str, List[dict]]] = {}
    for taxonomy_type, level, name, runs in rows:
        found.setdefault(taxonomy_type, {}).setdefault(level, []).append({'name': name, 'runs': int(runs)})
    return {
        taxonomy_type: {
            level: sorted(taxa, key=lambda row: (-row['runs'], row['name']))[:count]
            for level, taxa in levels.items()}
        for taxonomy_type, levels in found.items()}


def top_taxa_by_group(db_path: str) -> dict:
    """Per group (see GROUP_NAMES): its side, how many runs it has and its most widely detected taxa.

    A run is in a group when its organism label is one of group_labels(name) and the database's
    host/ecological call is the group's side, exactly as the other Statistics charts group runs.
    Reads the website database read-only; omits groups with no runs.
    """
    import duckdb
    connection = duckdb.connect(db_path, read_only=True)
    try:
        result = {}
        for call, names in GROUP_NAMES.items():
            for name in names:
                labels = list(group_labels(name))
                marks = ', '.join('?' for _ in labels)
                members = ('SELECT n.id FROM ncbi_metadata n JOIN parsed_sample_attributes p ON p.run_id = n.id '
                           f'WHERE n.taxon_name IN ({marks}) AND p.host_or_not_mature = ?')
                runs = connection.execute(f'SELECT count(*) FROM ({members})', [*labels, call]).fetchone()[0]
                if not runs:
                    continue
                rows = connection.execute(
                    'SELECT t.taxonomy_type, t.taxonomy_level, t.name, count(DISTINCT c.run_id) '
                    'FROM condensed_profiles c JOIN taxonomies t ON t.id = c.taxonomy_id '
                    f'WHERE c.run_id IN ({members}) AND t.taxonomy_level IN ({", ".join("?" for _ in TAXA_LEVELS)}) '
                    'GROUP BY t.taxonomy_type, t.taxonomy_level, t.name',
                    [*labels, call, *TAXA_LEVELS]).fetchall()
                result[name] = {'call': call, 'runs': int(runs), 'taxa': group_top_taxa(rows)}
        return result
    finally:
        connection.close()


SIDE_COUNT_COLUMNS = {'host': 'host_sample_count', 'ecological': 'ecological_sample_count'}


def taxa_group_breakdown(db_path: str) -> dict:
    """For each side (host, ecological), its most widely detected taxa split by group, for stacked bars.

    The taxa are the ten with the most runs of that side per taxonomy database and level, as the
    page's all-sides view ranks them (the run counts the database stores on each taxon). Each row is
    {name, runs (all runs of the side), groups: {group: runs}}; runs of the side in no named group are
    the difference. Groups use the same labels as top_taxa_by_group. Reads the database read-only.
    """
    import duckdb
    connection = duckdb.connect(db_path, read_only=True)
    try:
        result: Dict[str, dict] = {}
        ranked: Dict[str, Dict[int, Tuple[str, str, str, int]]] = {}
        for side, column in SIDE_COUNT_COLUMNS.items():
            ranked[side] = {}
            for (taxonomy_type,) in connection.execute('SELECT DISTINCT taxonomy_type FROM taxonomies').fetchall():
                for level in TAXA_LEVELS:
                    for taxon_id, name, runs in connection.execute(
                            f'SELECT id, name, {column} FROM taxonomies WHERE taxonomy_type = ? AND taxonomy_level = ? '
                            f'AND coalesce({column}, 0) > 0 ORDER BY {column} DESC, name LIMIT {TOP_TAXA_COUNT}',
                            [taxonomy_type, level]).fetchall():
                        ranked[side][taxon_id] = (taxonomy_type, level, name, int(runs))
        in_groups: Dict[str, Dict[int, Dict[str, int]]] = {side: {} for side in SIDE_COUNT_COLUMNS}
        for side, names in GROUP_NAMES.items():
            ids = list(ranked[side])
            if not ids:
                continue
            for name in names:
                labels = list(group_labels(name))
                members = ('SELECT n.id FROM ncbi_metadata n JOIN parsed_sample_attributes p ON p.run_id = n.id '
                           f'WHERE n.taxon_name IN ({", ".join("?" for _ in labels)}) AND p.host_or_not_mature = ?')
                counts = connection.execute(
                    'SELECT c.taxonomy_id, count(DISTINCT c.run_id) FROM condensed_profiles c '
                    f'WHERE c.taxonomy_id IN ({", ".join("?" for _ in ids)}) AND c.run_id IN ({members}) '
                    'GROUP BY c.taxonomy_id', [*ids, *labels, side]).fetchall()
                for taxon_id, runs in counts:
                    in_groups[side].setdefault(taxon_id, {})[name] = int(runs)
        for side, taxa in ranked.items():
            result[side] = {}
            for taxon_id, (taxonomy_type, level, name, runs) in sorted(taxa.items(), key=lambda item: (-item[1][3], item[1][2])):
                result[side].setdefault(taxonomy_type, {}).setdefault(level, []).append(
                    {'name': name, 'runs': runs, 'groups': in_groups[side].get(taxon_id, {})})
        return result
    finally:
        connection.close()


# Organism label -> IndicPiper habitat, from Table S4 of the IndicPiper paper (the exact strings its habitat search
# uses). Next release: read IndicPiper's own mapping instead.
HABITAT_MAP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'vue', 'src', 'constants',
                                'indicpiperHabitats.json')


def indicpiper_label_habitats(path: str = HABITAT_MAP_PATH) -> Dict[str, str]:
    """Canonical organism label -> IndicPiper habitat; the same file the website uses for its habitat check."""
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def canonical_organism(label: str) -> str:
    """An organism label as the website compares it: lower case, spaces for underscores, trimmed after 'metagenome'."""
    text = re.sub(r'\s+', ' ', label.lower().replace('_', ' ')).strip()
    return re.sub(r'(metagenome).*$', r'\1', text)


def _mean(total: float, runs: int) -> Optional[float]:
    return float(total) / runs if runs else None


def indicpiper_by_habitat(db_path: str, label_habitats: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Optional[float]]]:
    """Per IndicPiper habitat: how many runs are recorded as it and the average indicator abundance (a fraction
    of the sample) and number of indicator genera per run.

    A run belongs to the habitat its organism label maps to (indicpiper_label_habitats). The database only
    stores (run, habitat) pairs with a match, so `mean_*` divide by every run of the group and `*_matched`
    by the runs that matched. A habitat nobody is recorded as is listed with 0 runs and no means.
    Reads the website database read-only.
    """
    import duckdb
    if label_habitats is None:
        label_habitats = indicpiper_label_habitats()
    connection = duckdb.connect(db_path, read_only=True)
    try:
        labels_of: Dict[str, List[str]] = defaultdict(list)
        for (label,) in connection.execute('SELECT DISTINCT taxon_name FROM ncbi_metadata WHERE taxon_name IS NOT NULL').fetchall():
            habitat = label_habitats.get(canonical_organism(label))
            if habitat:
                labels_of[habitat].append(label)
        habitats = sorted(set(label_habitats.values())
                          | {h for (h,) in connection.execute('SELECT DISTINCT habitat FROM indicator_habitat_scores').fetchall()})
        result = {}
        for habitat in habitats:
            labels = labels_of.get(habitat, [])
            entry = {'runs': 0, 'matched_runs': 0, 'mean_abundance': None, 'mean_genera': None,
                     'mean_abundance_matched': None, 'mean_genera_matched': None}
            if labels:
                members = f'SELECT id FROM ncbi_metadata WHERE taxon_name IN ({", ".join("?" for _ in labels)})'
                runs = connection.execute(f'SELECT count(DISTINCT id) FROM ({members})', labels).fetchone()[0]
                matched, total = connection.execute(
                    f'SELECT count(*), coalesce(sum(score), 0) FROM indicator_habitat_scores WHERE habitat = ? AND run_id IN ({members})',
                    [habitat, *labels]).fetchone()
                genera = connection.execute(
                    f'SELECT count(*) FROM indicator_habitat_genus_scores WHERE habitat = ? AND run_id IN ({members})',
                    [habitat, *labels]).fetchone()[0]
                entry = {'runs': int(runs), 'matched_runs': int(matched),
                         'mean_abundance': _mean(total, runs), 'mean_genera': _mean(genera, runs),
                         'mean_abundance_matched': _mean(total, matched), 'mean_genera_matched': _mean(genera, matched)}
            result[habitat] = entry
        return result
    finally:
        connection.close()


def species_first_years(metadata_paths: List[str]) -> Dict[str, int]:
    """Year of the earliest genome (by NCBI date) of each GTDB species."""
    frames = [pd.read_csv(path, sep='\t', usecols=['gtdb_taxonomy', 'ncbi_date'], dtype=str)
              for path in metadata_paths]
    genomes = pd.concat(frames)
    genomes['species'] = genomes['gtdb_taxonomy'].str.rsplit(';', n=1).str[-1].str.removeprefix('s__')
    genomes['year'] = pd.to_datetime(genomes['ncbi_date'], errors='coerce').dt.year
    return {name: int(year) for name, year in genomes.groupby('species')['year'].min().dropna().items()}


def write_table(path: str, rows: Iterable[Iterable]) -> None:
    with open(path, 'w') as handle:
        for row in rows:
            handle.write('\t'.join(str(value) for value in row) + '\n')


def stream_condensed(condensed_path: str, groups: Dict[str, Tuple[str, str]], years: Dict[str, int],
                     first_years: Dict[str, int], work_dir: str) -> Tuple[dict, Dict[str, float]]:
    """Phylum composition of the group runs, and for each run in `years` the
    percent of its coverage in species with a genome released before its year."""
    inputs = [os.path.join(work_dir, name) for name in ('group_samples.tsv', 'run_years.tsv', 'species_first_year.tsv')]
    write_table(inputs[0], ((sample, kind, name) for sample, (kind, name) in groups.items()))
    write_table(inputs[1], years.items())
    write_table(inputs[2], first_years.items())
    try:
        reader = 'zcat' if condensed_path.endswith('.gz') else 'cat'
        pipeline = subprocess.Popen([reader, condensed_path], stdout=subprocess.PIPE)
        awk = subprocess.Popen(['awk', AWK_PROGRAM, *inputs, '-'], stdin=pipeline.stdout,
                               stdout=subprocess.PIPE, text=True)
        pipeline.stdout.close()
        phylum_lines, known = [], {}
        for line in awk.stdout:
            kind, rest = line.rstrip('\n').split('\t', 1)
            if kind == 'P':
                phylum_lines.append(rest)
            else:
                sample, part, total = rest.split('\t')
                if float(total) > 0:
                    known[sample] = 100 * float(part) / float(total)
        if awk.wait() != 0 or pipeline.wait() != 0:
            sys.exit('reading the condensed table failed')
    finally:
        for path in inputs:
            if os.path.exists(path):
                os.remove(path)
    return aggregate_composition(phylum_lines, groups), known


def pop_option(argv: list, name: str) -> Tuple[Optional[str], list]:
    """The value after option `name` in argv (None if absent), and argv without the pair."""
    if name not in argv:
        return None, argv
    at = argv.index(name)
    if at + 1 >= len(argv):
        sys.exit('{} needs a value'.format(name))
    return argv[at + 1], argv[:at] + argv[at + 2:]


def main(argv: list) -> None:
    db_path, argv = pop_option(argv, '--db')
    if len(argv) < 8:
        sys.exit(__doc__)
    out_path, blacklist_path, summary_path, metadata_path, chunk_dir, condensed_path = argv[1:7]
    gtdb_metadata = argv[7:]
    with open(blacklist_path) as handle:
        blacklist = {line.strip() for line in handle if line.strip()}
    frame = pd.read_csv(summary_path, low_memory=False)
    metadata_runs = set(pd.read_csv(metadata_path, sep='\t', usecols=['run'], dtype=str)['run'])
    kept = keep_website_runs(frame, blacklist, metadata_runs).copy()
    if db_path:
        before = int(kept['host_or_not'].isin(CALL_KEYS).sum())
        kept = with_database_calls(kept, database_calls(db_path))
        print('host/ecological call taken from the database:', int(kept['host_or_not'].isin(CALL_KEYS).sum()),
              'called runs (the summary file had', before, ')', file=sys.stderr)
    kept['year'] = kept['sample'].map(release_years(chunk_dir, set(kept['sample'])))
    print('runs', len(kept), 'with a release year', int(kept['year'].notna().sum()), file=sys.stderr)
    groups = group_samples(kept)
    print('group runs', len(groups), file=sys.stderr)
    work_dir = os.path.dirname(os.path.abspath(out_path))
    dated = kept[kept['host_or_not'].isin(CALL_KEYS) & kept['year'].notna()]
    years = dict(zip(dated['sample'], dated['year'].astype(int)))
    first_years = species_first_years(gtdb_metadata)
    print('species with a dated genome', len(first_years), file=sys.stderr)
    composition, known = stream_condensed(condensed_path, groups, years, first_years, work_dir)
    kept['contemporaneous_known'] = kept['sample'].map(known)
    table = collection_table(chunk_dir, set(kept['sample']))
    called = kept[kept['host_or_not'].isin(CALL_KEYS)]
    collection = collection_summary(table, dict(zip(called['sample'], called['host_or_not'])), len(called))
    print('runs by collection date precision', collection['available'], file=sys.stderr)
    result = {'yearly_known': yearly_trend(kept, 'contemporaneous_known'),
              'yearly_known_groups': yearly_group_trends(kept, 'contemporaneous_known'), 'composition': composition,
              'yearly_depth': yearly_depth(kept), 'collection_to_release': collection}
    if db_path:
        result['top_taxa_by_group'] = top_taxa_by_group(db_path)
        result['taxa_group_breakdown'] = taxa_group_breakdown(db_path)
        result['indicpiper_by_habitat'] = indicpiper_by_habitat(db_path)
        print('groups with most-detected taxa', sorted(result['top_taxa_by_group']), file=sys.stderr)
    else:
        print('no --db given: the most widely detected taxa by group are left out', file=sys.stderr)
    with open(out_path, 'w') as out:
        json.dump(result, out, separators=(',', ':'))


if __name__ == '__main__':
    main(sys.argv)
