#!/usr/bin/env python3
"""Append metalog extended metadata (meta_* columns) onto parsed_metadata.tsv.

parsed_metadata.tsv (one row per run) is the source of truth for its native
columns. This step only *appends* the meta_* columns from a metalog extension
file (also keyed by run); the two never share a column name, so native values
are never touched. Runs absent from the extension receive empty meta_ values.

If --metalog-extension is omitted, parsed_metadata.tsv is passed through
unchanged so the pipeline behaves exactly as it did before the metalog
extension existed (backward-compatible).

The metalog extension file is the slim output of metaup_sandpiper:
    run  meta_<col1>  meta_<col2>  ...
"""

import argparse
import datetime
import json
import logging
import os
import shutil
import sys


PROVENANCE_SUFFIX = '.metalog_provenance.json'


def derive_provenance(extension_path):
    """Derive Metalog retrieval provenance without a manually supplied date."""
    extension_path = os.path.abspath(extension_path)
    candidates = [
        extension_path + '.provenance.json',
        os.path.join(os.path.dirname(os.path.dirname(extension_path)),
                     'metalog_downloads', 'metalog_fetch_manifest.json'),
    ]
    for manifest_path in candidates:
        if not os.path.exists(manifest_path):
            continue
        with open(manifest_path) as f:
            manifest = json.load(f)
        fetched_at = manifest.get('fetched_at')
        if fetched_at:
            return {'fetched_at': fetched_at,
                    'derived_from': 'metalog_fetch_manifest',
                    'manifest': manifest_path}

    # Legacy Metalog outputs pre-date the fetch manifest. Their modification
    # time is the best available, reproducible record of when that source
    # artifact was obtained/generated.
    timestamp = os.path.getmtime(extension_path)
    fetched_at = datetime.datetime.fromtimestamp(
        timestamp, tz=datetime.timezone.utc).astimezone().isoformat(timespec='seconds')
    return {'fetched_at': fetched_at,
            'derived_from': 'extension_file_mtime',
            'source': extension_path}


def write_provenance(extension_path, output_path):
    provenance_path = output_path + PROVENANCE_SUFFIX
    with open(provenance_path, 'w') as f:
        json.dump(derive_provenance(extension_path), f, indent=2)
        f.write('\n')
    logging.info("Wrote Metalog provenance -> %s", provenance_path)


def load_extension(path):
    """Read the slim extension file.

    Returns (lookup, meta_cols) where lookup maps run -> list[str] of meta
    values aligned to meta_cols (the ordered meta_* column names).
    """
    with open(path) as f:
        header = f.readline().rstrip('\r\n').split('\t')
        if not header or header[0] != 'run':
            raise ValueError(
                "Expected first column 'run' in extension file {}, got {!r}".format(
                    path, header[0] if header else None))
        meta_cols = header[1:]
        n_meta = len(meta_cols)

        lookup = {}
        for line in f:
            fields = line.rstrip('\r\n').split('\t')
            run = fields[0]
            vals = fields[1:]
            # Tolerate short rows (trailing empty cells dropped on write).
            if len(vals) < n_meta:
                vals = vals + [''] * (n_meta - len(vals))
            elif len(vals) > n_meta:
                raise ValueError(
                    "Row for run {} has {} value columns, expected {} in {}".format(
                        run, len(vals), n_meta, path))
            lookup[run] = vals

    logging.info("Loaded %d runs and %d meta_ columns from %s",
                 len(lookup), n_meta, path)
    return lookup, meta_cols


def merge(parsed_path, extension_path, output_path):
    """Append meta_ columns from the extension onto parsed_metadata, by run."""
    lookup, meta_cols = load_extension(extension_path)
    empty = [''] * len(meta_cols)

    matched = 0
    total = 0
    with open(parsed_path) as fin, open(output_path, 'w') as fout:
        header = fin.readline().rstrip('\r\n').split('\t')
        try:
            i_run = header.index('run')
        except ValueError:
            raise ValueError(
                "No 'run' column in parsed metadata {}; header={}".format(
                    parsed_path, header))

        overlap = set(header) & set(meta_cols)
        if overlap:
            raise ValueError(
                "Column name collision between parsed metadata and meta_ columns: "
                "{}".format(sorted(overlap)))

        fout.write('\t'.join(header + meta_cols) + '\n')

        for line in fin:
            fields = line.rstrip('\r\n').split('\t')
            run = fields[i_run] if i_run < len(fields) else ''
            meta_vals = lookup.get(run)
            if meta_vals is not None:
                matched += 1
            else:
                meta_vals = empty
            fout.write('\t'.join(fields + meta_vals) + '\n')
            total += 1

    logging.info("Merged metalog extension: %d / %d runs enriched -> %s",
                 matched, total, output_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--parsed-metadata', required=True,
                        help='parsed_metadata.tsv from parse_biosample_extras.py')
    parser.add_argument('--metalog-extension', default='',
                        help='slim metalog extension TSV (run + meta_ columns); '
                             'if omitted, parsed metadata is passed through unchanged')
    parser.add_argument('--output', required=True,
                        help='output path for the extended parsed metadata TSV')
    parser.add_argument('--debug', action='store_true', help='verbose logging')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p')

    ext = args.metalog_extension.strip()
    if not ext:
        logging.info("No --metalog-extension given; passing parsed metadata through unchanged")
        shutil.copyfile(args.parsed_metadata, args.output)
        with open(args.output + PROVENANCE_SUFFIX, 'w') as f:
            json.dump({'fetched_at': None, 'derived_from': 'no_metalog_extension'}, f)
            f.write('\n')
        return

    if not os.path.exists(ext):
        raise SystemExit("Metalog extension file does not exist: {}".format(ext))

    merge(args.parsed_metadata, ext, args.output)
    write_provenance(ext, args.output)


if __name__ == '__main__':
    main()
