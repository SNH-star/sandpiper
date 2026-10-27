"""
Join SPIRE metalog extended metadata onto sandpiper kingfisher metadata
via biosample ID (spire_sample_name -> biosample).

Join is strict per-biosample only — no study/bioproject inference.
Validated 2026-06-11: join is clean, coverage is ~75% of metalog biosamples.

The kingfisher metadata can be given as one TSV (--kingfisher-metadata) or as a
list of TSV files (--kingfisher-metadata-list), e.g. the per-chunk files the
Snakefile pulls fresh each build. Each chunk has its own column set, so the
`run` and `biosample` columns are looked up per file.
"""

import argparse
import gzip
import os
import sys
from typing import Dict, List, Optional, Tuple

import metalog_config


# Same field, different capitalisation across source studies. Coalesce the
# secondary spelling into the canonical one (verified disjoint, never co-populated).
# DuckDB column names are case-insensitive, so these cannot co-exist as separate columns.
COALESCE = {
    'Comorbidities': 'comorbidities',
    'pH_range': 'ph_range',
}


def read_file_list(list_path: str) -> List[str]:
    """Paths in a one-path-per-line file; blank lines are ignored."""
    with open(list_path) as f:
        paths = [line.strip() for line in f if line.strip()]
    if not paths:
        raise SystemExit("No kingfisher metadata files listed in {}".format(list_path))
    return paths


def load_metalog(paths: Dict[str, str]) -> Tuple[dict, List[str]]:
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


def join_and_write(kingfisher_paths: List[str], metalog: dict, metalog_cols: List[str],
                   output_path: Optional[str], slim_path: str) -> None:
    """Stream each kingfisher file once, writing up to two outputs:

    - output_path: full kingfisher columns + all meta_ columns (every run). Only
                   written when not None, and only possible when every input file
                   has the same header.
    - slim_path:   run + meta_ columns, matched runs only. This is the lean
                   artifact the sandpiper pipeline consumes (keyed by run).

    Meta column names are lowercased so they map cleanly to case-insensitive
    DuckDB columns.
    """
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

    def coalesce_val(meta_row: dict, srcs: List[str]) -> str:
        for s in srcs:
            v = meta_row.get(s, '')
            if v:
                return v
        return ''

    empty_meta = [''] * len(prefixed_cols)
    first_header = None
    rows_seen = 0

    fout = open(output_path, 'w') if output_path else None
    try:
        with open(slim_path, 'w') as fslim:
            # Slim output header: run + prefixed metalog cols
            fslim.write('\t'.join(['run'] + prefixed_cols) + '\n')

            for kingfisher_path in kingfisher_paths:
                print(f"\nStreaming {kingfisher_path}...", flush=True)
                with open(kingfisher_path) as fin:
                    kf_hdr = fin.readline().rstrip('\r\n').split('\t')
                    i_bs = kf_hdr.index('biosample')
                    i_run = kf_hdr.index('run')

                    if fout is not None:
                        if first_header is None:
                            first_header = kf_hdr
                            # Full output header: all kingfisher cols + prefixed metalog cols
                            fout.write('\t'.join(kf_hdr + prefixed_cols) + '\n')
                        elif kf_hdr != first_header:
                            raise SystemExit(
                                "Cannot write the full output: the headers differ between {} and {}. "
                                "Use --slim-only when joining several kingfisher files.".format(
                                    kingfisher_paths[0], kingfisher_path))

                    for line in fin:
                        if rows_seen % 100000 == 0:
                            print(f"  {rows_seen:,} rows processed, {matched:,} matched...", flush=True)
                        rows_seen += 1

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

                        if fout is not None:
                            fout.write('\t'.join(fields + meta_vals) + '\n')
    finally:
        if fout is not None:
            fout.close()

    total = matched + unmatched
    print(f"\nDone.")
    if total:
        print(f"  Matched:   {matched:,} / {total:,} runs ({100*matched/total:.1f}%)")
        print(f"  Unmatched: {unmatched:,} / {total:,} runs ({100*unmatched/total:.1f}%)")
    else:
        print("  No kingfisher rows were read.")
    if output_path:
        print(f"  Full output: {output_path}")
    print(f"  Slim output: {slim_path} ({matched:,} matched runs)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Join metalog metadata onto sandpiper kingfisher metadata")
    parser.add_argument('--config', default='config.yml', help='Path to config.yml')
    # Per-build overrides (mirrors indicpiper_custom/scripts/build_indicpiper_inputs.py) so the
    # Snakefile can point this at the current build's own paths without editing config.yml.
    parser.add_argument('--kingfisher-metadata', help='one kingfisher TSV; overrides KINGFISHER_METADATA')
    parser.add_argument('--kingfisher-metadata-list',
                        help='file listing kingfisher TSVs (one path per line), used instead of '
                             '--kingfisher-metadata; each file may have its own columns')
    parser.add_argument('--download-dir', help='directory holding the four metalog wide files '
                                               '(as written by fetch_metalog.py); overrides the METALOG_* paths')
    parser.add_argument('--output-dir', help='overrides OUTPUT_DIR')
    parser.add_argument('--slim-only', action='store_true',
                        help='write only the slim output (run + meta_ columns)')
    args = parser.parse_args()

    cfg = metalog_config.load_config(args.config)
    if args.download_dir:
        metalog_config.apply_download_dir(cfg, os.path.abspath(args.download_dir))
    if args.kingfisher_metadata:
        cfg['KINGFISHER_METADATA'] = args.kingfisher_metadata
    if args.output_dir:
        cfg['OUTPUT_DIR'] = args.output_dir

    if args.kingfisher_metadata_list:
        kingfisher_paths = read_file_list(args.kingfisher_metadata_list)
    else:
        kingfisher_paths = [cfg['KINGFISHER_METADATA']]

    metalog_paths = {
        'animal':        cfg['METALOG_ANIMAL'],
        'environmental': cfg['METALOG_ENVIRONMENTAL'],
        'human':         cfg['METALOG_HUMAN'],
        'ocean':         cfg['METALOG_OCEAN'],
    }

    os.makedirs(cfg['OUTPUT_DIR'], exist_ok=True)
    slim_path = os.path.join(cfg['OUTPUT_DIR'], cfg['SLIM_OUTPUT_FILE'])
    output_path = None if args.slim_only else os.path.join(cfg['OUTPUT_DIR'], cfg['OUTPUT_FILE'])

    metalog, metalog_cols = load_metalog(metalog_paths)
    join_and_write(kingfisher_paths, metalog, metalog_cols, output_path, slim_path)


if __name__ == '__main__':
    main()
