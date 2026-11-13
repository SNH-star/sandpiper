"""JGI GOLD records read from the database's ``gold_*`` tables.

``bin/fetch_gold.py`` downloads everything GOLD holds for the projects Sandpiper knows about and
``sandpiper.gold_load`` stores it in four tables (projects, biosamples, studies, analysis
projects), one column per GOLD field. This module reads those tables:

* :func:`fetch_summary` / :func:`fetch_summaries` give the same summary the live GOLD service used
  to (rows, publications, link) for the run page, so the page never calls GOLD;
* :func:`matching_project_ids` turns a ``gold:`` search into a query for the GOLD project IDs
  whose record matches, which the caller links to runs through the BioSample ``sample_alias``.

The tables are small (about 25,000 projects), so nothing here needs an index. Everything works
on a database without the tables: lookups find nothing and searches match nothing.
"""
import json
import math
import re
from typing import Dict, Iterable, List, Mapping, NamedTuple, Optional, Tuple

from sqlalchemy import String, bindparam, cast, column, or_, select, table, text, union

from . import gold

PROJECTS = 'gold_projects'
BIOSAMPLES = 'gold_biosamples'
STUDIES = 'gold_studies'
ANALYSIS_PROJECTS = 'gold_analysis_projects'
GOLD_TABLES = (PROJECTS, BIOSAMPLES, STUDIES, ANALYSIS_PROJECTS)

# DuckDB takes a one character ESCAPE, and SQLAlchemy would write a backslash as two.
_LIKE_ESCAPE = '!'
_schema_by_database: Dict[str, 'GoldSchema'] = {}


class GoldSchema(NamedTuple):
    """The columns each GOLD table has in this database (empty when the tables are not there)."""

    columns: Mapping[str, Tuple[str, ...]]

    @property
    def is_empty(self) -> bool:
        return not self.columns.get(PROJECTS)

    def field_names(self) -> List[str]:
        """Every searchable field once, whichever tables it is in, in alphabetical order."""
        names = {name for columns in self.columns.values() for name in columns}
        return sorted(names, key=str.lower)


def _usable(columns: Mapping[str, Tuple[str, ...]]) -> Dict[str, Tuple[str, ...]]:
    """Only the tables the queries below can use.

    The loader makes a table with just its own ID column when GOLD gave no records for it, so a
    table counts only when it has the GOLD ID column the others are joined on, and nothing at all
    counts without a project table that has its own ID.
    """
    projects = columns.get(PROJECTS, ())
    if 'projectGoldId' not in projects:
        return {}
    usable = {PROJECTS: projects}
    for name, key in ((BIOSAMPLES, 'biosampleGoldId'), (STUDIES, 'studyGoldId')):
        if key in projects and key in columns.get(name, ()):
            usable[name] = columns[name]
    if 'gold_project_id' in columns.get(ANALYSIS_PROJECTS, ()):
        usable[ANALYSIS_PROJECTS] = columns[ANALYSIS_PROJECTS]
    return usable


def load_schema(connection) -> GoldSchema:
    """Read which GOLD tables and columns the database has (empty when it has no usable GOLD data)."""
    names = ', '.join("'{}'".format(name) for name in GOLD_TABLES)
    rows = connection.execute(text(
        'SELECT table_name, column_name FROM information_schema.columns '
        'WHERE table_name IN ({}) AND table_schema = current_schema() AND table_catalog = current_database() '
        'ORDER BY table_name, ordinal_position'.format(names))).all()
    columns: Dict[str, List[str]] = {}
    for table_name, column_name in rows:
        columns.setdefault(table_name, []).append(column_name)
    return GoldSchema(_usable({name: tuple(found) for name, found in columns.items()}))


def get_schema(connection) -> GoldSchema:
    """The schema, read once per database. A database without GOLD data is read again next time,
    so loading the tables while the API is running is noticed."""
    key = str(connection.engine.url)
    schema = _schema_by_database.get(key)
    if schema is None:
        schema = load_schema(connection)
        if not schema.is_empty:
            _schema_by_database[key] = schema
    return schema


def normalise_field(name: str) -> str:
    """``Ecosystem Type``, ``ecosystem_type`` and ``ecosystemType`` all become ``ecosystemtype``."""
    return re.sub(r'[^a-z0-9]', '', name.lower())


# --- reading ---------------------------------------------------------------------------------------

def record_from_row(row: Mapping) -> dict:
    """A GOLD record as the web service gave it: empty values dropped, lists and objects read back from text."""
    record = {}
    for key, value in row.items():
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        if isinstance(value, str) and value.startswith(('[', '{')):
            try:
                value = json.loads(value)
            except ValueError:
                pass
        record[key] = value
    return record


