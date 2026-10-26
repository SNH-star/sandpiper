#!/usr/bin/env python3
"""Generate the SQLAlchemy column block for the metalog meta_ columns.

Reads the header of the metalog_custom slim file and emits one
`db.Column(db.String)` line per meta_ column. The output is pasted between the
BEGIN/END markers inside ParsedSampleAttribute in sandpiper backend/api/models.py.

Usage:
    gen_meta_columns.py <slim_file.tsv>
"""

import sys


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: gen_meta_columns.py <slim_file.tsv>")
    slim = sys.argv[1]

    with open(slim) as f:
        header = f.readline().rstrip('\r\n').split('\t')
    meta_cols = [c for c in header if c.startswith('meta_')]
    if not meta_cols:
        raise SystemExit("No meta_ columns found in {}".format(slim))

    out = [
        "    # --- BEGIN metalog meta_ columns (generated; see metalog_custom) ---",
        "    # Auto-generated from the metalog_custom slim file header. All metalog",
        "    # extended-metadata fields, stored as String (source data is heterogeneous,",
        "    # e.g. '0-0.1', 'unknown'). Populated by the parsed_metadata stage when",
        "    # INCLUDE_METALOG is enabled; NULL otherwise. Regenerate with",
        "    # scripts/gen_meta_columns.py if the metalog schema changes.",
    ]
    out += ["    {} = db.Column(db.String)".format(c) for c in meta_cols]
    out.append("    # --- END metalog meta_ columns ---")
    print("\n".join(out))


if __name__ == '__main__':
    main()
