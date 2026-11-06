#!/usr/bin/env python3
"""Summarise each version's per_acc_summary file for the Statistics page's
version comparison. Writes a small JSON of histograms so the page never loads
the summaries themselves.

Usage: summarise_versions.py OUTPUT.json BLACKLIST.csv [--reuse PREVIOUS.json] LABEL:GTDB:SUMMARY:METADATA [...]
List the newest version first. With --reuse, an earlier version already in
PREVIOUS.json (same label and GTDB release) is copied across instead of being
read again, provided PREVIOUS.json was made with this same blacklist; the
newest version (the first one listed) is always recomputed. SUMMARY may be gzipped. A summary lists every run
that was scanned, so only runs that are not on the blacklist and are in
METADATA (a parsed_metadata.tsv[.gz] with a `run` column) are kept: the website
database loads no others.
"""
import hashlib
import json
import sys
from typing import Optional

import numpy as np
import pandas as pd

KNOWN_BIN_PERCENT = 1
GENOME_SIZE_BIN_MB = 0.25
GENOME_SIZE_MAX_MB = 8
DEPTH_LOG10_MIN = 8
DEPTH_LOG10_MAX = 11.5
DEPTH_LOG10_STEP = 0.25
# Older summaries name this column with spaces.
RENAMED_COLUMNS = {'singlem prokaryotic fraction (SPF)': 'singlem_prokaryotic_fraction'}
CALLS = ('host', 'ecological')
# Groups for the per-group figures: the organism label must be exactly
# "<name> metagenome" (also "<name> gut metagenome" for the animal hosts in
# GUT_GROUPS), and the run's host call must be the group's call.
GROUP_NAMES = {
    'host': ('plant', 'bovine', 'pig', 'human', 'mouse'),
    'ecological': ('soil', 'sediment', 'marine', 'freshwater', 'aquatic'),
}
GUT_GROUPS = ('bovine', 'human', 'mouse', 'pig')
GROUP_KEYS = {'host': 'host_groups', 'ecological': 'ecological_groups'}
SPF_GROUP_KEYS = {'host': 'spf_host_groups', 'ecological': 'spf_ecological_groups'}
SPF_COLUMN = 'singlem_prokaryotic_fraction'


def group_labels(name: str) -> tuple:
    """The organism labels that put a run in the named group."""
    if name in GUT_GROUPS:
        return (f'{name} metagenome', f'{name} gut metagenome')
    return (f'{name} metagenome',)


def histogram(values: pd.Series, edges: np.ndarray) -> Optional[dict]:
    """Share of runs (percent) in each bin; the last bin takes anything above
    it. None when the column is absent or empty."""
    values = values.dropna()
    if values.empty:
        return None
    counts, _ = np.histogram(np.clip(values, edges[0], edges[-1]), bins=edges)
    return {
        'start': [round(float(edge), 3) for edge in edges[:-1]],
        'percent': [round(100 * float(count) / len(values), 2) for count in counts],
        'median': round(float(values.median()), 2),
        'runs': int(len(values)),
    }


def group_histograms(frame: pd.DataFrame, call: str, column: str = 'known_species_fraction') -> dict:
    """Histograms of a percent column (known species fraction by default) for
    each named group of runs with this host call; a group with no runs (or no
    column) is None."""
    if not {'organism', 'host_or_not', column} <= set(frame.columns):
        return {name: None for name in GROUP_NAMES[call]}
    edges = np.arange(0, 100 + KNOWN_BIN_PERCENT, KNOWN_BIN_PERCENT)
    in_call = frame[frame['host_or_not'] == call]
    return {name: histogram(in_call.loc[in_call['organism'].isin(group_labels(name)), column], edges)
            for name in GROUP_NAMES[call]}


def keep_website_runs(frame: pd.DataFrame, blacklist: set, metadata_runs: set) -> pd.DataFrame:
    """The summary's runs that the website database also holds."""
    return frame[~frame['sample'].isin(blacklist) & frame['sample'].isin(metadata_runs)]


def with_known_fraction(frame: pd.DataFrame) -> pd.DataFrame:
    """Give summaries that predate `known_species_fraction` (1.1.9) that column.
    They stored it as a 0-1 share in `species_coverage`; from 1.1.10 on that
    column holds coverage (values above 1), so only a column that never
    exceeds 1 is converted."""
    if 'known_species_fraction' in frame or 'species_coverage' not in frame:
        return frame
    share = frame['species_coverage']
    if share.dropna().empty or share.max() > 1:
        return frame
    return frame.assign(known_species_fraction=(100 * share).round(2))


