"""
Join SPIRE metalog extended metadata onto sandpiper kingfisher_metadata.tsv
via biosample ID (spire_sample_name -> biosample).

Join is strict per-biosample only — no study/bioproject inference.
Validated 2026-06-11: join is clean, coverage is ~75% of metalog biosamples.
"""

import argparse
import gzip
import os
import sys
import yaml
from collections import defaultdict


def load_config(config_path):
    with open(config_path) as f:
        return yaml.safe_load(f)


# Same field, different capitalisation across source studies. Coalesce the
# secondary spelling into the canonical one (verified disjoint, never co-populated).
# DuckDB column names are case-insensitive, so these cannot co-exist as separate columns.
COALESCE = {
    'Comorbidities': 'comorbidities',
    'pH_range': 'ph_range',
}


def load_metalog(paths):
    """Load all four metalog files into a single dict keyed by spire_sample_name."""
    print("Loading metalog files...", flush=True)
    metalog = {}  # biosample -> {col: val}
    metalog_cols = set()

    for label, path in paths.items():
        count = 0
        # rstrip('\r\n'): the animal file is CRLF, which otherwise leaves a stray
        # '\r' on the last column (time_period) and splits it into a phantom header.
        with gzip.open(path, 'rt') as f:
            hdr = f.readline().rstrip('\r\n').split('\t')
            i_spire = hdr.index('spire_sample_name')
            metalog_cols.update(hdr)
            for line in f:
                fields = line.rstrip('\r\n').split('\t')
                row = dict(zip(hdr, fields))
                bs = row.get('spire_sample_name', '').strip()
                if bs and bs not in metalog:
                    metalog[bs] = row
                    count += 1
        print(f"  {label}: {count} samples", flush=True)

    print(f"Total metalog biosamples: {len(metalog)}", flush=True)
    return metalog, sorted(metalog_cols)


def join_and_write(kingfisher_path, metalog, metalog_cols, output_path, slim_path):
    """Stream kingfisher once, writing two outputs:

    - output_path: full kingfisher columns + all meta_ columns (every run).
    - slim_path:   run + meta_ columns, matched runs only. This is the lean
                   artifact the sandpiper pipeline consumes (keyed by run).

    Meta column names are lowercased so they map cleanly to case-insensitive
    DuckDB columns.
    """
    print(f"\nStreaming {kingfisher_path}...", flush=True)

    matched = 0
    unmatched = 0

    # Canonical output columns: drop the join key and any coalesced secondary spellings.
    secondary = set(COALESCE)
    canonical_cols = [c for c in metalog_cols
                      if c != 'spire_sample_name' and c not in secondary]

    # For each canonical column, the source columns to draw a value from (first non-empty wins).
    sources = {c: [c] for c in canonical_cols}
    for sec, canon in COALESCE.items():
        if canon in sources:
            sources[canon].append(sec)

    # Prefix + lowercase metalog columns (DuckDB column names are case-insensitive).
    meta_prefix = 'meta_'
    prefixed_cols = [f"{meta_prefix}{c}".lower() for c in canonical_cols]

    def coalesce_val(meta_row, srcs):
        for s in srcs:
            v = meta_row.get(s, '')
            if v:
                return v
        return ''

    with open(kingfisher_path) as fin, \
            open(output_path, 'w') as fout, \
            open(slim_path, 'w') as fslim:
        kf_hdr = fin.readline().rstrip('\r\n').split('\t')
        i_bs = kf_hdr.index('biosample')
        i_run = kf_hdr.index('run')

        # Full output header: all kingfisher cols + prefixed metalog cols
        fout.write('\t'.join(kf_hdr + prefixed_cols) + '\n')
        # Slim output header: run + prefixed metalog cols
        fslim.write('\t'.join(['run'] + prefixed_cols) + '\n')

        empty_meta = [''] * len(prefixed_cols)

        for i, line in enumerate(fin):
            if i % 100000 == 0:
                print(f"  {i:,} rows processed, {matched:,} matched...", flush=True)

            fields = line.rstrip('\r\n').split('\t')
            bs = fields[i_bs].strip() if i_bs < len(fields) else ''

            if bs and bs in metalog:
                meta_row = metalog[bs]
                meta_vals = [coalesce_val(meta_row, sources[c]) for c in canonical_cols]
                matched += 1
                run = fields[i_run] if i_run < len(fields) else ''
                fslim.write('\t'.join([run] + meta_vals) + '\n')
            else:
                meta_vals = empty_meta
                unmatched += 1

            fout.write('\t'.join(fields + meta_vals) + '\n')

    total = matched + unmatched
    print(f"\nDone.")
    print(f"  Matched:   {matched:,} / {total:,} runs ({100*matched/total:.1f}%)")
    print(f"  Unmatched: {unmatched:,} / {total:,} runs ({100*unmatched/total:.1f}%)")
    print(f"  Full output: {output_path}")
    print(f"  Slim output: {slim_path} ({matched:,} matched runs)")


def main():
    parser = argparse.ArgumentParser(description="Join metalog metadata onto sandpiper kingfisher_metadata")
    parser.add_argument('--config', default='config.yml', help='Path to config.yml')
    # Per-build overrides (mirrors indicpiper_custom/scripts/build_indicpiper_inputs.py) so the
    # Snakefile can point this at the current build's own paths without editing config.yml.
    parser.add_argument('--kingfisher-metadata', help='overrides KINGFISHER_METADATA')
    parser.add_argument('--output-dir', help='overrides OUTPUT_DIR')
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.kingfisher_metadata:
        cfg['KINGFISHER_METADATA'] = args.kingfisher_metadata
    if args.output_dir:
        cfg['OUTPUT_DIR'] = args.output_dir

    metalog_paths = {
        'animal':        cfg['METALOG_ANIMAL'],
        'environmental': cfg['METALOG_ENVIRONMENTAL'],
        'human':         cfg['METALOG_HUMAN'],
        'ocean':         cfg['METALOG_OCEAN'],
    }

    output_path = os.path.join(cfg['OUTPUT_DIR'], cfg['OUTPUT_FILE'])
    slim_path = os.path.join(cfg['OUTPUT_DIR'], cfg['SLIM_OUTPUT_FILE'])
    os.makedirs(cfg['OUTPUT_DIR'], exist_ok=True)

    metalog, metalog_cols = load_metalog(metalog_paths)
    join_and_write(cfg['KINGFISHER_METADATA'], metalog, metalog_cols, output_path, slim_path)


if __name__ == '__main__':
    main()
