"""Store the runs Weebill introduced (no SingleM marker-gene hits) in the table ``weebill_only_runs``.

``bin/find_weebill_only.py`` writes the list of accessions. This (re)creates the one-column table
of their run IDs. It changes no other table, so it can be run on a finished database, and running
it again gives the same result. The table is separate from ``parsed_sample_attributes`` so that
databases without it keep working (see ``api/weebill_only.py``).
"""
import logging
import os
from typing import Dict, List

import duckdb

TABLE = 'weebill_only_runs'


def read_accessions(path: str) -> List[str]:
    """The accessions in a list file, one per line; blank lines ignored."""
    if not os.path.exists(path):
        raise FileNotFoundError('Weebill-only accession list not found: {}'.format(path))
    with open(path) as handle:
        accessions = list(dict.fromkeys(line.strip() for line in handle if line.strip()))
    if not accessions:
        raise ValueError('Weebill-only accession list {} is empty; that would clear every flag'.format(path))
    return accessions


def load_weebill_only(db_path: str, accession_file: str) -> Dict[str, int]:
    """Replace the table; returns how many accessions were listed, found in the database (flagged) and unknown, and the run count."""
    accessions = read_accessions(accession_file)
    connection = duckdb.connect(db_path)
    try:
        connection.execute('CREATE TEMP TABLE weebill_only_accessions (acc VARCHAR)')
        connection.executemany('INSERT INTO weebill_only_accessions VALUES (?)', [[a] for a in accessions])
        connection.execute('DROP TABLE IF EXISTS {}'.format(TABLE))
        connection.execute(
            'CREATE TABLE {} AS SELECT DISTINCT m.id AS run_id FROM ncbi_metadata m '
            'JOIN weebill_only_accessions w ON w.acc = m.acc'.format(TABLE))
        flagged = connection.execute('SELECT count(*) FROM {}'.format(TABLE)).fetchone()[0]
        runs = connection.execute('SELECT count(*) FROM ncbi_metadata').fetchone()[0]
    finally:
        connection.close()
    counts = {'listed': len(accessions), 'flagged': flagged, 'unknown': len(accessions) - flagged, 'runs': runs}
    logging.info('weebill_only: %s', counts)
    return counts
