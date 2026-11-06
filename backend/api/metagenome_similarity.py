"""
metagenome_similarity.py
- Picks the descriptive fields of a metagenome run that are compared with the
  rest of its BioProject (see bioproject_similarity.py). Keys match the row
  keys /api/metadata builds, so unique fields can be mapped back onto rows.
"""
import re
from typing import Any

from sandpiper.parse_biosample_extras import ACTUALLY_MISSING

# Columns shown as table rows, identifiers and per-run sizes included. Not the
# run accession, BioProject or SRA study: those have no row to star.
COMPARED_COLUMNS = (
    'experiment', 'sample_name', 'sample_acc', 'biosample',
    'library_name', 'bases', 'spots', 'insertsize', 'ena_first_public_run',
    'ena_last_update_run', 'experiment_title', 'read1_length_average', 'read1_length_stdev',
    'read2_length_average', 'read2_length_stdev',
    'assay_type', 'center_name', 'model', 'librarylayout', 'libraryselection', 'librarysource',
    'platform', 'taxon_name', 'geo_loc_name_country_calc', 'geo_loc_name_country_continent_calc',
    'geo_loc_name', 'library_strategy', 'organisation_department', 'organisation_institution',
    'organisation_street', 'organisation_city', 'organisation_country',
    'organisation_contact_name', 'design_description',
)
# Fields whose values differ between samples by design (identifiers, per-run
# sizes and stamps, free-text titles, contact details, Metalog bookkeeping).
# A difference in these tells the reader nothing, so the run page marks them
# as "expected" rather than as a real difference.
EXPECTED_TO_DIFFER = frozenset({
    'experiment', 'sample_name', 'sample_acc', 'biosample', 'library_name',
    'bases', 'spots', 'insertsize',
    'read1_length_average', 'read1_length_stdev', 'read2_length_average', 'read2_length_stdev',
    'ena_first_public_run', 'ena_last_update_run', 'ena_first_public', 'ena_last_update', 'insdc_first_public', 'insdc_last_update', 'releasedate',
    'experiment_title', 'design_description',
    'organisation_contact_name', 'organisation_street',
    'couple_id', 'study_code', 'available_info', 'description', 'note', 'doi',
})
_IDENTIFIER_SUFFIX = re.compile(r'(^|_)(id|acc|accession|alias|uuid)$')
EXCLUDED_ATTRIBUTES = frozenset({'primary_search', 'study_links', 'Gbp', 'run_size'})
_SAM_SUFFIX = re.compile(r'_sam$')
DATE_FORMAT = '%-d %B %Y'


def _is_present(value: Any) -> bool:
    """False for blanks and the placeholder values the run page hides."""
    return value is not None and str(value).lower().strip() not in ACTUALLY_MISSING


def comparable_values(meta: Any) -> dict:
    """Row key -> value for the fields of `meta` compared across its BioProject.

    Only values the page displays are included, so the shared percentage covers
    exactly the fields that can carry a star. Columns win over biosample
    attributes of the same name. Callers keep only the keys that have a row on
    the page (see api.bioproject_similarity), so the counts match the stars.
    """
    values = {column: getattr(meta, column, None) for column in COMPARED_COLUMNS}
    if meta.collection_date_parsed:
        values['collection_date_parsed'] = meta.collection_date_parsed.strftime(DATE_FORMAT)
    if meta.published:
        values['releasedate'] = meta.published.strftime(DATE_FORMAT)
    for attribute in meta.biosample_attributes:
        key = _SAM_SUFFIX.sub('', attribute.k)
        if attribute.k in EXCLUDED_ATTRIBUTES or key in EXCLUDED_ATTRIBUTES or key in values:
            continue
        values[key] = attribute.v
    return {key: value for key, value in values.items() if _is_present(value)}


METALOG_PREFIX = 'metalog:'


def metalog_comparable_values(attributes: Any) -> dict:
    """Metalog display name -> value for the populated Metalog fields of a run's
    ParsedSampleAttribute row (None when the run has none).

    Keys carry METALOG_PREFIX so they cannot collide with the NCBI keys from
    comparable_values; the run page's Metalog rows are matched the same way.
    """
    if attributes is None:
        return {}
    return {METALOG_PREFIX + row['k']: row['v'] for row in attributes.metalog_rows()}


def is_expected_to_differ(key: str) -> bool:
    """True for a row key (NCBI, or METALOG_PREFIX + Metalog display name)
    whose value is expected to differ between samples."""
    name = key[len(METALOG_PREFIX):] if key.startswith(METALOG_PREFIX) else key
    name = name.lower().replace(' ', '_').replace('-', '_')
    return name in EXPECTED_TO_DIFFER or bool(_IDENTIFIER_SUFFIX.search(name))


def _row_key(key: str) -> str:
    return str(key).lower().replace(' ', '_').replace('-', '_')


def is_already_shown(sections: Any, key: str, value: Any) -> bool:
    """True when a displayed row already has this key (ignoring case, spaces and
    hyphens) with exactly the same value, so a BioSample attribute that repeats
    a database column is not listed twice. `sections` is an iterable of row
    lists; rows without a `raw_k` are never matches."""
    wanted_key, wanted_value = _row_key(key), str(value).strip()
    return any(
        'raw_k' in row and _row_key(row['raw_k']) == wanted_key and str(row.get('v')).strip() == wanted_value
        for rows in sections for row in rows if isinstance(row, dict))