def summarise(frame: pd.DataFrame, summary_rows: Optional[int] = None) -> dict:
    frame = with_known_fraction(frame.rename(columns=RENAMED_COLUMNS))
    column = lambda name: frame[name] if name in frame else pd.Series(dtype=float)  # noqa: E731
    # As on the website, a run with no recorded call takes the predictor's.
    calls = column('host_or_not').fillna(column('prediction')) if 'prediction' in frame else column('host_or_not')
    return {
        'runs': int(len(frame)),
        'summary_rows': int(summary_rows if summary_rows is not None else len(frame)),
        'host_associated': int((calls == 'host').sum()),
        'ecological': int((calls == 'ecological').sum()),
        'unclassified': int((~calls.isin(CALLS)).sum()) if len(calls) else int(len(frame)),
        'known_species_fraction': histogram(
            column('known_species_fraction'), np.arange(0, 100 + KNOWN_BIN_PERCENT, KNOWN_BIN_PERCENT)),
        'genome_size_mb': histogram(
            column('average_bacterial_archaeal_genome_size') / 1e6,
            np.arange(0, GENOME_SIZE_MAX_MB + GENOME_SIZE_BIN_MB, GENOME_SIZE_BIN_MB)),
        **{GROUP_KEYS[call]: group_histograms(frame, call) for call in CALLS},
        **{SPF_GROUP_KEYS[call]: group_histograms(frame, call, SPF_COLUMN) for call in CALLS},
        'depth_log10_bases': histogram(
            np.log10(column('metagenome_size')),
            np.arange(DEPTH_LOG10_MIN, DEPTH_LOG10_MAX + DEPTH_LOG10_STEP, DEPTH_LOG10_STEP)),
    }


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def reusable_versions(previous: dict, blacklist_sha: str, skip_label: str) -> dict:
    """Earlier summaries safe to copy: {(label, gtdb): summary}. Empty unless
    `previous` was made with the same blacklist (kept runs depend on it), and
    never includes `skip_label`, the build being made now."""
    if previous.get('blacklist_sha256') != blacklist_sha:
        return {}
    return {(version['label'], version['gtdb']): version
            for version in previous.get('versions', []) if version['label'] != skip_label}


def split_reuse_option(args: list) -> tuple:
    """(path or None, remaining args) for an optional `--reuse PATH`."""
    if '--reuse' not in args:
        return None, args
    at = args.index('--reuse')
    if at + 1 >= len(args):
        sys.exit('--reuse needs a path')
    return args[at + 1], args[:at] + args[at + 2:]


def load_previous(path: Optional[str]) -> dict:
    if not path:
        return {}
    try:
        with open(path) as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}


def summarise_version(spec: str, blacklist: set) -> dict:
    label, gtdb, summary_path, metadata_path = spec.split(':', 3)
    frame = pd.read_csv(summary_path, low_memory=False)
    metadata_runs = set(pd.read_csv(metadata_path, sep='\t', usecols=['run'], dtype=str)['run'])
    kept = keep_website_runs(frame, blacklist, metadata_runs)
    print(label, len(frame), '->', len(kept), 'runs', file=sys.stderr)
    return {'label': label, 'gtdb': gtdb, **summarise(kept, len(frame))}


def main(argv: list) -> None:
    reuse_path, argv = split_reuse_option(list(argv))
    if len(argv) < 4:
        sys.exit(__doc__)
    with open(argv[2]) as handle:
        blacklist = {line.strip() for line in handle if line.strip()}
    blacklist_sha = file_sha256(argv[2])
    specs = argv[3:]
    reused = reusable_versions(load_previous(reuse_path), blacklist_sha, skip_label=specs[0].split(':', 1)[0])
    versions = []
    for spec in specs:
        label, gtdb = spec.split(':', 2)[:2]
        if (label, gtdb) in reused:
            print(label, 'reused from', reuse_path, file=sys.stderr)
            versions.append(reused[(label, gtdb)])
        else:
            versions.append(summarise_version(spec, blacklist))
    with open(argv[1], 'w') as out:
        json.dump({'blacklist_sha256': blacklist_sha, 'versions': versions}, out, separators=(',', ':'))


if __name__ == '__main__':
    main(sys.argv)
