"""
api.py
- provides the API endpoints for consuming and producing
  REST requests and responses
"""
import csv
from dataclasses import dataclass
import functools
import io
import logging
import re
import requests
from datetime import datetime

from flask import Blueprint, jsonify, request, make_response, current_app, Response, stream_with_context

from sqlalchemy import Integer, select, distinct, or_, and_, case, literal
from sqlalchemy.sql import func, text
from sqlalchemy.orm import joinedload, lazyload, aliased

from .models import (
    NcbiMetadata,
    ParsedSampleAttribute,
    BiosampleAttribute,
    db,
    Marker,
    CondensedProfile,
    CondensedProfileCtas1,
    Taxonomy,
    SandpiperCache,
    IndicatorHabitatScore,
    IndicatorHabitatGenusScore,
)
import polars as pl
# from api.models import #for flask shell
from .bioproject_similarity import compare_to_peers
from .metagenome_similarity import METALOG_PREFIX, comparable_values, is_already_shown, is_expected_to_differ, metalog_comparable_values
from .grid import describe_grid, grid_condition, parse_grid_squares
from .keywords import LIKE_ESCAPE, like_pattern, parse_keyword_terms
from .match_cache import MatchCache
from . import statistics_figures as figures
from .version import __version__, __gtdb_version__, __indicpiper_version__, __scrape_date__

import os, sys, json
sys.path = [os.environ['HOME']+'/git/singlem-local'] + [os.environ['HOME']+'/git/singlem'] + sys.path
from singlem.condense import WordNode
from singlem.summariser import Summariser

sys.path = [os.path.join(os.path.dirname(os.path.realpath(__file__)),'..')] + sys.path
from sandpiper.biosample_attributes import *
from sandpiper.parse_biosample_extras import ACTUALLY_MISSING

api = Blueprint('api', __name__)

sandpiper_stats_cache = None
biosample_attribute_definitions = None
ncbi_metadata_infos = None
metalog_provenance = None

def generate_cache():
    global sandpiper_stats_cache
    global biosample_attribute_definitions
    global ncbi_metadata_infos
    global metalog_provenance

    if (
        sandpiper_stats_cache is None
        or biosample_attribute_definitions is None
        or ncbi_metadata_infos is None
    ):
        try:
            cache_rows = SandpiperCache.query.all()
            cache = {row.key: json.loads(row.value) for row in cache_rows}
            if 'stats' in cache and sandpiper_stats_cache is None:
                sandpiper_stats_cache = cache['stats']
            if 'biosample_attribute_definitions' in cache and biosample_attribute_definitions is None:
                biosample_attribute_definitions = {
                    k: BioSampleAttribute(**v)
                    for k, v in cache['biosample_attribute_definitions'].items()
                }
            if 'ncbi_metadata_infos' in cache and ncbi_metadata_infos is None:
                ncbi_metadata_infos = {
                    k: NcbiMetadataExtraInfo(**v)
                    for k, v in cache['ncbi_metadata_infos'].items()
                }
            if 'metalog_provenance' in cache and metalog_provenance is None:
                metalog_provenance = cache['metalog_provenance']
        except Exception as e:
            current_app.logger.warning(
                'Failed to load cache table, regenerating dynamically: %s', e
            )

    if sandpiper_stats_cache is None or len(sandpiper_stats_cache) != 3:
        sandpiper_stats_cache = {}
        sandpiper_stats_cache['sandpiper_total_terrabases'] = db.session.query(func.sum(NcbiMetadata.bases)).scalar()/10**12
        sandpiper_stats_cache['sandpiper_num_runs'] = db.session.query(func.count(distinct(NcbiMetadata.acc))).scalar()
        sandpiper_stats_cache['sandpiper_num_bioprojects'] = db.session.query(func.count(distinct(NcbiMetadata.bioproject))).scalar()
    if biosample_attribute_definitions is None:
        biosample_attribute_definitions = BioSampleAttributes(current_app.logger).attributes
    if ncbi_metadata_infos is None:
        ncbi_metadata_infos = NcbiMetadataExtraInfos().extra_info
    if metalog_provenance is None:
        metalog_provenance = {}


def metalog_retrieved_date():
    """Human-readable retrieval date derived during the Metalog merge."""
    generate_cache()
    fetched_at = metalog_provenance.get('fetched_at')
    if not fetched_at:
        return None
    try:
        return datetime.fromisoformat(fetched_at).strftime('%-d %B %Y')
    except (TypeError, ValueError):
        current_app.logger.warning('Invalid Metalog fetched_at value: %r', fetched_at)
        return None


def database_versions(fetched_at, indicpiper_version):
    """The Metalog collection date and IndicPiper version this database carries.

    The Metalog date is when Sandpiper pulled it (the build's collection date), not
    Metalog's own release date. Either value is None when it is not recorded.
    """
    collected = None
    if fetched_at:
        try:
            collected = datetime.fromisoformat(fetched_at).strftime('%-d %B %Y')
        except (TypeError, ValueError):
            logging.getLogger(__name__).warning('Invalid Metalog fetched_at value: %r', fetched_at)
    return {'metalog_collected_date': collected, 'indicpiper_version': indicpiper_version or None}


def metalog_release():
    """Metalog's own release date and advertised sample totals, or None.

    Recorded at fetch time (see metalog_custom/scripts/fetch_metalog.py) and
    carried here through the same provenance blob as fetched_at. Distinct from
    metalog_retrieved_date(), which is when Sandpiper downloaded the data --
    this is the release Metalog itself publishes. Databases built before this
    was recorded simply have no 'release' key, so the front end keeps its own
    last-known values.
    """
    generate_cache()
    release = metalog_provenance.get('release')
    if not release:
        return None
    return {
        'last_metadata_update': release.get('last_metadata_update'),
        'sample_counts': release.get('sample_counts'),
    }


@functools.lru_cache(maxsize=1)
def _indicator_habitat_genus_scores_exists():
    """Whether this DB has the indicator_habitat_genus_scores table yet --
    False for any db built before it was added (see generate_backend_db's
    add_indicpiper_scores()), so indicpiper_rows() can degrade to the flat
    (habitat, score) view instead of erroring on older databases. Cached:
    schema doesn't change mid-process.

    Deliberately a raw information_schema query, not sqlalchemy.inspect()'s
    generic reflection -- that goes through duckdb-engine's postgres-style
    dialect emulation and errors against DuckDB's actual pg_catalog
    implementation (confirmed against a live run: 500 on /api/metadata/<acc>,
    a pg_catalog.pg_class/pg_attribute query failing under the hood).
    """
    tables = {row[0] for row in db.session.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_name = 'indicator_habitat_genus_scores'"
    ))}
    return 'indicator_habitat_genus_scores' in tables


@functools.lru_cache(maxsize=1)
def _indicator_habitat_genus_scores_has_indval():
    """Whether indicator_habitat_genus_scores has the ind_val_mean/p_val_mean
    columns -- False for any DB whose --stage indicpiper hasn't been re-run
    since these columns were added (see generate_backend_db's
    add_indicpiper_scores(), which ALTER TABLE ADD COLUMN IF NOT EXISTS's
    them onto a pre-existing table rather than requiring a fresh rebuild).
    Schema migration (this code) and the DB rebuild that actually adds the
    columns are separate, independently-timed operational steps against a
    live production DB -- this code must not 500 in the gap between them.
    Cached: schema doesn't change mid-process.
    """
    columns = {row[0] for row in db.session.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'indicator_habitat_genus_scores' "
        "AND column_name = 'ind_val_mean'"
    ))}
    return 'ind_val_mean' in columns


def indicpiper_rows(run_id):
    """This run's IndicPiper habitat-indicator scores, one entry per matched
    habitat, each carrying its genus-level breakdown for
    IndicPiperHabitatChart.vue's stacked bar + detail list.

    indicator_habitat_scores only has a row for a (run, habitat) pair when the
    score is nonzero (see IndicatorHabitatScore's docstring in models.py), so
    most runs have a handful of rows, not one per habitat. Sorted by score
    descending -- the strongest habitat match first. Empty list when the run
    has no indicator match, which the front end uses to decide whether to
    show the section at all.
    """
    has_genus_detail = _indicator_habitat_genus_scores_exists()
    has_indval = _indicator_habitat_genus_scores_has_indval()
    scores = db.session.execute(
        select(IndicatorHabitatScore.habitat, IndicatorHabitatScore.score)
        .where(IndicatorHabitatScore.run_id == run_id)
        .order_by(IndicatorHabitatScore.score.desc())
    ).all()

    genus_rows_by_habitat = {}
    if has_genus_detail and scores:
        genus_columns = [
            IndicatorHabitatGenusScore.habitat,
            IndicatorHabitatGenusScore.genus,
            IndicatorHabitatGenusScore.relative_abundance,
        ]
        if has_indval:
            genus_columns += [
                IndicatorHabitatGenusScore.ind_val_mean,
                IndicatorHabitatGenusScore.p_val_mean,
            ]
        genus_scores = db.session.execute(
            select(*genus_columns)
            .where(IndicatorHabitatGenusScore.run_id == run_id)
            .order_by(IndicatorHabitatGenusScore.relative_abundance.desc())
        ).all()
        for g in genus_scores:
            genus_rows_by_habitat.setdefault(g.habitat, []).append(dict(
                genus=g.genus,
                relative_abundance=g.relative_abundance,
                ind_val_mean=g.ind_val_mean if has_indval else None,
                p_val_mean=g.p_val_mean if has_indval else None,
            ))

    rows = []
    for s in scores:
        # indicator_habitat_scores only ever has a row when the raw score is
        # strictly > 0 (see the HAVING clause in generate_backend_db's
        # add_indicpiper_scores()), but rounding to 3dp can still bring a
        # genuinely positive score (e.g. 0.0003) down to 0.000 -- showing a
        # bare "0" there reads as "no match" when it's actually a real,
        # if marginal, one. Show the threshold instead of a misleading zero.
        rounded = round(s.score, 3)
        v = '<0.001' if rounded == 0 else rounded
        description = ('Summed relative abundance, in this run, of the genera IndicPiper '
                        'identified as indicators of the "{}" habitat.'.format(s.habitat))
        genera = genus_rows_by_habitat.get(s.habitat, [])
        if genera:
            description += ' Indicator genera present in this run, by abundance: {}.'.format(
                ', '.join(g['genus'] for g in genera))
        rows.append(dict(
            k=s.habitat,
            v=v,
            description=description,
            is_custom=False,
            score=s.score,
            genera=genera))
    return rows



######## DEBUG to find slow SQL queries ########
# Set up SQL logging for debugging
from sqlalchemy import event
import time
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.perf_counter()
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.perf_counter() - getattr(context, "_query_start_time", 0)
    print(f"[SQL] {statement} - {total:.6f} sec")
# Attach listeners when the application context is available (on first request).
# Attaching at import time caused "Working outside of application context" because
# db.engine requires the current_app to be set up.
@api.before_app_request
def setup_sql_logging():
    # Only enable SQL timing when in debug mode (or if explicitly enabled via config)
    try:
        event.listen(db.engine, "before_cursor_execute", before_cursor_execute)
        event.listen(db.engine, "after_cursor_execute", after_cursor_execute)
    except RuntimeError:
        # If for some reason the app context is still not available, log a warning.
        try:
            current_app.logger.warning("Could not attach SQL event listeners at setup_sql_logging()")
        except Exception:
            # Fallback to printing if logger isn't available
            print("Warning: Could not attach SQL event listeners at setup_sql_logging()")
######## END DEBUG to find slow SQL queries ########



@api.route('/sandpiper_stats', methods=['GET'])
def sandpiper_stats():
    global sandpiper_stats_cache

    # Cache results because they don't change unless the DB changes
    generate_cache()

    return jsonify({
        'num_terrabases': round(sandpiper_stats_cache['sandpiper_total_terrabases']),
        'num_runs': sandpiper_stats_cache['sandpiper_num_runs'],
        'num_bioprojects': sandpiper_stats_cache['sandpiper_num_bioprojects'],
        'version': __version__,
        'scrape_date': __scrape_date__,
        'gtdb_version': __gtdb_version__,
        'metalog_retrieved_date': metalog_retrieved_date(),
        'metalog_release': metalog_release(),
    })

SAMPLE_TYPE_ORDER = (('host', 'host_associated'), ('ecological', 'ecological'), (None, 'unclassified'))
COVERAGE_ORDER = ('coordinates', 'metalog', 'indicpiper', 'low_complexity')


def _percent(count, total):
    return round(100 * count / total, 1) if total else 0


def statistics_payload(total_runs, bioprojects, terabases, host_counts, release_years, coverage_counts, top_taxa):
    """Shape the Statistics page's figures: counts plus their share of all runs.

    host_counts: Sandpiper's host/ecological call -> runs (None = no call).
    release_years: (year string or None, runs) pairs.
    coverage_counts: name -> runs, or None when that table is not in the database.
    top_taxa: taxonomy type -> level -> (name, host runs, ecological runs) rows.
    """
    return {
        'totals': {'runs': total_runs, 'bioprojects': bioprojects, 'terabases': round(terabases, 1)},
        'sample_types': [
            {'key': key, 'runs': host_counts.get(call, 0), 'percent': _percent(host_counts.get(call, 0), total_runs)}
            for call, key in SAMPLE_TYPE_ORDER],
        'release_years': sorted(
            ({'year': int(year), 'runs': runs} for year, runs in release_years if year is not None),
            key=lambda row: row['year']),
        'coverage': [
            {'key': key, 'runs': coverage_counts.get(key),
             'percent': None if coverage_counts.get(key) is None else _percent(coverage_counts[key], total_runs)}
            for key in COVERAGE_ORDER],
        'top_taxa': {
            taxonomy_type: {
                level: sorted(
                    ({'name': name, 'host': host or 0, 'ecological': ecological or 0,
                      'runs': (host or 0) + (ecological or 0),
                      'percent': _percent((host or 0) + (ecological or 0), total_runs)}
                     for name, host, ecological in rows),
                    key=lambda row: -row['runs'])
                for level, rows in levels.items()}
            for taxonomy_type, levels in top_taxa.items()},
    }


KNOWN_SPECIES_BINS = 20
SAMPLE_CALL_KEYS = (('host', 'host_associated'), ('ecological', 'ecological'))


