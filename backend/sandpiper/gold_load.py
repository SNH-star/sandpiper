"""Load the JSON-lines files written by ``backend/bin/fetch_gold.py`` into DuckDB tables.

One table per GOLD record type, one column per GOLD field, so every field GOLD offers is
queryable. Scalars keep a numeric/boolean type when every value in the column has it; anything
else, including nested lists and objects, is stored as text (nested values as JSON).
"""
import json
import logging
import os
from typing import Dict, Iterable, List, Optional

import duckdb
import pandas as pd

# table -> (jsonl file stem, column holding the GOLD ID the record was looked up by)
TABLES = {
    'gold_projects': ('projects', 'gold_project_id'),
    'gold_biosamples': ('biosamples', 'gold_biosample_id'),
    'gold_studies': ('studies', 'gold_study_id'),
    'gold_analysis_projects': ('analysis_projects', 'gold_project_id'),
}


def read_jsonl(path: str) -> Dict[str, Optional[object]]:
    """Records by ID from a fetch_gold file (later lines win; None = unknown to GOLD)."""
    records: Dict[str, Optional[object]] = {}
    if not os.path.exists(path):
        return records
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue  # half-written last line from a killed fetch
            records[entry['id']] = entry['record']
    return records


def _is_plain_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_text(value) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)


def build_frame(records: Dict[str, Optional[object]], id_column: str) -> pd.DataFrame:
    """One row per record; analysis projects (a list per ID) give one row per element."""
    rows: List[dict] = []
    for gold_id, record in sorted(records.items()):
        if not record:
            continue
        for item in record if isinstance(record, list) else [record]:
            rows.append({id_column: gold_id, **item})
    columns = list(dict.fromkeys(key for row in rows for key in row))
    data = {}
    for column in columns:
        values = [row.get(column) for row in rows]
        present = [v for v in values if v is not None]
        is_numeric = bool(present) and all(_is_plain_number(v) for v in present)
        is_boolean = bool(present) and all(isinstance(v, bool) for v in present)
        data[column] = values if (is_numeric or is_boolean) else [_as_text(v) for v in values]
    return pd.DataFrame(data, columns=columns)


def load_gold(db_path: str, download_dir: str) -> Dict[str, int]:
    """(Re)create the gold_* tables in the DuckDB file from ``download_dir``; returns rows per table."""
    if not os.path.isdir(download_dir):
        raise FileNotFoundError('GOLD download directory not found: {}'.format(download_dir))
    counts = {}
    connection = duckdb.connect(db_path)
    try:
        for table, (stem, id_column) in TABLES.items():
            frame = build_frame(read_jsonl(os.path.join(download_dir, stem + '.jsonl')), id_column)
            connection.execute('DROP TABLE IF EXISTS {}'.format(table))
            if frame.empty:
                connection.execute('CREATE TABLE {} ({} VARCHAR)'.format(table, id_column))
            else:
                connection.register('gold_frame', frame)
                connection.execute('CREATE TABLE {} AS SELECT * FROM gold_frame'.format(table))
                connection.unregister('gold_frame')
            counts[table] = frame.shape[0]
            logging.info('%s: %d rows', table, counts[table])
    finally:
        connection.close()
    return counts
