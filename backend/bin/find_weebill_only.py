#!/usr/bin/env python3
"""List the runs Weebill introduced: in Weebill's condensed table but with no SingleM marker-gene hits.

A run has marker-gene hits when it appears in SingleM's OTU table (one row per OTU, with a
``sample`` column). The Weebill-integrated condensed table (the build's CONDENSED_OTU_TABLE,
also with a ``sample`` column) lists every run Sandpiper profiles. A run in the second and not
the first has a profile made only by Weebill's k-mer matching.

Only the ``sample`` column is read, so the large OTU table is scanned but not held in memory.

Usage: find_weebill_only.py WEEBILL_CONDENSED.csv.gz SINGLEM_OTU_TABLE.csv.gz OUTPUT.txt
Writes one accession per line, and prints the counts.
"""
import argparse
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Set

import duckdb

SAMPLE_COLUMN = 'sample'


def read_samples(path: str) -> Set[str]:
    """The distinct values of the ``sample`` column of a delimited (optionally gzipped) table."""
    connection = duckdb.connect()
    try:
        columns = [row[0] for row in connection.execute(
            'DESCRIBE SELECT * FROM read_csv(?, header = true, all_varchar = true)', [path]).fetchall()]
        if SAMPLE_COLUMN not in columns:
            raise ValueError('{} has no "{}" column (columns: {})'.format(path, SAMPLE_COLUMN, ', '.join(columns)))
        rows = connection.execute(
            'SELECT DISTINCT "{}" FROM read_csv(?, header = true, all_varchar = true)'.format(SAMPLE_COLUMN), [path]).fetchall()
    finally:
        connection.close()
    return {row[0].strip() for row in rows if row[0] and row[0].strip()}


def weebill_only_accessions(weebill_samples: Iterable[str], singlem_samples: Iterable[str]) -> List[str]:
    """Runs Weebill profiled that SingleM found no marker genes in, sorted."""
    return sorted(set(weebill_samples) - set(singlem_samples))


def main(argv: Optional[Sequence[str]] = None) -> Dict[str, int]:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('weebill_condensed', help="Weebill-integrated condensed table (CONDENSED_OTU_TABLE)")
    parser.add_argument('singlem_otu_table', help="SingleM's OTU table (OTU_TABLE)")
    parser.add_argument('output', help='file to write, one accession per line')
    args = parser.parse_args(argv)

    weebill = read_samples(args.weebill_condensed)
    singlem = read_samples(args.singlem_otu_table)
    accessions = weebill_only_accessions(weebill, singlem)
    with open(args.output, 'w') as handle:
        handle.writelines(accession + '\n' for accession in accessions)
    counts = {'weebill_runs': len(weebill), 'singlem_runs': len(singlem), 'weebill_only': len(accessions)}
    print('{weebill_runs} runs in the Weebill table, {singlem_runs} with SingleM marker-gene hits, '
          '{weebill_only} Weebill only -> {out}'.format(out=args.output, **counts))
    return counts


if __name__ == '__main__':
    main(sys.argv[1:])