def known_species_payload(histogram_rows, bins=KNOWN_SPECIES_BINS):
    """How known species fraction is spread across the runs, for the Statistics page.

    histogram_rows: (band number, host/ecological call, runs), where the 0 to 1
    fraction is cut into `bins` bands. Each group's figures are its share of its
    own runs per band, so groups of different size can be compared.
    """
    width = 100 // bins
    distribution = {'bin_width': width}
    for call, key in SAMPLE_CALL_KEYS:
        counts = [0] * bins
        for band, row_call, runs in histogram_rows:
            if row_call == call:
                counts[band] += runs
        total = sum(counts)
        distribution[key] = [
            {'start': band * width, 'percent': round(100 * runs / total, 1) if total else 0}
            for band, runs in enumerate(counts)]
    return {'distribution': distribution}


TOP_TAXA_LEVELS = ('phylum', 'genus', 'species')
TOP_TAXA_COUNT = 10


def _top_taxa():
    """The taxa found in the most runs, per taxonomy database and level. The
    host/ecological run counts are stored on each taxonomy row."""
    detected = func.coalesce(Taxonomy.host_sample_count, 0) + func.coalesce(Taxonomy.ecological_sample_count, 0)
    return {
        taxonomy_type: {
            level: db.session.execute(select(
                Taxonomy.name, Taxonomy.host_sample_count, Taxonomy.ecological_sample_count).where(
                Taxonomy.taxonomy_type == taxonomy_type, Taxonomy.taxonomy_level == level).order_by(
                detected.desc()).limit(TOP_TAXA_COUNT)).all()
            for level in TOP_TAXA_LEVELS}
        for taxonomy_type in ('gtdb', 'globdb')}


statistics_cache = None


@api.route('/sandpiper_statistics', methods=['GET'])
def sandpiper_statistics():
    """Figures for the Statistics page. They only change when the database does,
    so they are worked out once per process."""
    global statistics_cache
    if statistics_cache is None:
        total_runs, bioprojects, bases = db.session.execute(select(
            func.count(), func.count(distinct(NcbiMetadata.bioproject)), func.sum(NcbiMetadata.bases))).one()
        host_counts = dict(db.session.execute(select(
            ParsedSampleAttribute.host_or_not_mature, func.count()).group_by(
            ParsedSampleAttribute.host_or_not_mature)).all())
        release_year = func.extract('year', NcbiMetadata.published)
        release_years = db.session.execute(select(release_year, func.count()).group_by(release_year)).all()
        parsed = ParsedSampleAttribute
        coordinates, metalog, low_complexity = db.session.execute(select(
            func.count().filter(parsed.latitude.is_not(None), parsed.longitude.is_not(None)),
            func.count().filter(parsed.meta_environment_biome.is_not(None)),
            func.count().filter(parsed.low_complexity.is_(True)))).one()
        indicpiper = None
        if _indicator_habitat_genus_scores_exists():
            indicpiper = db.session.execute(select(
                func.count(distinct(IndicatorHabitatScore.run_id)))).scalar()
        band = func.least(func.floor(parsed.known_species_fraction * KNOWN_SPECIES_BINS), KNOWN_SPECIES_BINS - 1).cast(Integer)
        known_species = known_species_payload(db.session.execute(select(band, parsed.host_or_not_mature, func.count()).where(
            parsed.known_species_fraction.is_not(None)).group_by(band, parsed.host_or_not_mature)).all())
        statistics_cache = statistics_payload(
            total_runs, bioprojects, (bases or 0) / 10**12, host_counts, release_years,
            {'coordinates': coordinates, 'metalog': metalog, 'indicpiper': indicpiper,
             'low_complexity': low_complexity},
            _top_taxa())
        statistics_cache['known_species'] = known_species
        statistics_cache['year_breakdown'] = figures.query_year_breakdown(db.session)
        statistics_cache['map'] = figures.query_map_cells(db.session)
    generate_cache()
    return jsonify({**statistics_cache, 'version': __version__, 'gtdb_version': __gtdb_version__,
                    'scrape_date': __scrape_date__,
                    **database_versions(metalog_provenance.get('fetched_at'), __indicpiper_version__)})


@api.route('/markers/', methods=('GET',))
def fetch_markers():
    markers = Marker.query.all()
    return jsonify({ 'markers': [s.to_dict() for s in markers] })

@api.route('/condensed/<string:sample_name>', methods=('GET',))
def fetch_condensed(sample_name):
    taxonomy_type = request.args.get('taxonomy_type', 'gtdb')
    root = WordNode(None, 'Root')
    taxons_to_wordnode = {root.word: root}

    condensed = db.session.execute(
        select(CondensedProfile.coverage, Taxonomy.full_name)
            .join(CondensedProfile.ncbi_metadata)
            .filter(NcbiMetadata.acc == sample_name)
            .filter(CondensedProfile.taxonomy_id == Taxonomy.id)
            .filter(Taxonomy.taxonomy_type == taxonomy_type)
        ).fetchall()
    if len(condensed) == 0:
        return jsonify({ 'no_data': True, 'sample_name': sample_name })

    for entry in condensed:
        taxons = entry.full_name.split('; ')

        last_taxon = root
        wn = None
        for (i, tax) in enumerate(taxons):
            if tax not in taxons_to_wordnode:
                wn = WordNode(last_taxon, tax)
                last_taxon.children[tax] = wn
                taxons_to_wordnode[tax] = wn #TODO: Problem when there is non-unique labels? Require full taxonomy used?
            last_taxon = taxons_to_wordnode[tax]
        last_taxon.coverage = entry.coverage

    return jsonify({ 'condensed': wordnode_json(root, 0, 0), 'sample_name': sample_name })

@api.route('/condensed_csv/<string:sample_name>', methods=('GET',))
def fetch_condensed_csv(sample_name):
    taxonomy_type = request.args.get('taxonomy_type', 'gtdb')
    condensed = db.session.execute(
        select(CondensedProfile.coverage, Taxonomy.full_name, Taxonomy.taxonomy_level)
            .join(CondensedProfile.ncbi_metadata)
            .filter(NcbiMetadata.acc == sample_name)
            .filter(CondensedProfile.taxonomy_id == Taxonomy.id)
            .filter(Taxonomy.taxonomy_type == taxonomy_type)
            .filter(CondensedProfile.coverage > 0)
        ).fetchall()
    if len(condensed) is None:
        return jsonify({ sample_name: 'no condensed data found' })
    
    # Sort df by taxonomy level. Since they are strings, we convert to int first
    level_to_int = {
        'domain': 1,
        'phylum': 2,
        'class': 3,
        'order': 4,
        'family': 5,
        'genus': 6,
        'species': 7,
    }
    df = pl.DataFrame(
        [[
            sample_name,
            d.coverage,
            'Root; '+d.full_name if d.full_name != 'Root' else d.full_name,
            level_to_int[d.taxonomy_level]
        ] for d in condensed],
        orient="row",
        schema=['sample', 'coverage', 'taxonomy', 'taxonomy_level_int']
    ).sort( # sort by taxonomy level_int first, then coverage descending
        ['taxonomy_level_int', 'coverage'], descending=[False, True]).select(['sample', 'coverage', 'taxonomy'])
    
    response = make_response(df.write_csv(separator='\t'))
    cd = 'attachment; filename=sandpiper_v{}_{}_{}_condensed.csv'.format(__version__, sample_name, taxonomy_type)
    response.headers['Content-Disposition'] = cd
    response.mimetype = 'text/csv'
    return response

@api.route('/condensed_csv_with_extras/<string:sample_name>', methods=('GET',))
def fetch_condensed_csv_with_extras(sample_name):
    # TODO: remove duplication with above?
    taxonomy_type = request.args.get('taxonomy_type', 'gtdb')
    condensed = db.session.execute(
        select(CondensedProfile.coverage, Taxonomy.full_name, Taxonomy.taxonomy_level)
            .join(CondensedProfile.ncbi_metadata)
            .filter(NcbiMetadata.acc == sample_name)
            .filter(CondensedProfile.taxonomy_id == Taxonomy.id)
            .filter(Taxonomy.taxonomy_type == taxonomy_type)
            .filter(CondensedProfile.coverage > 0) # zeroes are introduced later, so this filter makes no difference
        ).fetchall()
    if len(condensed) is None:
        return jsonify({ sample_name: 'no condensed data found' })

    # Use the Summarise.write_taxonomic_profile_with_extras function logic to implement
    df = pl.DataFrame(
        [[
            sample_name,
            d.coverage,
            'Root; '+d.full_name if d.full_name != 'Root' else d.full_name,
        ] for d in condensed],
        orient="row",
        schema=['sample', 'coverage', 'taxonomy']
    )
    # write_taxonomic_profile_with_extras takes a list of input files, so we
    # need to simulate that by writing our df to a temp file first. The output
    # will be also be a file, so create a temp file for that too.
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w+', delete=True) as input_tempfile, tempfile.NamedTemporaryFile(mode='r+', delete=True) as output_tempfile:
        df.write_csv(input_tempfile.name, separator='\t')
        input_taxonomic_profile_files = [input_tempfile.name]
        Summariser.write_taxonomic_profile_with_extras(
            input_taxonomic_profile_files=input_taxonomic_profile_files,
            output_taxonomic_profile_extras_io=output_tempfile,
            num_decimal_places=2, # As of 0.20.2, defaulting to 2 fails
        )
        output_tempfile.seek(0)
        response = make_response(output_tempfile.read())
        cd = 'attachment; filename=sandpiper_v{}_{}_{}_condensed_with_extras.csv'.format(__version__, sample_name, taxonomy_type)
        response.headers['Content-Disposition'] = cd
        response.mimetype = 'text/csv'
        return response


@api.route('/indicpiper_csv/<string:sample_name>', methods=('GET',))
def fetch_indicpiper_csv(sample_name):
    """This run's own IndicPiper habitat/genus breakdown as a downloadable
    CSV -- the same genus-level detail IndicPiperHabitatChart.vue renders,
    one row per (habitat, genus). Bounded to a single run, so built in
    memory like fetch_condensed_csv above, not streamed like the bulk
    /indicpiper_results_csv endpoint.
    """
    rows = []
    has_indval = False
    if _indicator_habitat_genus_scores_exists():
        has_indval = _indicator_habitat_genus_scores_has_indval()
        genus_columns = [
            IndicatorHabitatGenusScore.genus,
            IndicatorHabitatGenusScore.relative_abundance,
        ]
        if has_indval:
            genus_columns += [
                IndicatorHabitatGenusScore.ind_val_mean,
                IndicatorHabitatGenusScore.p_val_mean,
            ]
        rows = db.session.execute(
            select(
                IndicatorHabitatScore.habitat,
                IndicatorHabitatScore.score,
                *genus_columns,
            )
            .join(NcbiMetadata, NcbiMetadata.id == IndicatorHabitatScore.run_id)
            .join(
                IndicatorHabitatGenusScore,
                and_(
                    IndicatorHabitatGenusScore.run_id == IndicatorHabitatScore.run_id,
                    IndicatorHabitatGenusScore.habitat == IndicatorHabitatScore.habitat,
                ),
            )
            .where(NcbiMetadata.acc == sample_name)
            .order_by(IndicatorHabitatScore.score.desc(), IndicatorHabitatGenusScore.relative_abundance.desc())
        ).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    header = ['habitat', 'score', 'genus', 'relative_abundance']
    if has_indval:
        header += ['ind_val_mean', 'p_val_mean']
    writer.writerow(header)
    for r in rows:
        row = [r.habitat, r.score, r.genus, r.relative_abundance]
        if has_indval:
            row += [r.ind_val_mean, r.p_val_mean]
        writer.writerow(row)

    response = make_response(buffer.getvalue())
    cd = 'attachment; filename=sandpiper_v{}_{}_indicpiper.csv'.format(__version__, sample_name)
    response.headers['Content-Disposition'] = cd
    response.mimetype = 'text/csv'
    return response


@api.route('/metalog_csv/<string:sample_name>', methods=('GET',))
def fetch_metalog_csv(sample_name):
    """This run's own Metalog record as a downloadable single-row CSV.
    Unlike the bulk /metalog_results_csv (which has to keep every meta_*
    column so every run's row lines up under the same header), this is
    narrowed to only the columns actually populated for this run -- no
    empty/NaN columns -- since it's a single row and there's no shared
    header to keep consistent. Column set matches RunMetadata.vue's
    Metalog section, which is driven by the same "populated only" rule
    (see ParsedSampleAttribute.metalog_rows() in models.py).
    """
    meta_columns = [r[0] for r in db.session.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'parsed_sample_attributes' AND starts_with(column_name, 'meta_') "
        "ORDER BY column_name"
    ))]
    if not meta_columns:
        return jsonify({'error': 'No Metalog metadata available in this database.'}), 404

    row = db.session.execute(text(
        "SELECT nm.acc AS acc, {select_list} "
        "FROM parsed_sample_attributes psa "
        "JOIN ncbi_metadata nm ON nm.id = psa.run_id "
        "WHERE nm.acc = :acc".format(
            select_list=', '.join('psa."{}"'.format(c) for c in meta_columns))
    ), {'acc': sample_name}).fetchone()

    if row is None:
        return jsonify({'error': 'No Metalog metadata recorded for {}.'.format(sample_name)}), 404

    populated = [(c, v) for c, v in zip(meta_columns, row[1:])
                 if v is not None and str(v).strip() != '']
    if not populated:
        return jsonify({'error': 'No Metalog metadata recorded for {}.'.format(sample_name)}), 404

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Run'] + [c for c, _ in populated])
    writer.writerow([row.acc] + [v for _, v in populated])

    response = make_response(buffer.getvalue())
    cd = 'attachment; filename=sandpiper_v{}_{}_metalog.csv'.format(__version__, sample_name)
    response.headers['Content-Disposition'] = cd
    response.mimetype = 'text/csv'
    return response


def wordnode_json(wordnode, order, depth):
    r = re.compile('^.__(.+)')
    matches = r.match(wordnode.word)
    if matches is None:
        name = wordnode.word
    else:
        name = matches.group(1)
    j = {
        'name': '' if name == 'Root' else name,
        'size': wordnode.coverage,
        'order': order,
        'condensed_depth': depth,
    }
    # Sort children descending by coverage so more abundance lineages are first
    sorted_children = sorted(wordnode.children.values(), key=lambda x: x.get_full_coverage(), reverse=True)
    if len(wordnode.children.values()) > 0:
        j['children'] = [wordnode_json(child, order+i, depth+1) for i, child in enumerate(sorted_children)]
    return j