def _rows_where(connection, table_name: str, id_column: str, ids: List[str]) -> Dict[str, dict]:
    query = text('SELECT * FROM {} WHERE "{}" IN :ids'.format(table_name, id_column)).bindparams(
        bindparam('ids', expanding=True))
    found = {}
    for row in connection.execute(query, {'ids': ids}).mappings():
        record = record_from_row(row)
        found[record[id_column]] = record
    return found


def fetch_summaries(connection, project_ids: Iterable[str]) -> Dict[str, dict]:
    """GOLD summaries (see :func:`api.gold.build_summary`) by project ID, for the projects the database has."""
    ids = list(dict.fromkeys(project_ids))
    schema = get_schema(connection)
    if not ids or schema.is_empty:
        return {}
    projects = _rows_where(connection, PROJECTS, 'projectGoldId', ids)
    biosample_ids = list(dict.fromkeys(p['biosampleGoldId'] for p in projects.values() if p.get('biosampleGoldId')))
    study_ids = list(dict.fromkeys(p['studyGoldId'] for p in projects.values() if p.get('studyGoldId')))
    biosamples = _rows_where(connection, BIOSAMPLES, 'biosampleGoldId', biosample_ids) if biosample_ids and BIOSAMPLES in schema.columns else {}
    studies = _rows_where(connection, STUDIES, 'studyGoldId', study_ids) if study_ids and STUDIES in schema.columns else {}
    return {project_id: gold.build_summary(project, biosamples.get(project.get('biosampleGoldId')),
                                           studies.get(project.get('studyGoldId')))
            for project_id, project in projects.items()}


def fetch_summary(connection, project_id: str) -> Optional[dict]:
    """The GOLD summary for one project, or None when the database has nothing for it."""
    return fetch_summaries(connection, [project_id]).get(project_id)


# --- searching -------------------------------------------------------------------------------------

def _contains(sql_column, needle: str):
    """Case-insensitive 'contains', the value taken literally and numbers compared as text."""
    escaped = needle.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2).replace('%', _LIKE_ESCAPE + '%').replace('_', _LIKE_ESCAPE + '_')
    return cast(sql_column, String).ilike('%{}%'.format(escaped), escape=_LIKE_ESCAPE)


def _targets(schema: GoldSchema, field: Optional[str]) -> Dict[str, List[str]]:
    """The columns to look in, by table: every column, or those the field name stands for."""
    wanted = normalise_field(field) if field is not None else None
    found = {name: [c for c in columns if wanted is None or normalise_field(c) == wanted]
             for name, columns in schema.columns.items()}
    return {name: columns for name, columns in found.items() if columns}


def matching_project_ids(schema: GoldSchema, value: str):
    """A query for the GOLD project IDs whose record matches ``value``, or None when nothing can match.

    ``field=text`` looks only in the GOLD field of that name (in whichever table it is: a study
    field finds the study's projects, an analysis project field finds its project). Plain text
    looks in every field of every table, so it also finds things in IDs, lists and publication
    details; a search for "eye" wants every record that mentions eye, however it does. None
    means the database has no GOLD tables, or the field name is not one of theirs.
    """
    if schema.is_empty:
        return None
    field, _, needle = value.partition('=') if '=' in value else (None, '', value)
    targets = _targets(schema, field.strip() if field is not None else None)
    if not targets:
        return None
    needle = needle.strip()
    projects = table(PROJECTS, *[column(c) for c in schema.columns[PROJECTS]])
    selects = []
    for name, columns in targets.items():
        other = projects if name == PROJECTS else table(name, *[column(c) for c in schema.columns[name]])
        match = or_(*[_contains(other.c[c], needle) for c in columns])
        if name == PROJECTS:
            selects.append(select(projects.c.projectGoldId.label('project_id')).where(match))
        elif name == BIOSAMPLES:
            selects.append(select(projects.c.projectGoldId.label('project_id')).select_from(
                projects.join(other, projects.c.biosampleGoldId == other.c.biosampleGoldId)).where(match))
        elif name == STUDIES:
            selects.append(select(projects.c.projectGoldId.label('project_id')).select_from(
                projects.join(other, projects.c.studyGoldId == other.c.studyGoldId)).where(match))
        else:
            selects.append(select(other.c.gold_project_id.label('project_id')).where(match))
    matches = union(*selects).subquery()
    return select(matches.c.project_id)
