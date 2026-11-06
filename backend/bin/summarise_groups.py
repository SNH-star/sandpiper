#!/usr/bin/env python3
"""Figures for the Statistics page that need more than the per-run summary:
the yearly trend in known species fraction, and the phylum composition of each
group of runs. Writes a small JSON so the page never loads the inputs.

Usage: summarise_groups.py OUTPUT.json BLACKLIST.csv SUMMARY PARSED_METADATA CHUNK_DIR CONDENSED GTDB_METADATA...

SUMMARY is the newest per_acc_summary; PARSED_METADATA and BLACKLIST decide
which of its runs the website holds (as in summarise_versions.py). CHUNK_DIR
holds the kingfisher metadata chunks, whose `published` column gives each run's
release year. CONDENSED is the condensed profile table (sample, coverage,
taxonomy), which may be gzipped. GTDB_METADATA are the bac120 and ar53 metadata
tables of the GTDB release the table was profiled against; their `ncbi_date`
gives the year each species first had a genome. The yearly trend follows the
Sandpiper paper: a run counts only the species whose first genome predates its
release year.
"""
import glob
import json
import os
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


def yearly_trend(frame: pd.DataFrame, column: str = 'known_species_fraction') -> dict:
    """Mean known species fraction (percent) per release year for each host call.

    frame: columns host_or_not, year and `column` (percent).
    Years with fewer than MIN_YEAR_RUNS runs are left out.
    """
    result = {}
    for call, key in CALL_KEYS.items():
        rows = frame[(frame['host_or_not'] == call) & frame[column].notna() & frame['year'].notna()]
        yearly = rows.groupby('year')[column].agg(['mean', 'size'])
        yearly = yearly[yearly['size'] >= MIN_YEAR_RUNS]
        if len(yearly) < 2:
            result[key] = None
            continue
        years = [int(year) for year in yearly.index]
        means = [round(float(mean), 2) for mean in yearly['mean']]
        runs = [int(size) for size in yearly['size']]
        slope, intercept = weighted_line(years, means, runs)
        result[key] = {
            'points': [{'year': y, 'mean': m, 'runs': r} for y, m, r in zip(years, means, runs)],
            'slope': round(slope, 3),
            # The line as its values at the first and last year: a rounded slope times a year near 2000 is off by a point.
            'fit': [{'year': y, 'value': round(slope * y + intercept, 2)} for y in (years[0], years[-1])],
        }
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


def main(argv: list) -> None:
    if len(argv) < 8:
        sys.exit(__doc__)
    out_path, blacklist_path, summary_path, metadata_path, chunk_dir, condensed_path = argv[1:7]
    gtdb_metadata = argv[7:]
    with open(blacklist_path) as handle:
        blacklist = {line.strip() for line in handle if line.strip()}
    frame = pd.read_csv(summary_path, low_memory=False)
    metadata_runs = set(pd.read_csv(metadata_path, sep='\t', usecols=['run'], dtype=str)['run'])
    kept = keep_website_runs(frame, blacklist, metadata_runs).copy()
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
    result = {'yearly_known': yearly_trend(kept, 'contemporaneous_known'), 'composition': composition,
              'yearly_depth': yearly_depth(kept)}
    with open(out_path, 'w') as out:
        json.dump(result, out, separators=(',', ':'))


if __name__ == '__main__':
    main(sys.argv)