def _read_length_summary(read1_length_average, read2_length_average):
    if read1_length_average is not None and read2_length_average is not None:
        return '%.0fx%.0fbp reads' % (read1_length_average, read2_length_average)
    if read1_length_average is not None:
        return '%.0fbp reads' % read1_length_average
    return None


@api.route('/metadata/<string:sample_name>', methods=('GET',))
def fetch_metadata(sample_name):
    global biosample_attribute_definitions, ncbi_metadata_infos

    # Doesn't usually cache anything, but useful to have here for testing
    generate_cache()

    metadata = NcbiMetadata.query.filter_by(acc=sample_name).all()
    if metadata == [] or metadata is None:
        return jsonify({ "error": 'No metadata found for '+sample_name+'. This likely means that this run was not included when the list of runs to analyse was gathered ('+__scrape_date__+').' })
    meta = metadata[0]

    metadata_dict = meta.to_displayable_dict()

    host_mature = metadata_dict['parsed_sample_attributes']['host_or_not_mature']
    if host_mature == 'host':
        host_mature = 'Eukaryote host-associated'
    
    metadata_parsed = {
        'mbases': round(metadata_dict['bases']/1e6),
        'spots': metadata_dict['spots'],
        'organism': metadata_dict['taxon_name'],
        'instrument': metadata_dict['model'],
        'collection_time': metadata_dict['parsed_sample_attributes']['collection_year'],
        'release_month': meta.published.strftime('%Y'),
        'latitude': metadata_dict['parsed_sample_attributes']['latitude'],
        'longitude': metadata_dict['parsed_sample_attributes']['longitude'],
        'num_related_runs': related_run_count(meta.bioproject)-1,
        'host_or_not_mature': host_mature,
        'smf': round(metadata_dict['parsed_sample_attributes']['smf']),
        'smf_warning': metadata_dict['parsed_sample_attributes']['smf_warning'],
        'low_complexity': metadata_dict['parsed_sample_attributes']['low_complexity'],
        'top1_order_fraction': metadata_dict['parsed_sample_attributes']['top1_order_fraction'],
        'known_species_fraction': round(metadata_dict['parsed_sample_attributes']['known_species_fraction']*100),
        'globdb_known_species_fraction': (
            round(metadata_dict['parsed_sample_attributes']['globdb_known_species_fraction'] * 100)
            if metadata_dict['parsed_sample_attributes']['globdb_known_species_fraction'] is not None
            else None
        ),
        'non_metagenome_organism_strict': metadata_dict['parsed_sample_attributes']['non_metagenome_organism_strict'],
        'non_metagenome_organism_loose': metadata_dict['parsed_sample_attributes']['non_metagenome_organism_loose'],
        'synthetic': metadata_dict['parsed_sample_attributes']['synthetic'],
        'rna_or_non_dna_strict': metadata_dict['parsed_sample_attributes']['rna_or_non_dna_strict'],
        'rna_or_non_dna_loose': metadata_dict['parsed_sample_attributes']['rna_or_non_dna_loose'],
        'domain_only_gtdb': metadata_dict['parsed_sample_attributes']['domain_only_gtdb'],
        'domain_only_globdb': metadata_dict['parsed_sample_attributes']['domain_only_globdb'],
        'domain_only_both': metadata_dict['parsed_sample_attributes']['domain_only_both'],
        'sample_name': metadata_dict['sample_name'],
        'study_title': metadata_dict['study_title'],
        'bioproject': metadata_dict['bioproject'],
        'study_abstract': metadata_dict['study_abstract'],
    }

    metadata_parsed['read_length_summary'] = _read_length_summary(
        meta.read1_length_average, meta.read2_length_average
    )

    # Change format to be classification => [[name, description], [name, description], ..]
    # for fields that are known already
    d2 = {}
    basic_metadata_metadata = {}
    for info in ncbi_metadata_infos.values():
        basic_metadata_metadata[info.name] = info
        basic_metadata_metadata[info.name.replace('_', ' ')] = info
        basic_metadata_metadata[info.name.replace(' ', '_')] = info

    def add_annotation(k, v):
        if v is None or str(v).lower().strip() in ACTUALLY_MISSING:
            # Do not display missing / fake data
            return
        if k in basic_metadata_metadata:
            info = basic_metadata_metadata[k]
            to_add = {
                'k': basic_metadata_metadata[k].nice_name,
                'v': v,
                'description': basic_metadata_metadata[k].description,
                'is_custom': False,
                'raw_k': k}
            if info.classification in d2:
                d2[info.classification].append(to_add)
            else:
                d2[info.classification] = [to_add]
        else:
            to_add = {
                'k': k.replace('_', ' '),
                'v': v,
                'description': None,
                'is_custom': True,
                'raw_k': k}
            # by default, associate with sample
            if SAMPLE_INFO_TYPE_METADATA not in d2:
                d2[SAMPLE_INFO_TYPE_METADATA] = []
            d2[SAMPLE_INFO_TYPE_METADATA].append(to_add)

    for k, v in metadata_dict.items():
        # metalog_metadata is already in display-row form and has its own
        # section; without this it falls through to add_annotation() and gets
        # rendered as a single custom "metalog metadata" row in Sample
        # information, with the whole array as its value.
        if k in ['acc', 'biosample_attributes', 'study_links', 'parsed_sample_attributes', 'study_title', 'study_abstract', 'metalog_metadata']:
            continue
        add_annotation(k, v)

    # Give the biosample attributes a more friendly name, and annotate them as
    # being custom or not.
    biosample_dict = []
    sam_regex = re.compile(r'_sam$')

    for bs in metadata_dict['biosample_attributes']:
        k_original = bs['k']
        k = sam_regex.sub('', k_original)
        v = bs['v']

        if k_original in ['Gbp', 'run_size', 'study_links']: continue # This is a duplicate of mbases / spots
        # study_links is a temperorary fix

        if v is None or str(v).lower().strip() in ACTUALLY_MISSING:
            # Do not display missing / fake data
            continue

        # Some attributes repeat a database column (e.g. "sample name"); show
        # the value once.
        if is_already_shown(d2.values(), k, v):
            continue

        if k in biosample_attribute_definitions:
            biosample_dict.append({ 
                'k': biosample_attribute_definitions[k].name, 
                'v': v,
                'is_custom': False,
                'raw_k': k,
                'description': biosample_attribute_definitions[k].description })
        else:
            # Submitters can upload custom attributes
            add_annotation(k, v)

    if SAMPLE_INFO_TYPE_METADATA not in d2:
        d2[SAMPLE_INFO_TYPE_METADATA] = []
    d2[SAMPLE_INFO_TYPE_METADATA].extend(biosample_dict)

    # Inject computed complexity fractions into sequencing metadata
    if SEQUENCING_TYPE_METADATA not in d2:
        d2[SEQUENCING_TYPE_METADATA] = []
    top1 = metadata_dict['parsed_sample_attributes']['top1_order_fraction']
    if top1 is not None:
        d2[SEQUENCING_TYPE_METADATA].append({
            'k': 'top order fraction',
            'v': f'{top1:.2f}%',
            'is_custom': False,
            'description': 'Fraction of prokaryotic reads assigned to the single most abundant order. Samples where ≥95% of the community is assigned to a single order are flagged as low complexity and are less likely to represent true microbial communities they may be SAGs, negative controls, or isolate genomic data mistakenly deposited as metagenomic.'
        })

    # Some are double e.g. https://sandpiper.qut.edu.au/run/SRR9224309 has 2 PubMed study_links
    final_study_links = []
    # print("Study links from dict: {}".format(metadata_dict['study_links']))
    for study_link_pair in metadata_dict['study_links']:
        if 'database' in study_link_pair:
            db = study_link_pair['database']
            study_id = study_link_pair['study_id']
            if db == 'ePubmed': db = 'pubmed'
            if db == 'eDOI': db = 'DOI'
            new_link = {
                'database': db,
                'study_id': study_id,
            }
            if new_link not in final_study_links:
                final_study_links.append(new_link)
        else:
            # label / url type
            if study_link_pair not in final_study_links:
                final_study_links.append(study_link_pair)
    d2['study_links'] = final_study_links

    # Order the values in each classification dict in alphabetical order
    for k, v in d2.items():
        if len(v) > 0 and 'k' in v[0]: # don't sort e.g. study_links
            d2[k] = sorted(v, key=lambda x: x['k'].lower())

    # Metalog extended metadata. Already sorted and filtered to populated
    # fields by metalog_rows(); added after the sort above since it is built
    # in display form rather than from a classification.
    d2['metalog_metadata'] = metadata_dict['metalog_metadata']

    # How much of this run's information the rest of its BioProject shares.
    # Each row is tagged `difference`: 'only_here' (no other run has the
    # field), 'differs' (a value other runs do not share) or 'expected' (an
    # identifier-like field that differs by design). Metalog rows are compared
    # too, under a prefixed key (see metalog_comparable_values).
    displayed_keys = {row['raw_k'] for rows in d2.values() for row in rows if isinstance(row, dict) and 'raw_k' in row}
    displayed_keys |= {METALOG_PREFIX + row['k'] for row in d2['metalog_metadata']}
    similarity = bioproject_similarity(meta, displayed_keys)
    for rows in d2.values():
        for row in rows:
            if isinstance(row, dict):
                difference = row_difference(row.pop('raw_k', None), similarity)
                if difference:
                    row['difference'] = difference
    for row in d2['metalog_metadata']:
        difference = row_difference(METALOG_PREFIX + row['k'], similarity)
        if difference:
            row['difference'] = difference
    metadata_parsed['bioproject_similarity'] = similarity

    d2['metalog_retrieved_date'] = metalog_retrieved_date()
    d2['metalog_release'] = metalog_release()

    # IndicPiper habitat-indicator scores. Same "built in display form, added
    # after the classification sort" treatment as metalog_metadata above --
    # see indicpiper_rows()'s docstring for why most runs only have a few rows.
    d2['indicpiper_scores'] = indicpiper_rows(meta.id)
    d2['indicpiper_version'] = __indicpiper_version__

    return jsonify({ 
        'metadata': d2,
        'metadata_parsed': metadata_parsed})

def taxonomy_search_fail_json(reason):
    return jsonify({ 'taxon': reason })


def canonical_taxon_name(taxon):
    """The stored spelling of a taxon name, matched ignoring case, so
    /taxonomy/C__bog-38 finds c__Bog-38. Safe because no two taxa differ only
    by case (checked over all 745,836 GTDB + GlobDB names). Unknown names are
    returned unchanged, so the usual "not found" handling still applies."""
    name = db.session.execute(
        select(Taxonomy.name).where(func.lower(Taxonomy.name) == taxon.lower()).limit(1)).scalar()
    return name or taxon


def taxonomy_types_for_name(taxon):
    return db.session.execute(
        select(distinct(Taxonomy.taxonomy_type)).where(Taxonomy.name == taxon)
    ).scalars().all()


def taxonomy_not_found_response(taxon):
    taxonomy_types = taxonomy_types_for_name(taxon)
    if len(taxonomy_types) == 0:
        reason = f'"{taxon}" is not a known taxonomy in Sandpiper, suggesting it is not known in GTDB or GlobDB either.'
    else:
        reason = (
            f'"{taxon}" is a known taxonomy, but no samples containing it were found. '
            f'It is a valid taxonomy in: {", ".join(sorted(taxonomy_types))}.'
        )
    return taxonomy_search_fail_json(reason)

@api.route('/taxonomy_search_global_data/<string:taxon>', methods=('GET',))
def taxonomy_search_global_data(taxon):
    taxon = canonical_taxon_name(taxon)
    taxonomy_type = request.args.get('taxonomy_type', 'gtdb')
    taxonomy = Taxonomy.query.filter_by(name=taxon, taxonomy_type=taxonomy_type).first()
    if taxonomy is None:
        return taxonomy_not_found_response(taxon)
    total_num_hits = CondensedProfileCtas1.query.filter_by(taxonomy_id=taxonomy.id).count()
    if total_num_hits == 0:
        # This happens when there's a taxonomy in the full table that didn't make it into any condensed table
        return taxonomy_not_found_response(taxon)
    if request.args.get('count_only') == 'true':
        # Availability probe (is this taxon in the other database?): skip the
        # map markers and cluster counts below.
        return jsonify({'total_num_results': total_num_hits})
    num_host_runs = taxonomy.host_sample_count
    num_ecological_runs = taxonomy.ecological_sample_count
    # lat_lons are commented out for now because it is too slow to query and
    # render. SQL needs better querying i.e. in batch, and multiple
    # annotations at a single location need to be collapsed.
    # Optional map-cluster filter -- same construction as
    # taxonomy_search_core's cluster_filters, so a click on the summary map's
    # cluster actually restricts the Individual Runs map (and its caption
    # text below) to that cluster too, not just the paginated table. Without
    # this, clicking a cluster only panned/zoomed the Individual Runs map to
    # that location while it kept showing (and describing) every marker.
    cluster_lat = request.args.get('cluster_lat')
    cluster_lon = request.args.get('cluster_lon')
    cluster_filters = []
    if cluster_lat is not None and cluster_lon is not None:
        try:
            precision = max(0, min(2, int(request.args.get('cluster_precision', 1))))
            cluster_filters = [
                func.round(ParsedSampleAttribute.latitude, precision) == float(cluster_lat),
                func.round(ParsedSampleAttribute.longitude, precision) == float(cluster_lon),
            ]
        except (TypeError, ValueError):
            cluster_filters = []

    lat_lons, lat_lons_count, min_lat_lon_relabund = get_lat_lons(
        taxonomy.id, 1000, cluster_filters)

    # total_num_results feeds the "Matching Samples" summary count and the "N
    # other runs are not shown" caption -- both need to reflect the active
    # cluster filter, not the taxon's full unfiltered count, otherwise those
    # numbers contradict what the filtered map/table actually show.
    if cluster_filters:
        count_query = select(func.count()).select_from(
            CondensedProfileCtas1
        ).join(NcbiMetadata, CondensedProfileCtas1.run_id == NcbiMetadata.id
        ).join(ParsedSampleAttribute, ParsedSampleAttribute.run_id == NcbiMetadata.id
        ).where(CondensedProfileCtas1.taxonomy_id == taxonomy.id)
        for condition in cluster_filters:
            count_query = count_query.where(condition)
        total_num_results = db.session.execute(count_query).scalar()
    else:
        total_num_results = total_num_hits

    return jsonify({
        'total_num_results': total_num_results,
        'taxon_name': taxonomy.name.split('__')[-1],
        'lineage': taxonomy.split_taxonomy(),
        'taxonomy_level': taxonomy.taxonomy_level,
        'lat_lons': lat_lons,
        'lat_lons_min_relabund': min_lat_lon_relabund,
        'num_lat_lon_runs': lat_lons_count,
        'num_host_runs': num_host_runs,
        'num_ecological_runs': num_ecological_runs,
    })

# sort_field=${sortField}&sort_direction=${sortDirection}&page=${page
@api.route('/taxonomy_search_run_data/<string:taxon>', methods=('GET',))
def taxonomy_search_run_data(taxon):
    exclude_low_complexity = request.args.get('exclude_low_complexity') == 'true'
    worked, condensed_profile_hits, filtered_total = taxonomy_search_core(
        taxon, request.args, exclude_low_complexity=exclude_low_complexity
    )

    if worked:
        return jsonify({
            'results': {
                'condensed_profiles': [{
                    'sample_acc': c.acc,
                    'relative_abundance': round(c.relative_abundance*100,2),
                    'coverage': round(c.filled_coverage, 2),
                    'organism': "unspecified" if c.taxon_name is None else c.taxon_name.replace(' metagenome',''),
                    'release_year': c.published.strftime('%Y'),
                    'top1_order_fraction': round(c.top1_order_fraction, 2) if c.top1_order_fraction is not None else None,}
                    for c in condensed_profile_hits],
                'filtered_total': filtered_total,
            }
        })
    else:
        return condensed_profile_hits

@api.route('/taxonomy_search_csv/<string:taxon>', methods=('GET',))
def taxonomy_search_csv(taxon):
    taxonomy_type = request.args.get('taxonomy_type', 'gtdb')
    from datetime import datetime
    print('=== {}: running core'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    worked, condensed_profile_hits, _ = taxonomy_search_core(
        taxon, request.args, no_limit=True, include_extras=True, return_open_cursor=True,
        exclude_low_complexity=request.args.get('exclude_low_complexity') == 'true'
    )
    print('=== {}: after core'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    if worked:
        print('=== {}: worked core'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        headers = [
            'sample', 'relative_abundance', 'coverage', 'taxon_name', 'study_title', 'release_year',
            'metagenome_base_pairs', 'bacterial_archaeal_bases',
            'eukaryotic_host_association', 'num_reads', 'read_length_summary', 'sequencing_instrument', 'collection_year',
            'spf', 'spf_warning',
            'gtdb_known_species_fraction_percent', 'globdb_known_species_fraction_percent',
            'latitude', 'longitude', 'top1_order_fraction_percent', 'low_complexity'
        ]

        def generate_csv_rows():
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(headers)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

            try:
                while True:
                    chunk = condensed_profile_hits.fetchmany(1000)
                    if not chunk:
                        break
                    for c in chunk:
                        writer.writerow([
                            c.acc,
                            round(c.relative_abundance * 100, 2),
                            round(c.filled_coverage, 2),
                            c.taxon_name,
                            c.study_title,
                            c.published.strftime('%Y'),
                            c.bases,
                            c.bacterial_archaeal_bases,
                            c.host_or_not_mature,
                            c.spots,
                            _read_length_summary(c.read1_length_average, c.read2_length_average),
                            c.model,
                            c.collection_year,
                            round(c.smf, 2) if c.smf is not None else None,
                            c.smf_warning,
                            round(c.known_species_fraction * 100, 2)
                            if c.known_species_fraction is not None
                            else None,
                            round(c.globdb_known_species_fraction * 100, 2)
                            if c.globdb_known_species_fraction is not None
                            else None,
                            c.latitude,
                            c.longitude,
                            f'{round(c.top1_order_fraction)}%' if c.top1_order_fraction is not None else None,
                            c.low_complexity,
                        ])
                    yield buffer.getvalue()
                    buffer.seek(0)
                    buffer.truncate(0)
            finally:
                condensed_profile_hits.close()

        response = Response(stream_with_context(generate_csv_rows()), mimetype='text/csv')
        cd = 'attachment; filename=sandpiper_v{}_{}_{}_sample_coverage.csv'.format(__version__, taxon, taxonomy_type)
        response.headers['Content-Disposition'] = cd
        return response
    else:
        return condensed_profile_hits # Really returning a JSON indicating the failure


@api.route('/taxonomy_search_csv_minimal/<string:taxon>', methods=('GET',))
def taxonomy_search_csv_minimal(taxon):
    taxonomy_type = request.args.get('taxonomy_type', 'gtdb')
    worked, condensed_profile_hits, _ = taxonomy_search_core(
        taxon, request.args, no_limit=True, include_extras=False, return_open_cursor=True,
        exclude_low_complexity=request.args.get('exclude_low_complexity') == 'true'
    )

    if worked:
        headers = [
            'run', 'environment', 'release_year', 'relative_abundance_percent', 'coverage', 'low_complexity'
        ]

        def generate_csv_rows():
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(headers)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

            try:
                while True:
                    chunk = condensed_profile_hits.fetchmany(1000)
                    if not chunk:
                        break
                    for c in chunk:
                        environment = (
                            "unspecified"
                            if c.taxon_name is None
                            else c.taxon_name.replace(' metagenome', '')
                        )
                        release_year = c.published.strftime('%Y') if c.published else None
                        writer.writerow([
                            c.acc,
                            environment,
                            release_year,
                            round(c.relative_abundance * 100, 2),
                            round(c.filled_coverage, 2),
                            c.low_complexity,
                        ])
                    yield buffer.getvalue()
                    buffer.seek(0)
                    buffer.truncate(0)
            finally:
                condensed_profile_hits.close()

        response = Response(stream_with_context(generate_csv_rows()), mimetype='text/csv')
        cd = 'attachment; filename=sandpiper_v{}_{}_{}_runs.csv'.format(
            __version__, taxon, taxonomy_type
        )
        response.headers['Content-Disposition'] = cd
        return response
    else:
        return condensed_profile_hits # Really returning a JSON indicating the failure


class _OpenCursorWrapper:
    def __init__(self, connection, result):
        self.connection = connection
        self.result = result

    def fetchmany(self, size=None):
        return self.result.fetchmany(size)

    def close(self):
        self.result.close()
        self.connection.close()


def taxonomy_search_core(
    taxon, args, no_limit=False, include_extras=False, return_open_cursor=False, exclude_low_complexity=False
):
    '''Returns (bool, iterable|json) where bool is whether it worked (True)
    or not (False) and iterable is the data to render. json is the error if
    it failed.'''
    taxon = canonical_taxon_name(taxon)

    sort_field = args.get('sort_field')
    sort_direction = args.get('sort_direction')
    page = args.get('page')
    page_size = args.get('page_size')
    taxonomy_type = args.get('taxonomy_type', 'gtdb')
    sort_field = 'relative_abundance' if sort_field is None else sort_field
    sort_direction = 'desc' if sort_direction is None else sort_direction
    page = int(page) if page is not None else 0
    page_size = int(page_size) if page_size is not None else 100

    sort_columns = {
        'relative_abundance': CondensedProfileCtas1.relative_abundance,
        'coverage': CondensedProfileCtas1.filled_coverage,
        'release_year': NcbiMetadata.published,
        'top1_order_fraction': ParsedSampleAttribute.top1_order_fraction,
        'organism': NcbiMetadata.taxon_name,
    }
    if sort_field not in sort_columns:
        return False, jsonify({ 'error': 'invalid sort field' }), None
    if sort_direction not in ['asc', 'desc']:
        return False, jsonify({ 'error': 'invalid sort direction' }), None

    taxonomy = Taxonomy.query.filter_by(name=taxon, taxonomy_type=taxonomy_type).first()
    if taxonomy is None:
        return False, taxonomy_not_found_response(taxon), None
    else:
        total_num_hits = CondensedProfileCtas1.query.filter_by(taxonomy_id=taxonomy.id).count()
        if total_num_hits == 0:
            return False, taxonomy_not_found_response(taxon), None
        # Query for samples that contain this taxon
        if include_extras:
            stmt = select(
                NcbiMetadata.acc,
                CondensedProfileCtas1.relative_abundance,
                CondensedProfileCtas1.filled_coverage,
                NcbiMetadata.taxon_name,
                NcbiMetadata.study_title,
                NcbiMetadata.published,
                ParsedSampleAttribute.host_or_not_mature,
                ParsedSampleAttribute.latitude,
                ParsedSampleAttribute.longitude,
                NcbiMetadata.bases,
                ParsedSampleAttribute.bacterial_archaeal_bases,
                NcbiMetadata.spots,
                NcbiMetadata.read1_length_average,
                NcbiMetadata.read2_length_average,
                NcbiMetadata.model,
                ParsedSampleAttribute.collection_year,
                ParsedSampleAttribute.smf,
                ParsedSampleAttribute.smf_warning,
                ParsedSampleAttribute.known_species_fraction,
                ParsedSampleAttribute.globdb_known_species_fraction,
                ParsedSampleAttribute.top1_order_fraction,
                ParsedSampleAttribute.low_complexity,
            ).where(CondensedProfileCtas1.run_id == NcbiMetadata.id
            ).where(ParsedSampleAttribute.run_id == NcbiMetadata.id)
        else:
            stmt = select(
                NcbiMetadata.acc,
                CondensedProfileCtas1.relative_abundance,
                CondensedProfileCtas1.filled_coverage,
                NcbiMetadata.taxon_name,
                NcbiMetadata.published,
                ParsedSampleAttribute.top1_order_fraction,
                ParsedSampleAttribute.low_complexity,
                # TODO: Add experiment title here, not currently in DB
            ).where(CondensedProfileCtas1.run_id == NcbiMetadata.id
            ).where(ParsedSampleAttribute.run_id == NcbiMetadata.id)

        
        column = sort_columns[sort_field]
        order = column.desc().nulls_last() if sort_direction == 'desc' else column.asc().nulls_last()
        # The run accession breaks ties so paging through equal values is stable.
        hits_query = stmt.order_by(order, NcbiMetadata.acc)

        hits_query = hits_query.where(CondensedProfileCtas1.taxonomy_id == taxonomy.id)

        # Optional map-cluster filter. The summary map groups samples by
        # rounded coordinates, so clicking a circle restricts the run list to
        # exactly the samples that circle represents. Applied here rather than
        # client-side because this table is paginated server-side -- filtering
        # a single page would leave the other pages unfiltered.
        cluster_lat = args.get('cluster_lat')
        cluster_lon = args.get('cluster_lon')
        cluster_filters = []
        if cluster_lat is not None and cluster_lon is not None:
            try:
                precision = max(0, min(2, int(args.get('cluster_precision', 1))))
                cluster_filters = [
                    func.round(ParsedSampleAttribute.latitude, precision) == float(cluster_lat),
                    func.round(ParsedSampleAttribute.longitude, precision) == float(cluster_lon),
                ]
            except (TypeError, ValueError):
                cluster_filters = []
        for condition in cluster_filters:
            hits_query = hits_query.where(condition)

        if exclude_low_complexity:
            hits_query = hits_query.where(ParsedSampleAttribute.low_complexity != 'yes')

        # Pagination needs a total that reflects every active filter, otherwise
        # the pager offers pages that are empty.
        if exclude_low_complexity or cluster_filters:
            count_query = select(func.count()).select_from(
                CondensedProfileCtas1
            ).join(NcbiMetadata, CondensedProfileCtas1.run_id == NcbiMetadata.id
            ).join(ParsedSampleAttribute, ParsedSampleAttribute.run_id == NcbiMetadata.id
            ).where(CondensedProfileCtas1.taxonomy_id == taxonomy.id)
            if exclude_low_complexity:
                count_query = count_query.where(ParsedSampleAttribute.low_complexity != 'yes')
            for condition in cluster_filters:
                count_query = count_query.where(condition)
            filtered_total = db.session.execute(count_query).scalar()
        else:
            filtered_total = None

        if not no_limit:
            hits_query = hits_query.limit(page_size).offset((page-1)*page_size)

        if no_limit or return_open_cursor:
            hits_query = hits_query.execution_options(stream_results=True)

        if return_open_cursor:
            connection = db.engine.connect()
            condensed_profile_hits = connection.execute(hits_query)
            return True, _OpenCursorWrapper(connection, condensed_profile_hits), filtered_total

        condensed_profile_hits = db.session.execute(hits_query)

        return True, condensed_profile_hits, filtered_total


@api.route('/taxonomy_search_hints/<string:taxon>', methods=('GET',))
def taxonomy_search_hints(taxon):
    if len(taxon) < 3: return jsonify(['3 or more characters are required'])
    taxonomy_type = request.args.get('taxonomy_type', None)

    # Underscores are wildcards, but we don't want that since there are names like p__Actinobacteria
    search = '%'+taxon.lower().replace('_','\\_')+'%'
    if taxonomy_type is None:
        sql = (
            "select name from taxonomies "
            "where lower(name) like :taxon escape \'\\' "
            "order by taxonomy_type, name limit 30"
        )
        results = db.session.execute(text(sql), {'taxon': search})
    else:
        sql = (
            "select name from taxonomies where taxonomy_type = :taxonomy_type "
            "and lower(name) like :taxon escape \'\\' order by name limit 30"
        )
        results = db.session.execute(text(sql), {'taxon': search, 'taxonomy_type': taxonomy_type})
    taxonomies = []
    for r in results:
        taxonomies.append(r)
    if len(taxonomies) == 0:
        return jsonify(['no taxonomy found for '+taxon])

    return jsonify({ 'taxonomies': [t.name for t in taxonomies] })

# Universal search bar autocomplete: value suggestions for the
# high-cardinality fields, one query per keystroke (debounced client-side).
# Explicit allowlist -- never let a user-supplied field name choose an
# arbitrary SQL column.
#
# 'organisation' suggests from organisation_institution rather than
# organisation_name: organisation_name is 100% NULL in production
# (sandpiper_40.duckdb has 913,071/913,071 NULL rows), a real BioSample
# metadata gap upstream, not a bug here. organisation_institution is the
# best-populated of the six columns the 'organisation' filter itself
# ORs together (api.py's _apply_filter_for_key, 'organisation' branch) --
# suggestions won't cover every possible match that filter accepts (e.g.
# a city- or contact-name-only match), only the common case.
# Values are trusted, hardcoded NcbiMetadata column names -- never derived
# from the request -- so interpolating them into raw SQL text below is safe;
# only the allowlist KEY (matched against the URL's <field>) comes from the
# caller, and any field not in this dict is rejected before a query runs.
_SUGGESTABLE_FIELDS = {
    'country': 'geo_loc_name',
    'location': 'geo_loc_name',
    'organism': 'taxon_name',
    'organisation': 'organisation_institution',
    'study': 'study_title',
    'bioproject': 'bioproject',
}

@api.route('/search_field_values/<string:field>/<string:query>', methods=('GET',))
def search_field_values(field, query):
    column = _SUGGESTABLE_FIELDS.get(field)
    if column is None:
        return jsonify({'error': f'field "{field}" is not suggestable'}), 400
    if len(query) < 2:
        return jsonify({'values': []})
    search = '%' + query.lower().replace('_', '\\_') + '%'
    # Highest total count first. Because the GROUP BY is on the exact column
    # value (not the search string), this count already is that value's
    # total frequency across the whole table -- free to compute, since it's
    # already needed for the "(N)" suggestion label regardless of sort order.
    sql = (
        f"select {column}, count(*) as n from ncbi_metadata "
        f"where lower({column}) like :search escape '\\' "
        f"group by {column} order by n desc limit 15"
    )
    rows = db.session.execute(text(sql), {'search': search})
    return jsonify({'values': [{'value': r[0], 'count': r[1]} for r in rows if r[0]]})

def get_lat_lons(taxonomy_id, max_to_show, extra_filters=None):
    """Up to max_to_show runs with coordinates, grouped into map markers.

    taxonomy_id=None means no taxon (the search results page): the runs are
    chosen by extra_filters alone and, with no abundance to rank by, ordered
    by accession; the returned minimum relative abundance is then None."""
    if taxonomy_id is None:
        stmt = select(
            NcbiMetadata.acc, ParsedSampleAttribute.latitude, ParsedSampleAttribute.longitude,
            NcbiMetadata.study_title, literal(None)
        ).where(
            NcbiMetadata.id == ParsedSampleAttribute.run_id).where(
            ParsedSampleAttribute.latitude.is_not(None))
        order = (NcbiMetadata.acc,)
    else:
        stmt = select(
            NcbiMetadata.acc, ParsedSampleAttribute.latitude, ParsedSampleAttribute.longitude,
            NcbiMetadata.study_title, CondensedProfileCtas1.relative_abundance
        ).where(
            CondensedProfileCtas1.taxonomy_id == taxonomy_id).where(
            NcbiMetadata.id == ParsedSampleAttribute.run_id).where(
            NcbiMetadata.id == CondensedProfileCtas1.run_id).where(
            ParsedSampleAttribute.latitude.is_not(None))
        order = (CondensedProfileCtas1.relative_abundance.desc(), CondensedProfileCtas1.run_id)
    for condition in (extra_filters or []):
        stmt = stmt.where(condition)
    lat_lon_db_entries = db.session.execute(
        stmt.order_by(*order).limit(max_to_show).distinct()).fetchall()

    lat_lons = {}
    lat_lons_count = 0
    min_lat_lon_relabund = None
    for (sample_name, lat, lon, description, _relabund) in lat_lon_db_entries:
        lat_lons_count += 1
        # Never None: jsonify sorts keys, and None can't be compared with a title.
        description = description or 'Unknown study'
        mykey = '%s %s' % (lat, lon)
        if mykey in lat_lons:
            if description in lat_lons[mykey]['samples']:
                lat_lons[mykey]['samples'][description].append(sample_name)
            else:
                lat_lons[mykey]['samples'][description] = [sample_name]
        else:
            lat_lons[mykey] = {'lat_lon': [lat, lon], 'samples': {description: [sample_name]}}
    if taxonomy_id is None:
        min_lat_lon_relabund = None
    elif len(lat_lon_db_entries) > 0:
        min_lat_lon_relabund = lat_lon_db_entries[-1][4] # sorted by descending, so last one is the min
    else:
        # Currently occurs for
        # http://localhost:8080/taxonomy/s__Nanoarchaeum%20equitans where there
        # are no lat lons for any sample where this taxon is found.
        min_lat_lon_relabund = 0
    return list(lat_lons.values()), lat_lons_count, min_lat_lon_relabund

def map_category(host_or_not):
    """Map legend category for a group of runs, from Sandpiper's own
    host/ecological call."""
    return {'host': 'host_associated', 'ecological': 'ecological'}.get(host_or_not, 'unclassified')


def get_lat_lon_clusters(taxonomy_id, precision=1, extra_filters=None):
    """Sample counts per map cell for one taxon, split by environment category.
    taxonomy_id=None: the runs chosen by extra_filters (search results page).

    Aggregated in the database rather than in Python: a common taxon matches
    hundreds of thousands of runs, and get_lat_lons() caps at 1000 for exactly
    that reason. Grouping by rounded coordinates returns a few thousand cells
    however many runs match, so the whole distribution can be shown rather than
    the top slice by abundance.

    Colour category is sandpiper's own host/ecological classification.

    Deliberately does NOT include per-cell study titles: grouping by
    study_title roughly doubled the row count here (~35k vs ~19k rows for one
    mid-sized taxon) and made up over half the response payload (~2MB of a
    ~3.9MB response), all to back a hover tooltip almost nobody triggers for
    most cells. That's fetched on demand instead, per cell, by
    get_cell_study_titles() below.
    """
    rounded_lat = func.round(ParsedSampleAttribute.latitude, precision)
    rounded_lon = func.round(ParsedSampleAttribute.longitude, precision)

    stmt = select(
        rounded_lat.label('lat'),
        rounded_lon.label('lon'),
        ParsedSampleAttribute.host_or_not_mature,
        func.count().label('n'),
    ).where(
        ParsedSampleAttribute.run_id == NcbiMetadata.id
    ).where(
        ParsedSampleAttribute.latitude.is_not(None)
    ).where(
        ParsedSampleAttribute.longitude.is_not(None)
    )
    if taxonomy_id is not None:
        stmt = stmt.where(
            CondensedProfileCtas1.taxonomy_id == taxonomy_id
        ).where(
            NcbiMetadata.id == CondensedProfileCtas1.run_id
        )
    for condition in (extra_filters or []):
        stmt = stmt.where(condition)

    rows = db.session.execute(
        stmt.group_by(
            rounded_lat, rounded_lon,
            ParsedSampleAttribute.host_or_not_mature,
        )
    ).fetchall()

    cells = {}
    for lat, lon, host_or_not, count in rows:
        category = map_category(host_or_not)
        key = (lat, lon)
        cell = cells.setdefault(key, {'lat': lat, 'lon': lon, 'total': 0, 'categories': {}})
        cell['total'] += count
        cell['categories'][category] = cell['categories'].get(category, 0) + count

    return sorted(cells.values(), key=lambda c: -c['total'])


def get_cell_study_titles(taxonomy_id, lat, lon, precision=1, extra_filters=None):
    """Top 5 study titles for one map cell, by sample count -- the hover
    tooltip content that get_lat_lon_clusters() above deliberately omits from
    the bulk response. taxonomy_id=None: runs chosen by extra_filters alone."""
    rounded_lat = func.round(ParsedSampleAttribute.latitude, precision)
    rounded_lon = func.round(ParsedSampleAttribute.longitude, precision)

    stmt = select(
        NcbiMetadata.study_title, func.count().label('n')
    ).select_from(NcbiMetadata
    ).join(ParsedSampleAttribute, ParsedSampleAttribute.run_id == NcbiMetadata.id)
    if taxonomy_id is not None:
        stmt = stmt.join(CondensedProfileCtas1, CondensedProfileCtas1.run_id == NcbiMetadata.id
        ).where(CondensedProfileCtas1.taxonomy_id == taxonomy_id)
    stmt = stmt.where(rounded_lat == lat
    ).where(rounded_lon == lon
    ).where(NcbiMetadata.study_title.is_not(None))
    for condition in (extra_filters or []):
        stmt = stmt.where(condition)

    rows = db.session.execute(
        stmt.group_by(NcbiMetadata.study_title).order_by(func.count().desc()).limit(5)
    ).fetchall()
    return [{'title': title, 'count': n} for title, n in rows]


@api.route('/taxonomy_map/<string:taxon>', methods=('GET',))
def taxonomy_map(taxon):
    """Aggregated sample distribution for one taxon, for the summary map."""
    taxon = canonical_taxon_name(taxon)
    taxonomy_type = request.args.get('taxonomy_type', 'gtdb')
    try:
        precision = max(0, min(2, int(request.args.get('precision', 1))))
    except ValueError:
        precision = 1

    taxonomy = db.session.execute(
        select(Taxonomy).where(Taxonomy.name == taxon).where(
            Taxonomy.taxonomy_type == taxonomy_type)).scalars().first()
    if taxonomy is None:
        return jsonify({'taxon': taxon, 'cells': [], 'total': 0})

    cells = get_lat_lon_clusters(taxonomy.id, precision)
    return jsonify({
        'taxon': taxon,
        'precision': precision,
        'cells': cells,
        'total': sum(cell['total'] for cell in cells),
    })


@api.route('/taxonomy_map_cell_studies/<string:taxon>', methods=('GET',))
def taxonomy_map_cell_studies(taxon):
    """Study titles for one summary-map cell, fetched on hover rather than
    bundled into every /taxonomy_map response -- see get_cell_study_titles()."""
    taxon = canonical_taxon_name(taxon)
    taxonomy_type = request.args.get('taxonomy_type', 'gtdb')
    try:
        precision = max(0, min(2, int(request.args.get('precision', 1))))
        lat = float(request.args['lat'])
        lon = float(request.args['lon'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'studies': []}), 400

    taxonomy = db.session.execute(
        select(Taxonomy).where(Taxonomy.name == taxon).where(
            Taxonomy.taxonomy_type == taxonomy_type)).scalars().first()
    if taxonomy is None:
        return jsonify({'studies': []})

    studies = get_cell_study_titles(taxonomy.id, lat, lon, precision)
    return jsonify({'studies': studies})


# --- Search results page ("Explore tabled results" on the advanced search) ---
# The taxonomy page's view of every run matching a search-box query. All of
# these filter with parse_universal_query(), exactly as /universal_search
# counts, so the page always describes the runs the search box counted.

QUERY_MAX_MARKERS = 1000
QUERY_MAX_PAGE = 1_000_000
QUERY_SORT_COLUMNS = {
    'sample_acc': NcbiMetadata.acc,
    'organism': NcbiMetadata.taxon_name,
    'release_year': NcbiMetadata.published,
}
# The named taxon's profile row, kept separate from any join the search filter makes.
QueryTaxonProfile = aliased(CondensedProfileCtas1)
# Only when the search names a whole taxon (see _query_taxon).
QUERY_TAXON_SORT_COLUMNS = {
    'relative_abundance': QueryTaxonProfile.relative_abundance,
    'coverage': QueryTaxonProfile.filled_coverage,
}


class BadQuery(Exception):
    pass


@api.errorhandler(BadQuery)
def _bad_query(err):
    return jsonify({'error': str(err)}), 400


MATCH_CACHE = MatchCache()


@api.teardown_request
def _release_match_cache(_exc):
    MATCH_CACHE.release()


def _query_run_filter():
    """[run filter] for ?q=, or None if the query matches nothing."""
    q = request.args.get('q', '').strip()
    if not q:
        raise BadQuery('No query provided')
    parsed = parse_universal_query(q)
    if parsed is None:
        raise BadQuery('No valid conditions parsed')
    if parsed.matches_nothing:
        return None
    def find_matches():
        # Only the taxonomy join can repeat a run, and a repeated id would bloat the stored set.
        return parsed.select(NcbiMetadata.id, distinct=parsed.needs_condensed)
    # The same ?q= is filtered on by the summary, table and map requests of
    # one results page; the text search is done once for all of them.
    matching = MATCH_CACHE.ids_select(q, find_matches, db.session)
    run_filter = [NcbiMetadata.id.in_(matching if matching is not None else find_matches())]
    return run_filter


def _query_runs(run_filter, *columns, taxon_id=None):
    """SELECT columns, one row per matching run, with its parsed attributes.
    taxon_id: also outer-join that one taxon's profile row (QueryTaxonProfile),
    so its abundance can be selected -- NULL where the run lacks it. One row
    per (taxon, run), so this never adds or drops runs."""
    stmt = select(*columns).select_from(NcbiMetadata).outerjoin(
        ParsedSampleAttribute, ParsedSampleAttribute.run_id == NcbiMetadata.id)
    if taxon_id is not None:
        stmt = stmt.outerjoin(QueryTaxonProfile, and_(
            QueryTaxonProfile.run_id == NcbiMetadata.id, QueryTaxonProfile.taxonomy_id == taxon_id))
    for condition in run_filter:
        stmt = stmt.where(condition)
    return stmt


QUERY_TAXON_TYPES = ('gtdb', 'globdb')


def _query_taxon():
    """The taxon named by `taxonomy:` in ?q= when it is a whole taxon name (any
    case): {'name', 'ids': {taxonomy_type: id}}. None otherwise -- a partial
    name matches many taxa, so there is no single abundance to show."""
    for part in split_query_parts(request.args.get('q', '')):
        match = re.match(r'^(\w[\w\s]*?)\s*:\s*(.*)$', part)
        if not match or match.group(1).lower().strip() != 'taxonomy':
            continue
        value = unquote(match.group(2))
        if not value:
            return None
        rows = db.session.execute(
            select(Taxonomy.id, Taxonomy.name, Taxonomy.taxonomy_type)
            .where(func.lower(Taxonomy.name) == value.lower())).fetchall()
        if not rows:
            return None
        return {'name': rows[0].name, 'ids': {r.taxonomy_type: r.id for r in rows}}
    return None


def _query_taxon_json(taxon):
    if taxon is None:
        return None
    return {'name': taxon['name'], 'taxonomy_types': [t for t in QUERY_TAXON_TYPES if t in taxon['ids']]}


def _query_taxon_id():
    """Profile row id of the named taxon in the database on the switch
    (?taxonomy_type=gtdb|globdb, default gtdb), or None."""
    taxon = _query_taxon()
    taxonomy_type = request.args.get('taxonomy_type', 'gtdb')
    if taxonomy_type not in QUERY_TAXON_TYPES:
        raise BadQuery('taxonomy_type must be gtdb or globdb')
    return taxon['ids'].get(taxonomy_type) if taxon else None


def _query_cluster_filters():
    """Map-cluster filter, same parameters as the taxonomy page."""
    lat, lon = request.args.get('cluster_lat'), request.args.get('cluster_lon')
    if lat is None or lon is None:
        return []
    try:
        precision = max(0, min(2, int(request.args.get('cluster_precision', 1))))
        return [func.round(ParsedSampleAttribute.latitude, precision) == float(lat),
                func.round(ParsedSampleAttribute.longitude, precision) == float(lon)]
    except ValueError:
        raise BadQuery('invalid map cluster')


def _query_table_filters():
    """Cluster plus, if switched on, "Exclude low complexity" -- the runs
    table and its CSV use the same ones."""
    filters = _query_cluster_filters()
    if request.args.get('exclude_low_complexity') == 'true':
        # is_not(True) keeps runs whose low-complexity flag is unknown.
        filters.append(ParsedSampleAttribute.low_complexity.is_not(True))
    return filters


def _query_precision():
    try:
        return max(0, min(2, int(request.args.get('precision', 1))))
    except ValueError:
        raise BadQuery('precision must be a whole number')


def _count(stmt):
    return db.session.execute(select(func.count()).select_from(stmt.subquery())).scalar()


@api.route('/query_search_global_data', methods=('GET',))
def query_search_global_data():
    run_filter = _query_run_filter()
    if run_filter is None:
        return jsonify({'total_num_results': 0, 'num_host_runs': 0, 'num_ecological_runs': 0,
                        'num_low_complexity_runs': 0, 'taxon': None,
                        'lat_lons': [], 'num_lat_lon_runs': 0, 'total_lat_lon_runs': 0})
    filters = run_filter + _query_cluster_filters()
    has_coordinates = [ParsedSampleAttribute.latitude.is_not(None), ParsedSampleAttribute.longitude.is_not(None)]
    lat_lons, num_lat_lon_runs, _ = get_lat_lons(None, QUERY_MAX_MARKERS, filters + has_coordinates)
    # All five counts in one pass over the matching runs.
    total, host, ecological, low_complexity, with_coordinates = db.session.execute(_query_runs(
        filters,
        func.count(),
        func.count().filter(ParsedSampleAttribute.host_or_not_mature == 'host'),
        func.count().filter(ParsedSampleAttribute.host_or_not_mature == 'ecological'),
        # What "Exclude low complexity" removes from the table (>= 95% of reads from one order).
        func.count().filter(ParsedSampleAttribute.low_complexity.is_(True)),
        func.count().filter(*has_coordinates),
    )).one()
    return jsonify({
        'total_num_results': total,
        'num_host_runs': host,
        'num_ecological_runs': ecological,
        'num_low_complexity_runs': low_complexity,
        'lat_lons': lat_lons,
        'num_lat_lon_runs': num_lat_lon_runs,
        'total_lat_lon_runs': with_coordinates,
        # Set when the search names a whole taxon: the table can then show its
        # relative abundance and coverage, from the database on the switch.
        'taxon': _query_taxon_json(_query_taxon()),
    })


@api.route('/query_search_run_data', methods=('GET',))
def query_search_run_data():
    sort_field = request.args.get('sort_field', 'release_year')
    sort_direction = request.args.get('sort_direction', 'desc')
    taxon_id = _query_taxon_id()
    sort_columns = {**QUERY_SORT_COLUMNS, **(QUERY_TAXON_SORT_COLUMNS if taxon_id else {})}
    if sort_field not in sort_columns:
        raise BadQuery('invalid sort field')
    if sort_direction not in ('asc', 'desc'):
        raise BadQuery('invalid sort direction')
    try:
        page = max(1, int(request.args.get('page', 1)))
        page_size = max(1, min(int(request.args.get('page_size', 100)), 1000))
    except ValueError:
        raise BadQuery('page and page_size must be whole numbers')
    if page > QUERY_MAX_PAGE:
        raise BadQuery('page is too large')

    run_filter = _query_run_filter()
    if run_filter is None:
        return jsonify({'results': {'condensed_profiles': [], 'filtered_total': 0}})
    abundance = (QueryTaxonProfile.relative_abundance, QueryTaxonProfile.filled_coverage) if taxon_id \
        else (literal(None), literal(None))
    stmt = _query_runs(run_filter + _query_table_filters(), NcbiMetadata.acc, NcbiMetadata.taxon_name,
                       NcbiMetadata.published, ParsedSampleAttribute.top1_order_fraction, *abundance,
                       taxon_id=taxon_id)
    column = sort_columns[sort_field]
    order = column.desc().nulls_last() if sort_direction == 'desc' else column.asc().nulls_last()
    rows = db.session.execute(
        stmt.order_by(order, NcbiMetadata.acc).limit(page_size).offset((page - 1) * page_size)).fetchall()
    return jsonify({'results': {
        'condensed_profiles': [{
            'sample_acc': acc,
            'organism': 'unspecified' if organism is None else organism.replace(' metagenome', ''),
            'release_year': published.strftime('%Y') if published else None,
            'top1_order_fraction': None if top1 is None else round(top1, 2),
            'relative_abundance': None if rel is None else round(rel * 100, 2),
            'coverage': None if cov is None else round(cov, 2),
        } for acc, organism, published, top1, rel, cov in rows],
        'filtered_total': _count(stmt),
    }})


@api.route('/query_map', methods=('GET',))
def query_map():
    """Same response shape as /taxonomy_map, for the summary map."""
    precision = _query_precision()
    run_filter = _query_run_filter()
    cells = [] if run_filter is None else get_lat_lon_clusters(None, precision, run_filter)
    return jsonify({'precision': precision, 'cells': cells, 'total': sum(c['total'] for c in cells)})


@api.route('/query_map_cell_studies', methods=('GET',))
def query_map_cell_studies():
    precision = _query_precision()
    try:
        lat, lon = float(request.args['lat']), float(request.args['lon'])
    except (KeyError, ValueError):
        raise BadQuery('lat and lon are required numbers')
    run_filter = _query_run_filter()
    studies = [] if run_filter is None else get_cell_study_titles(None, lat, lon, precision, run_filter)
    return jsonify({'studies': studies})


@api.route('/query_search_csv', methods=('GET',))
def query_search_csv():
    """The runs in the table (same query, cluster and low-complexity filter),
    streamed in batches so a broad query doesn't sit in memory."""
    run_filter = _query_run_filter()
    filters = None if run_filter is None else run_filter + _query_table_filters()
    taxon_id = _query_taxon_id()

    def line(values):
        out = io.StringIO()
        csv.writer(out).writerow(values)
        return out.getvalue()

    def generate():
        yield line(['sample_acc', 'environment', 'release_year', 'bioproject', 'study_title',
                    'latitude', 'longitude'] + (['relative_abundance', 'coverage'] if taxon_id else []))
        if filters is None:
            return
        abundance = (QueryTaxonProfile.relative_abundance, QueryTaxonProfile.filled_coverage) if taxon_id \
            else (literal(None), literal(None))
        stmt = _query_runs(filters, NcbiMetadata.acc, NcbiMetadata.taxon_name, NcbiMetadata.published,
                           NcbiMetadata.bioproject, NcbiMetadata.study_title,
                           ParsedSampleAttribute.latitude, ParsedSampleAttribute.longitude, *abundance,
                           taxon_id=taxon_id)
        result = db.session.execute(stmt.order_by(NcbiMetadata.acc).execution_options(stream_results=True))
        while batch := result.fetchmany(1000):
            yield ''.join(line([acc, organism, published.strftime('%Y') if published else '',
                                bioproject, title, lat, lon]
                               + ([round(rel * 100, 2) if rel is not None else '',
                                   round(cov, 2) if cov is not None else ''] if taxon_id else []))
                          for acc, organism, published, bioproject, title, lat, lon, rel, cov in batch)

    resp = Response(stream_with_context(generate()), mimetype='text/csv')
    resp.headers['Content-Disposition'] = 'attachment; filename=sandpiper_search_results.csv'
    return resp


# ?host=${host}&ecological=${ecological}&two_gbp=${two_gbp}
@api.route('/random_run', methods=('GET',))
def random_run():
    host = request.args.get('host') == 'true'
    ecological = request.args.get('ecological') == 'true'
    two_gbp = request.args.get('two_gbp') == 'true'
    exclude_strict_low_complexity = request.args.get('exclude_strict_low_complexity') == 'true'
    non_human_host = request.args.get('non_human_host') == 'true'

    stmt = select(NcbiMetadata.acc).order_by(func.random())
    if host==True and ecological==True:
        # Nothing to do
        pass
    elif host==True:
        stmt = stmt.where(
            NcbiMetadata.id == ParsedSampleAttribute.run_id).where(
                ParsedSampleAttribute.host_or_not_mature=='host'
            )
    elif ecological==True:
        stmt = stmt.where(
            NcbiMetadata.id == ParsedSampleAttribute.run_id).where(
                ParsedSampleAttribute.host_or_not_mature=='ecological'
            )

    if host==True and non_human_host==True:
        # Exclude anything with "human", "homo sapiens", or "metagenome" in taxon_name.
        # "metagenome" labels are ambiguous but predominantly human-associated in practice.
        stmt = stmt.where(
            (NcbiMetadata.taxon_name == None) |
            (
                func.lower(NcbiMetadata.taxon_name).not_like('%human%') &
                func.lower(NcbiMetadata.taxon_name).not_like('%homo sapiens%') &
                func.lower(NcbiMetadata.taxon_name).not_like('%metagenome%')
            )
        )
        # Also exclude samples where any BioSample attribute value contains "homo sapiens".
        # This catches cases where taxon_name is uninformative (e.g. "unidentified", "metagenome")
        # but the host is recorded as Homo sapiens in the BioSample metadata.
        human_host_subq = select(BiosampleAttribute.run_id).where(
            func.lower(BiosampleAttribute.v).like('%homo sapiens%')
        ).distinct()
        stmt = stmt.where(NcbiMetadata.id.not_in(human_host_subq))

    if two_gbp == True:
        stmt = stmt.where(NcbiMetadata.bases >= 2e9)

    if exclude_strict_low_complexity:
        stmt = stmt.where(NcbiMetadata.id == ParsedSampleAttribute.run_id).where(
            (ParsedSampleAttribute.top1_order_fraction == None) |
            (ParsedSampleAttribute.top1_order_fraction < 95.0)
        )

    ran = db.session.execute(stmt).fetchone()

    return jsonify({
        'run': ran.acc
    })

def related_run_query(example_run):
    if example_run.study_abstract is None or example_run.study_abstract == '':
        q = NcbiMetadata.query.filter_by(study_title=example_run.study_title)
    else:
        q = NcbiMetadata.query.filter_by(study_abstract=example_run.study_abstract)
    return q.join(ParsedSampleAttribute).add_columns(
        ParsedSampleAttribute.smf,
        ParsedSampleAttribute.smf_warning,
        ParsedSampleAttribute.known_species_fraction)

@api.route('/project', methods=('GET',))
def project():
    projects = []
    # if request.args.get('bioproject') is not None:
    #     projects.extend(NcbiMetadata.query.filter_by(bioproject=request.args.get('bioproject')).all())
    if request.args.get('model_bioproject') is not None:
        # Match for new samples based on the study abstract, which JGI keeps constant, I think
        example_run = NcbiMetadata.query.filter_by(bioproject=request.args.get('model_bioproject')).first()
        if example_run is None:
            return jsonify({ 'error': 'no run found for bioproject '+request.args.get('model_bioproject') })
        projects.extend(related_run_query(example_run).all())
    if projects == []:
        return jsonify({ 'error': 'No runs found' })
    else:
        # Sort projects by run acc, numerically after removing the SRR/DRR/etc prefix
        projects.sort(key=lambda x: int(x[0].acc[3:]))
        return jsonify({
            'study_abstract': projects[0][0].study_abstract,
            'smf_mean': round(sum([p[1] for p in projects]) / len(projects), 0),
            'known_species_mean': round(sum([p[3] for p in projects])*100 / len(projects), 0),
            'projects': [{
                'acc': p[0].acc,
                'study_title': p[0].study_title,
                'sample_name': p[0].sample_name,
                'library_name': p[0].library_name,
                'experiment_title': p[0].experiment_title,
                'gbp': round(p[0].bases/1e9, 2),
                'smf': p[1],
                'smf_warning': p[2],
                'known_species_fraction': round(p[3]*100,1),
            } for p in projects]
        })

# Comparing against every run of a very large BioProject is slow and adds
# little, so the first PEER_LIMIT other runs stand in for the rest.
PEER_LIMIT = 50

def bioproject_similarity(meta, displayed_keys):
    """Compare `meta` with its BioProject peers on the fields that have a row on
    the page (`displayed_keys`), so the counts always match the flags shown.

    Fields expected to differ (identifiers and the like) are compared apart from
    the rest, so they are flagged but never lower the shared percentage."""
    if not meta.bioproject:
        return None
    peers = NcbiMetadata.query.filter(
        NcbiMetadata.bioproject == meta.bioproject, NcbiMetadata.acc != meta.acc
    ).order_by(NcbiMetadata.id).limit(PEER_LIMIT).options(joinedload(NcbiMetadata.biosample_attributes)).all()
    # One keyed lookup for the peers' Metalog columns: joining the wide table
    # onto the peer query instead takes seconds.
    peer_attributes = {a.run_id: a for a in ParsedSampleAttribute.query.filter(
        ParsedSampleAttribute.run_id.in_([peer.id for peer in peers])).all()} if peers else {}

    def displayed(run, attributes):
        values = {**comparable_values(run), **metalog_comparable_values(attributes)}
        return {key: value for key, value in values.items() if key in displayed_keys}

    def split(values):
        informative = {k: v for k, v in values.items() if not is_expected_to_differ(k)}
        return informative, {k: v for k, v in values.items() if k not in informative}

    own_attributes = meta.parsed_sample_attributes[0] if meta.parsed_sample_attributes else None
    run_informative, run_expected = split(displayed(meta, own_attributes))
    peer_informative, peer_expected = zip(*(split(displayed(peer, peer_attributes.get(peer.id))) for peer in peers)) if peers else ((), ())
    result = compare_to_peers(run_informative, list(peer_informative))
    expected = compare_to_peers(run_expected, list(peer_expected))
    if result is None and expected is None:
        return None
    if result is None:
        result = {'n_other_runs': len(peers), 'n_fields': 0, 'percent_shared': None,
                  'unique_fields': [], 'only_here_fields': []}
    # A run that has no Metalog match at all would otherwise show every Metalog
    # field as present only here, so require a peer that has Metalog data.
    if not any(key.startswith(METALOG_PREFIX) for peer in peer_informative for key in peer):
        result['only_here_fields'] = [f for f in result['only_here_fields'] if not f.startswith(METALOG_PREFIX)]
    result['expected_fields'] = expected['unique_fields'] if expected else []
    return result


def row_difference(key, similarity):
    """'only_here', 'differs' or 'expected' for a displayed row key, else None."""
    if not similarity:
        return None
    if key in similarity['only_here_fields']:
        return 'only_here'
    if key in similarity['unique_fields']:
        return 'differs'
    if key in similarity['expected_fields']:
        return 'expected'
    return None

def related_run_count(model_bioproject):
    example_run = NcbiMetadata.query.filter_by(bioproject=model_bioproject).first()
    if example_run is None:
        return 0
    return related_run_query(example_run).count()
        
@api.route('/accession/<string:acc>', methods=('GET',))
def accession(acc):
    acc = acc.strip()
    # If it is a bioproject, then return that and a model bioproject
    bioproject_example = NcbiMetadata.query.filter(or_(
        NcbiMetadata.bioproject==acc, # These columns need to be indexed
        NcbiMetadata.sra_study==acc
    )).first()
    if bioproject_example is not None:
        return jsonify({
            #   const result_type = response.data.result_type
            #   const acc = response.data.accession
            'result_type': 'project',
            'accession': bioproject_example.bioproject,
        })
    
    run_example = NcbiMetadata.query.filter(or_(
        NcbiMetadata.acc == acc, 
        NcbiMetadata.experiment == acc, # These columns need to be indexed
        NcbiMetadata.biosample == acc,
        NcbiMetadata.sample_acc == acc,
    )).first()
    if run_example is not None:
        return jsonify({
            'result_type': 'run',
            'accession': run_example.acc,
        })
    else:
        return jsonify({ 
            'result_type': 'fail',
            'error': 'No accession identified when searching for "'+acc+'". Please let us know if you believe this is a valid identifier.'})


def _parse_numeric_range(value):
    """Parse a numeric range string into (op, low_str, high_str).
    op is one of: 'between', 'gt', 'gte', 'lt', 'lte', 'eq'.
    Handles negatives: '-40-30' → ('-40', '30'), '-40--30' → ('-40', '-30').
    Handles comparisons: '>2', '>=2', '<5', '<=5'."""
    v = value.strip()
    if v.startswith('>='):
        return 'gte', v[2:], None
    if v.startswith('<='):
        return 'lte', v[2:], None
    if v.startswith('>'):
        return 'gt', v[1:], None
    if v.startswith('<'):
        return 'lt', v[1:], None
    parts = re.split(r'(?<=\d)-(?=-?\d)', v, maxsplit=1)
    if len(parts) == 2:
        return 'between', parts[0], parts[1]
    return 'eq', v, None


def _apply_numeric_filter(column, value, scale=1.0, approx_delta=None):
    """Apply a numeric filter to a SQLAlchemy column.
    scale: multiply parsed float by this (e.g. 1e9 for gbp→bases).
    approx_delta: tolerance for single-value equality (None = exact).
    An empty value means "field is populated, any value" rather than a parse
    failure -- lets sparsely-populated fields (age, temperature, ...) be
    searched for presence alone."""
    if not value.strip():
        return column.isnot(None)
    op, low_str, high_str = _parse_numeric_range(value)
    try:
        low = float(low_str) * scale
        if op == 'between':
            high = float(high_str) * scale
            return column.between(low, high)
        if op == 'gt':
            return column > low
        if op == 'gte':
            return column >= low
        if op == 'lt':
            return column < low
        if op == 'lte':
            return column <= low
        # eq — use approx range if provided, otherwise exact
        if approx_delta is not None:
            return column.between(low - approx_delta * scale, low + approx_delta * scale)
        return column == low
    except (ValueError, TypeError):
        return None


def _apply_numeric_filter_int(column, value, scale=1.0, approx_delta=None):
    """Like _apply_numeric_filter but casts scaled values to int."""
    if not value.strip():
        return column.isnot(None)
    op, low_str, high_str = _parse_numeric_range(value)
    try:
        low = float(low_str)
        if op == 'between':
            high = float(high_str)
            return column.between(int(low * scale), int(high * scale))
        if op == 'gt':
            return column > int(low * scale)
        if op == 'gte':
            return column >= int(low * scale)
        if op == 'lt':
            return column < int(low * scale)
        if op == 'lte':
            return column <= int(low * scale)
        if approx_delta is not None:
            return column.between(int((low - approx_delta) * scale), int((low + approx_delta) * scale))
        return column == int(low * scale)
    except (ValueError, TypeError):
        return None


# Trailing comparison on a habitat search value, e.g. "soil>=0.1" ->
# name="soil", expr=">=0.1". The name is optional -- a bare ">0.5" (empty
# name) matches name="" -- so a threshold with no habitat name at all is
# also accepted, meaning "any habitat's score meets this comparison" (which
# is equivalent to "this run's top/strongest habitat score meets it", since
# if the max score clears the bar, at least one row does, and vice versa).
# Habitat names are free-text and multi-word ("marine sediment") but never
# contain '<'/'>', so anchoring on the comparison operator to split is
# unambiguous. expr is fed straight into _apply_numeric_filter's own
# operator parsing (see _parse_numeric_range), so only the operators it
# supports are offered here: >, >=, <, <=.
HABITAT_SCORE_RE = re.compile(r'^(?P<name>.*?)\s*(?P<expr>(?:>=|<=|>|<)\s*-?\d+(?:\.\d+)?)$')


# Columns the `keywords` key searches: a term matches if any one contains it.
KEYWORD_COLUMNS = (
    NcbiMetadata.study_title, NcbiMetadata.study_abstract, NcbiMetadata.geo_loc_name,
    NcbiMetadata.taxon_name, NcbiMetadata.bioproject, NcbiMetadata.sra_study,
    NcbiMetadata.sample_name,
)


def _keywords_condition(terms, columns=KEYWORD_COLUMNS):
    """Every term must be found in at least one of `columns`."""
    return and_(*(
        or_(*(c.ilike(like_pattern(t), escape=LIKE_ESCAPE) for c in columns))
        for t in terms))


def _parse_search_condition(key, value):
    """Parse a single key:value pair into (sql_condition, description, needs_parsed_join, needs_condensed_join).
    Returns (None, None, False, False) if the key is unrecognised."""
    P = ParsedSampleAttribute
    N = NcbiMetadata

    if key in ('longitude', 'lon'):
        cond = _apply_numeric_filter(P.longitude, value, approx_delta=0.5)
        if cond is None: return None, None, False, False
        return cond, f'longitude: {value}', True, False
    elif key in ('latitude', 'lat'):
        cond = _apply_numeric_filter(P.latitude, value, approx_delta=0.5)
        if cond is None: return None, None, False, False
        return cond, f'latitude: {value}', True, False
    elif key == 'country':
        return N.geo_loc_name.ilike(f'%{value}%'), f'country: {value}', False, False
    elif key == 'continent':
        return N.geo_loc_name_country_continent_calc.ilike(f'%{value}%'), f'continent: {value}', False, False
    elif key == 'year':
        cond = _apply_numeric_filter(P.collection_year, value)
        if cond is None: return None, None, False, False
        return cond, f'year: {value}', True, False
    elif key in ('study', 'study_title', 'title'):
        return N.study_title.ilike(f'%{value}%'), f'study: {value}', False, False
    elif key in ('environment', 'env'):
        if not value.strip():
            return P.host_or_not_mature.isnot(None), 'environment: (any)', True, False
        return func.lower(P.host_or_not_mature) == value.lower(), f'environment: {value}', True, False
    elif key in ('location', 'geo'):
        return N.geo_loc_name.ilike(f'%{value}%'), f'location: {value}', False, False
    elif key in ('temperature', 'temp'):
        cond = _apply_numeric_filter(P.temperature, value, approx_delta=1.0)
        if cond is None: return None, None, False, False
        return cond, f'temperature: {value}°C', True, False
    elif key == 'depth':
        cond = _apply_numeric_filter(P.depth, value, approx_delta=1.0)
        if cond is None: return None, None, False, False
        return cond, f'depth: {value}m', True, False
    elif key == 'platform':
        return N.platform.ilike(f'%{value}%'), f'platform: {value}', False, False
    elif key in ('instrument', 'model'):
        return N.model.ilike(f'%{value}%'), f'instrument: {value}', False, False
    elif key in ('library_strategy', 'strategy'):
        return N.library_strategy.ilike(f'%{value}%'), f'library strategy: {value}', False, False
    elif key in ('organism', 'taxon_name'):
        return N.taxon_name.ilike(f'%{value}%'), f'organism: {value}', False, False
    elif key == 'taxonomy':
        tax_search = '%' + value.lower().replace('_', '\\_') + '%'
        tax_rows = db.session.execute(
            text("select id from taxonomies where lower(name) like :taxon escape '\\'"),
            {'taxon': tax_search}
        ).fetchall()
        if not tax_rows:
            return None, f'no taxonomy matching "{value}"', False, False
        tax_ids = [r.id for r in tax_rows]
        return CondensedProfileCtas1.taxonomy_id.in_(tax_ids), f'taxonomy: {value}', False, True

    # --- Quality / size fields ---
    elif key in ('spf', 'prokaryotic_fraction'):
        cond = _apply_numeric_filter(P.smf, value, approx_delta=2.0)
        if cond is None: return None, None, False, False
        return cond, f'SPF: {value}%', True, False
    elif key in ('ksf', 'known_species_fraction'):
        cond = _apply_numeric_filter(P.known_species_fraction, value, approx_delta=2.0)
        if cond is None: return None, None, False, False
        return cond, f'KSF: {value}%', True, False
    elif key == 'low_complexity':
        if not value.strip():
            return P.low_complexity.isnot(None), 'low complexity: (any)', True, False
        val_lower = value.lower()
        if val_lower in ('yes', 'true', '1'):
            return P.low_complexity == True, 'low complexity: yes', True, False
        elif val_lower in ('no', 'false', '0'):
            return P.low_complexity == False, 'low complexity: no', True, False
        return None, None, False, False
    elif key == 'synthetic':
        if not value.strip():
            return P.synthetic.isnot(None), 'synthetic: (any)', True, False
        val_lower = value.lower()
        if val_lower in ('yes', 'true', '1'):
            return P.synthetic == True, 'synthetic: yes', True, False
        elif val_lower in ('no', 'false', '0'):
            return P.synthetic == False, 'synthetic: no', True, False
        return None, None, False, False
    elif key == 'non_metagenome_organism':
        if not value.strip():
            return P.non_metagenome_organism_strict.isnot(None), 'non-metagenome organism: (any)', True, False
        val_lower = value.lower()
        if val_lower in ('yes', 'true', '1'):
            return P.non_metagenome_organism_strict == True, 'non-metagenome organism: yes', True, False
        elif val_lower in ('no', 'false', '0'):
            return P.non_metagenome_organism_strict == False, 'non-metagenome organism: no', True, False
        return None, None, False, False
    elif key == 'rna_or_non_dna':
        if not value.strip():
            return P.rna_or_non_dna_strict.isnot(None), 'RNA/non-DNA: (any)', True, False
        val_lower = value.lower()
        if val_lower in ('yes', 'true', '1'):
            return P.rna_or_non_dna_strict == True, 'RNA/non-DNA: yes', True, False
        elif val_lower in ('no', 'false', '0'):
            return P.rna_or_non_dna_strict == False, 'RNA/non-DNA: no', True, False
        return None, None, False, False
    elif key in ('gbp', 'bases', 'size'):
        cond = _apply_numeric_filter_int(N.bases, value, scale=1e9, approx_delta=0.1)
        if cond is None: return None, None, False, False
        return cond, f'size: {value} Gbp', False, False
    elif key in ('reads', 'spots'):
        cond = _apply_numeric_filter_int(N.spots, value, scale=1e6, approx_delta=1)
        if cond is None: return None, None, False, False
        return cond, f'reads: {value}M', False, False
    elif key == 'read_length':
        cond = _apply_numeric_filter(N.read1_length_average, value, approx_delta=5)
        if cond is None: return None, None, False, False
        return cond, f'read length: {value}bp', False, False
    elif key == 'release_year':
        if not value.strip():
            return N.published.isnot(None), 'release year: (any)', False, False
        op, low_str, high_str = _parse_numeric_range(value)
        try:
            low = int(low_str)
            if op == 'between':
                high = int(high_str)
                return N.published.between(f'{low}-01-01', f'{high}-12-31'), f'release year: {low}–{high}', False, False
            if op == 'gt':
                return N.published > f'{low}-12-31', f'release year: >{low}', False, False
            if op == 'gte':
                return N.published >= f'{low}-01-01', f'release year: >={low}', False, False
            if op == 'lt':
                return N.published < f'{low}-01-01', f'release year: <{low}', False, False
            if op == 'lte':
                return N.published <= f'{low}-12-31', f'release year: <={low}', False, False
            return N.published.between(f'{low}-01-01', f'{low}-12-31'), f'release year: {low}', False, False
        except ValueError:
            return None, None, False, False

    elif key == 'keywords':
        terms = parse_keyword_terms(value)
        if not terms:
            return None, None, False, False
        return _keywords_condition(terms), f'keywords: {" AND ".join(terms)}', False, False

    elif key == 'grid':
        squares = parse_grid_squares(value)
        if squares is None:
            return None, None, False, False
        return grid_condition(P, squares), describe_grid(squares), True, False

    # --- Study / project fields ---
    elif key in ('abstract', 'study_abstract'):
        return N.study_abstract.ilike(f'%{value}%'), f'abstract: {value}', False, False
    elif key == 'bioproject':
        return N.bioproject.ilike(f'%{value}%'), f'bioproject: {value}', False, False

    # --- Identifier fields ---
    elif key in ('sra_study', 'sra'):
        return _attribute_condition('study_accession', lambda v: v.ilike(f'%{value}%')), f'SRA study: {value}', False, False
    elif key in ('experiment', 'exp'):
        return _attribute_condition('experiment_accession', lambda v: v.ilike(f'%{value}%')), f'experiment: {value}', False, False
    elif key in ('sample_acc', 'sample'):
        return _attribute_condition('sample_accession', lambda v: v.ilike(f'%{value}%')), f'sample accession: {value}', False, False
    elif key == 'biosample':
        return N.biosample.ilike(f'%{value}%'), f'biosample: {value}', False, False

    # --- Submitter fields ---
    elif key in ('organisation', 'organization'):
        search = f'%{value}%'
        return or_(
            N.organisation_name.ilike(search),
            N.organisation_institution.ilike(search),
            N.organisation_department.ilike(search),
            N.organisation_city.ilike(search),
            N.organisation_country.ilike(search),
            N.organisation_contact_name.ilike(search),
        ), f'organisation: {value}', False, False

    # --- Age search ---
    # Numeric range on biosample age attributes. Assumes the stored number is meaningful
    # at face value — scale is study-dependent (years for humans, weeks for neonates, etc.)
    elif key == 'age':
        if not value.strip():
            subq = select(BiosampleAttribute.run_id).where(
                BiosampleAttribute.k.in_(['age', 'host_age', 'Age', 'host age'])
            ).distinct()
            return N.id.in_(subq), 'age: (any)', False, False
        op, low_str, high_str = _parse_numeric_range(value)
        try:
            low = float(low_str)
            age_col = "TRY_CAST(regexp_extract(v, '^\\d+\\.?\\d*') AS DOUBLE)"
            if op == 'between':
                high = float(high_str)
                age_filter = text(f"{age_col} BETWEEN {low} AND {high}")
            elif op == 'gt':
                age_filter = text(f"{age_col} > {low}")
            elif op == 'gte':
                age_filter = text(f"{age_col} >= {low}")
            elif op == 'lt':
                age_filter = text(f"{age_col} < {low}")
            elif op == 'lte':
                age_filter = text(f"{age_col} <= {low}")
            else:
                age_filter = text(f"{age_col} BETWEEN {low} AND {low}")
            subq = select(BiosampleAttribute.run_id).where(
                BiosampleAttribute.k.in_(['age', 'host_age', 'Age', 'host age'])
            ).where(age_filter).distinct()
            return N.id.in_(subq), f'age: {value}', False, False
        except ValueError:
            return None, None, False, False

    # --- BioSample attribute search ---
    # value can be "key=value" to match a specific attribute key, or plain text to match any attribute value
    elif key in ('attr', 'attribute', 'biosample_attr', 'metadata'):
        if '=' in value:
            attr_key, attr_val = value.split('=', 1)
            subq = select(BiosampleAttribute.run_id).where(
                BiosampleAttribute.k.ilike(attr_key.strip())
            ).where(
                BiosampleAttribute.v.ilike(f'%{attr_val.strip()}%')
            ).distinct()
        else:
            subq = select(BiosampleAttribute.run_id).where(
                BiosampleAttribute.v.ilike(f'%{value}%')
            ).distinct()
        return N.id.in_(subq), f'attribute: {value}', False, False

    # --- Metalog (curated/harmonised) metadata search ---
    # Distinct from 'metadata'/'attr' above, which search the raw NCBI BioSample
    # attributes as submitted. This searches ParsedSampleAttribute's meta_*
    # columns instead -- the harmonised fields from the Metalog database (host,
    # sex, age, diet, environment, chemistry measurements, ...). Same two
    # formats as 'attr': "key=value" matches one field by name, plain text
    # matches any field's value.
    elif key == 'metalog':
        meta_columns = {
            c.name[len('meta_'):]: c
            for c in ParsedSampleAttribute.__table__.columns
            if c.name.startswith('meta_')
        }
        if '=' in value:
            meta_key, meta_val = value.split('=', 1)
            normalized_key = meta_key.strip().lower().replace(' ', '_').replace('-', '_')
            column = meta_columns.get(normalized_key)
            if column is None:
                return None, None, False, False
            subq = select(ParsedSampleAttribute.run_id).where(
                column.ilike(f'%{meta_val.strip()}%')
            ).distinct()
        else:
            subq = select(ParsedSampleAttribute.run_id).where(
                or_(*[column.ilike(f'%{value}%') for column in meta_columns.values()])
            ).distinct()
        return N.id.in_(subq), f'metalog: {value}', False, False

    # --- IndicPiper habitat-indicator search ---
    # Matches runs with a nonzero indicator_habitat_scores row for the given
    # habitat -- i.e. this run's genus composition includes at least some of
    # the genera IndicPiper flagged as indicators of that habitat. Substring
    # match since habitat names are multi-word ("marine sediment", "human
    # oral"); empty value means "matches any habitat at all". A trailing
    # comparison (e.g. "soil>=0.1") additionally thresholds on that habitat's
    # IndicPiper score (summed relative abundance of its indicator genera),
    # not just presence of a nonzero row -- see HABITAT_SCORE_RE. A bare
    # comparison with no habitat name (e.g. ">0.5") drops the name filter
    # entirely and matches any run with any habitat row meeting that
    # threshold -- i.e. "this run's strongest habitat match is >0.5".
    elif key in ('habitat', 'indicpiper'):
        if not value.strip():
            subq = select(IndicatorHabitatScore.run_id).distinct()
            return N.id.in_(subq), 'habitat: (any)', False, False
        score_match = HABITAT_SCORE_RE.match(value.strip())
        habitat_name = score_match.group('name').strip() if score_match else None
        if score_match:
            score_filter = _apply_numeric_filter(
                IndicatorHabitatScore.score, score_match.group('expr').replace(' ', ''))
        else:
            score_filter = None
        if score_filter is not None:
            conditions = [score_filter]
            if habitat_name:
                conditions.append(IndicatorHabitatScore.habitat.ilike(f'%{habitat_name}%'))
            subq = select(IndicatorHabitatScore.run_id).where(*conditions).distinct()
        else:
            subq = select(IndicatorHabitatScore.run_id).where(
                IndicatorHabitatScore.habitat.ilike(f'%{value}%')
            ).distinct()
        return N.id.in_(subq), f'habitat: {value}', False, False

    return None, None, False, False


def split_query_parts(query: str) -> list[str]:
    """'a: 1, b: "x, y"' -> ['a: 1', 'b: "x, y"'].

    Search queries are comma-separated, but real values can contain commas
    (e.g. "Pacific Ocean: Oahu, Kaneohe Bay"), so a comma inside double
    quotes does not split. Shared with other query parsing.
    """
    parts, current, quoted = [], [], False
    for ch in query:
        if ch == '"':
            quoted = not quoted
        if ch == ',' and not quoted:
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)
    parts.append(''.join(current))
    return [p.strip() for p in parts if p.strip()]


def unquote(value: str) -> str:
    """'"Oahu, Kaneohe Bay"' -> 'Oahu, Kaneohe Bay'; unquoted values unchanged."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1].strip()
    return value


@dataclass(frozen=True)
class UniversalQuery:
    """A parsed search-box query. Every page that lists "the runs matching
    this query" builds its SQL from here, so they all agree on the count."""
    conditions: tuple
    description: str
    needs_parsed: bool
    needs_condensed: bool
    # A recognised key matched nothing, e.g. an unknown taxonomy.
    matches_nothing: bool = False

    def select(self, *columns, distinct=True):
        """SELECT DISTINCT columns over the matching runs.

        Only the taxonomy join (several profile rows per run) can repeat a
        run; ncbi_metadata.acc and the parsed-attributes join are one row per
        run, so callers that only need that may pass distinct=False and skip
        the de-duplication pass."""
        stmt = select(*columns)
        if distinct:
            stmt = stmt.distinct()
        if self.needs_parsed:
            stmt = stmt.join(ParsedSampleAttribute, ParsedSampleAttribute.run_id == NcbiMetadata.id)
        if self.needs_condensed:
            stmt = stmt.join(CondensedProfileCtas1, CondensedProfileCtas1.run_id == NcbiMetadata.id)
        for cond in self.conditions:
            stmt = stmt.where(cond)
        return stmt


def _attribute_condition(key: str, test):
    """Runs having a BioSample attribute `key` whose value passes `test` (a
    function from the value column to a condition)."""
    return NcbiMetadata.id.in_(
        select(BiosampleAttribute.run_id).where(BiosampleAttribute.k == key, test(BiosampleAttribute.v)))


# A bare accession (or the start of one) typed in the search box:
# (pattern, label, where the value is stored). The experiment, sample and study
# accessions are empty NcbiMetadata columns in the database; their values are
# stored as BioSample attributes, so those are searched instead.
ACCESSION_PATTERNS = (
    (re.compile(r'^[SED]RR\d*$', re.I), 'run accession', ('column', 'acc')),
    (re.compile(r'^[SED]RX\d*$', re.I), 'experiment', ('attribute', 'experiment_accession')),
    (re.compile(r'^[SED]RS\d*$', re.I), 'sample accession', ('attribute', 'sample_accession')),
    (re.compile(r'^[SED]RP\d*$', re.I), 'SRA study', ('attribute', 'study_accession')),
    (re.compile(r'^SAM[NED]A?\d*$', re.I), 'biosample', ('column', 'biosample')),
    (re.compile(r'^PRJ[NED][A-Z]?\d*$', re.I), 'bioproject', ('column', 'bioproject')),
)


def _accession_conditions(part: str):
    """(exact condition, starts-with condition, description) when `part` is an
    accession such as ERR1950668 or just the start of one (ERR12564), else None."""
    token = part.strip().upper()
    for pattern, label, (where, name) in ACCESSION_PATTERNS:
        if not pattern.match(token):
            continue
        if where == 'column':
            field = getattr(NcbiMetadata, name)
            exact, prefix = field == token, field.like(f'{token}%')
        else:
            exact = _attribute_condition(name, lambda v: v == token)
            prefix = _attribute_condition(name, lambda v: v.like(f'{token}%'))
        return exact, prefix, f'{label} starting {token}'
    return None


def _accession_condition(part: str):
    """The condition for a typed accession: that exact accession when it exists
    (a full accession can also be the start of a longer one), otherwise every
    accession starting with it."""
    conditions = _accession_conditions(part)
    if conditions is None:
        return None
    exact, prefix, description = conditions
    if db.session.execute(select(literal(1)).where(exact).select_from(NcbiMetadata).limit(1)).first():
        return exact, description.replace(' starting', ':')
    return prefix, description


def parse_universal_query(q):
    """'key: value, key: value' -> UniversalQuery, or None if nothing parsed."""
    # Commas inside double quotes belong to the value, e.g.
    # location: "Pacific Ocean: Oahu, Kaneohe Bay".
    parts = split_query_parts(q)
    conditions = []
    descriptions = []
    needs_parsed = False
    needs_condensed = False

    for part in parts:
        # (.*) rather than (.+) so "key:" with nothing after it still parses
        # as a key:value pair with an empty value -- that's the presence-only
        # query, e.g. "age:" means "age is populated, any value".
        kv_match = re.match(r'^(\w[\w\s]*?)\s*:\s*(.*)$', part)
        if kv_match:
            key = kv_match.group(1).lower().strip()
            value = unquote(kv_match.group(2))
            cond, desc, p_join, c_join = _parse_search_condition(key, value)
            if cond is not None:
                if not value:
                    # Generic override so free-text ilike fields (which reach
                    # a presence condition via ilike('%%'), not a dedicated
                    # empty-value branch) still get a readable description.
                    desc = f'{key}: (any)'
                conditions.append(cond)
                descriptions.append(desc)
                needs_parsed = needs_parsed or p_join
                needs_condensed = needs_condensed or c_join
                continue
            elif desc is not None:
                # key was recognised but returned no results (e.g. unknown taxonomy)
                return UniversalQuery((), desc, False, False, matches_nothing=True)

        # A bare accession searches for exactly that accession.
        accession = _accession_condition(unquote(part))
        if accession is not None:
            conditions.append(accession[0])
            descriptions.append(accession[1])
            continue

        # Free text fallback for unrecognised or non-key:value input
        part = unquote(part)
        conditions.append(or_(
            NcbiMetadata.study_title.ilike(f'%{part}%'),
            NcbiMetadata.study_abstract.ilike(f'%{part}%'),
            NcbiMetadata.geo_loc_name.ilike(f'%{part}%'),
            NcbiMetadata.taxon_name.ilike(f'%{part}%'),
            NcbiMetadata.sample_name.ilike(f'%{part}%'),
        ))
        descriptions.append(f'"{part}"')

    if not conditions:
        return None
    return UniversalQuery(tuple(conditions), ' AND '.join(descriptions), needs_parsed, needs_condensed)


@api.route('/universal_search', methods=['GET'])
def universal_search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'error': 'No query provided'}), 400

    parsed = parse_universal_query(q)
    if parsed is None:
        return jsonify({'error': 'No valid conditions parsed'}), 400
    if parsed.matches_nothing:
        return jsonify({'count': 0, 'random_acc': None, 'match_description': parsed.description, 'query': q})

    stmt = parsed.select(NcbiMetadata.acc, distinct=parsed.needs_condensed)
    matches = stmt.subquery()
    # One pass: the match total, plus a uniformly random match picked as the
    # row with the largest per-row random() -- no sort, no second scan.
    # The caller may be viewing a run already; excluding it from the pick (not
    # from the count, which the UI displays) stops a query that matches only
    # that run from handing it straight back.
    exclude = request.args.get('exclude')
    pick = func.arg_max(matches.c.acc, func.random())
    if exclude:
        pick = pick.filter(matches.c.acc != exclude)
    total, random_acc = db.session.execute(
        select(func.count(), pick).select_from(matches)).one()

    return jsonify({
        'count': total,
        'random_acc': random_acc,
        'match_description': parsed.description,
        'query': q,
    })


RECAPTCHA_SECRET_KEY = '6LdZXhorAAAAAJOtcFJj6SBkOKW4bhKu80khNcH2'


@api.route('/verify-recaptcha', methods=['POST'])
def verify_recaptcha():
    data = request.json
    token = data.get('recaptchaResponse')
    if token is None:  # Sometimes get either (in localhost testing at least)? Bit confused as to why
        token = data.get('token')

    if not token:
        return jsonify(success=False, message='No token provided'), 400

    response = requests.post(
        'https://www.google.com/recaptcha/api/siteverify',
        data={
            'secret': RECAPTCHA_SECRET_KEY,
            'response': token
        }
    )

    result = response.json()

    if result.get('success'):
        return jsonify(success=True)
    else:
        return jsonify(success=False, errors=result.get('error-codes', [])), 400
