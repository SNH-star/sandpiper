#!/usr/bin/env python3
"""Build IndicPiper's two input tables from the current Sandpiper duckdb,
instead of the frozen Zenodo/GitHub snapshot IndicPiper ships with.

Two phases, run in order (see config.yml for the full explanation):

  --phase metadata   Cheap. QC-filters samples, derives Habitat, applies the
                      combine rules, writes habitat_counts.tsv. This is the
                      countHabitats()-equivalent step -- inspect the output
                      and set MIN_HABITAT_SAMPLES in config.yml before
                      running phase "genus".

  --phase genus       Expensive. Filters to the habitats that cleared
                      MIN_HABITAT_SAMPLES, computes n_per_habitat from the
                      smallest included habitat's pool, and pivots the
                      genus-level condensed profile into the wide
                      sample-by-genus matrix runIndicPiper() expects.

Both phases write into OUTPUT_DIR, in the exact format
IndicPiper.R::runIndicPiper() expects (myMetadataTable.csv.gz,
myGenusTable.csv.gz) so prepIndicPiper() does not need to be called at all --
this script already does its job (QC, habitat combining, zero-prevalence
drop) directly against current data.
"""

import argparse
import gzip
import os
import sys

import duckdb
import pandas as pd
import yaml

MAMMALIAN_GUTS = ('human gut', 'pig gut', 'bovine gut', 'sheep gut', 'canine gut', 'goat gut')
FRESHWATER_GROUP = ('freshwater', 'aquatic', 'pond', 'lake water', 'riverine')


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def qc_metadata_query(cfg):
    """SQL selecting one QC-passed row per sample, with derived Habitat.

    Mirrors GenerateStartingPoint.R's filters (see config.yml for the
    single-cell caveat, which is intentionally NOT reproduced here).

    Deliberately does NOT touch condensed_profiles (huge table) -- phase 1
    must stay cheap. There is also no taxonomy row literally named
    'unassigned' in this schema (confirmed empty on a live diagnostic query),
    so the "< 60% unassigned genus fraction" check from GenerateStartingPoint.R
    can't be replicated the same way here; it is instead computed in phase 2
    as 100 - sum(genus relative_abundance) per sample, once we're already
    pivoting condensed_profiles anyway.
    """
    organism_field = cfg['ORGANISM_FIELD']
    min_bases = cfg['MIN_BACTERIAL_ARCHAEAL_BASES']

    return f"""
    SELECT
        nm.id AS run_pk,
        nm.acc AS sample,
        trim(regexp_replace(nm.{organism_field}, '(?i)\\s*metagenome\\s*$', '')) AS habitat_raw
    FROM ncbi_metadata nm
    JOIN parsed_sample_attributes psa ON psa.run_id = nm.id
    WHERE nm.{organism_field} IS NOT NULL
      AND nm.{organism_field} ILIKE '%metagenome%'
      AND lower(trim(nm.{organism_field})) != 'metagenome'
      AND psa.bacterial_archaeal_bases > {min_bases}
      AND (psa.smf_warning IS NULL OR psa.smf_warning = FALSE)
      AND (psa.low_complexity IS NULL OR psa.low_complexity = FALSE)
    """


def apply_combine_rules(df, cfg):
    habitat = df['habitat_raw'].str.strip().str.lower()

    if cfg.get('COMBINE_SOIL_RHIZO', True):
        habitat = habitat.replace('rhizosphere', 'soil')
    if cfg.get('COMBINE_FRESHWATER', True):
        habitat = habitat.replace(list(FRESHWATER_GROUP), 'freshwater water')
    if cfg.get('COMBINE_GLACIER_ICE', True):
        habitat = habitat.replace('ice', 'glacier')
    if cfg.get('COMBINE_MAMMALIAN_GUT', True):
        habitat = habitat.replace(list(MAMMALIAN_GUTS), 'mammalian gut')
    if cfg.get('COMBINE_SALIVA_ORAL', True):
        habitat = habitat.replace('human saliva', 'human oral')
    # prepIndicPiper's marine -> seawater -> "marine water" round trip: the second
    # step (gsub on the literal string "seawater") also catches any sample that was
    # ALREADY labelled "seawater" independently of the marine rename. Reproduce
    # both effects, not just the marine one.
    habitat = habitat.replace('marine', 'seawater').replace('seawater', 'marine water')

    df = df.copy()
    df['Habitat'] = habitat
    return df


def apply_vague_blocklist(df, cfg):
    blocklist = {v.strip().lower() for v in cfg.get('VAGUE_ORGANISM_BLOCKLIST', [])}
    return df[~df['Habitat'].isin(blocklist)]


def phase_metadata(cfg):
    os.makedirs(cfg['OUTPUT_DIR'], exist_ok=True)

    print(f"Connecting to {cfg['SANDPIPER_DB']} (read-only)...", flush=True)
    con = duckdb.connect(cfg['SANDPIPER_DB'], read_only=True)

    print("Running QC-filter query...", flush=True)
    df = con.execute(qc_metadata_query(cfg)).fetch_df()
    con.close()
    print(f"  {len(df):,} samples passed QC (bases/warning/low_complexity/unassigned/organism filters)", flush=True)

    df = apply_combine_rules(df, cfg)
    before = len(df)
    df = apply_vague_blocklist(df, cfg)
    print(f"  {before - len(df):,} samples dropped for a vague habitat label ({len(df):,} remain)", flush=True)

    qc_path = os.path.join(cfg['OUTPUT_DIR'], 'qc_metadata_full.csv.gz')
    df[['run_pk', 'sample', 'Habitat']].to_csv(qc_path, index=False, compression='gzip')
    print(f"Wrote {qc_path}", flush=True)

    counts = (df.groupby('Habitat').size().sort_values(ascending=False).rename('n').reset_index())
    counts_path = os.path.join(cfg['OUTPUT_DIR'], 'habitat_counts.tsv')
    counts.to_csv(counts_path, sep='\t', index=False)
    print(f"Wrote {counts_path}\n", flush=True)
    print(counts.to_string(index=False), flush=True)
    print(
        "\nInspect the counts above, set MIN_HABITAT_SAMPLES in config.yml, "
        "then run --phase genus.",
        flush=True,
    )


def phase_genus(cfg):
    qc_path = os.path.join(cfg['OUTPUT_DIR'], 'qc_metadata_full.csv.gz')
    if not os.path.exists(qc_path):
        sys.exit(f"{qc_path} not found -- run --phase metadata first.")

    df = pd.read_csv(qc_path)
    taxonomy_type = cfg['TAXONOMY_TYPE']
    max_unassigned = cfg['MAX_UNASSIGNED_GENUS_PERCENT']

    print(f"Connecting to {cfg['SANDPIPER_DB']} (read-only) -- this touches "
          f"condensed_profiles (hundreds of millions of rows), expect it to be slow.", flush=True)
    con = duckdb.connect(cfg['SANDPIPER_DB'], read_only=True)
    # DuckDB auto-detects system RAM via /proc/meminfo, which reports the node's full
    # physical memory rather than this job's PBS/cgroup allocation -- left unset, it
    # happily grows past the job's --mem limit and gets SIGKILLed by the scheduler
    # instead of spilling to disk. Cap it (with headroom for pandas/python overhead)
    # to whatever this job was actually given.
    job_mem_gb = int(cfg.get('DUCKDB_MEMORY_LIMIT_GB', 48))
    job_threads = len(os.sched_getaffinity(0))
    con.execute(f"PRAGMA memory_limit='{job_mem_gb}GB'")
    con.execute(f"PRAGMA threads={job_threads}")
    # SANDPIPER_DB is opened read_only, so DuckDB's default spill location next to the
    # db file may not be writable -- point it at our own output dir instead.
    con.execute(f"PRAGMA temp_directory='{cfg['OUTPUT_DIR']}/duckdb_tmp'")
    con.register('qc_samples', df[['run_pk', 'sample']])

    print("Building genus-level long table for QC-passed samples...", flush=True)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE genus_long AS
        SELECT
            s.sample AS sampleID,
            s.run_pk AS run_pk,
            t.full_name AS genus,
            cp.relative_abundance
        FROM condensed_profiles cp
        JOIN taxonomies t ON t.id = cp.taxonomy_id
        JOIN qc_samples s ON s.run_pk = cp.run_id
        WHERE cp.taxonomy_type = '{taxonomy_type}'
          AND t.taxonomy_level = 'genus'
          AND t.name != 'unassigned'
    """)

    # There is no explicit 'unassigned' taxon in this schema (confirmed empty
    # on a live query), so the unassigned genus fraction is derived as the
    # complement of what's classified. relative_abundance is a 0-1 fraction
    # here (confirmed on a live query: max=1.0, not 100), so convert to a
    # percentage to compare against MAX_UNASSIGNED_GENUS_PERCENT.
    print(f"Computing per-sample unassigned genus fraction (< {max_unassigned}% required)...", flush=True)
    unassigned_df = con.execute("""
        SELECT run_pk, 100 * (1 - sum(relative_abundance)) AS unassigned_pct
        FROM genus_long
        GROUP BY run_pk
    """).fetch_df()

    before = len(df)
    df = df.merge(unassigned_df, on='run_pk', how='inner')
    df = df[df['unassigned_pct'] < max_unassigned]
    print(f"  {before - len(df):,} samples dropped for >= {max_unassigned}% unassigned genus "
          f"fraction ({len(df):,} remain)", flush=True)

    counts = df.groupby('Habitat').size().sort_values(ascending=False)
    n_habitats = cfg.get('N_HABITATS')
    if n_habitats:
        # Top-N-by-count -- the "just tell me the number" knob for unattended
        # runs (e.g. from the main Snakefile), once MIN_HABITAT_SAMPLES has
        # already been tuned interactively via a habitat_counts.tsv inspection.
        included_habitats = counts.head(int(n_habitats)).index.tolist()
        print(f"N_HABITATS={n_habitats} set -- using top {len(included_habitats)} habitats by count, "
              f"ignoring MIN_HABITAT_SAMPLES.", flush=True)
    else:
        min_n = cfg['MIN_HABITAT_SAMPLES']
        included_habitats = counts[counts >= min_n].index.tolist()
        if not included_habitats:
            sys.exit(f"No habitat has >= {min_n} QC-passed samples. Lower MIN_HABITAT_SAMPLES and retry.")

    df = df[df['Habitat'].isin(included_habitats)].sort_values('sample').reset_index(drop=True)
    smallest_habitat_n = int(counts[included_habitats].min())

    n_per_habitat = int(smallest_habitat_n * cfg['N_PER_HABITAT_FRACTION'])
    n_per_habitat = max(cfg['N_PER_HABITAT_MIN'], min(n_per_habitat, cfg['N_PER_HABITAT_MAX']))
    if n_per_habitat >= smallest_habitat_n:
        con.close()
        sys.exit(
            f"n_per_habitat ({n_per_habitat}) >= smallest included habitat's pool "
            f"({smallest_habitat_n}). Raise MIN_HABITAT_SAMPLES or lower N_PER_HABITAT_MIN."
        )

    print(f"Included habitats ({len(included_habitats)}): {sorted(included_habitats)}", flush=True)
    print(f"Smallest included habitat pool: {smallest_habitat_n:,} samples", flush=True)
    print(f"n_per_habitat resolved to: {n_per_habitat:,} "
          f"({cfg['N_PER_HABITAT_FRACTION']:.0%} of smallest pool, clamped to "
          f"[{cfg['N_PER_HABITAT_MIN']}, {cfg['N_PER_HABITAT_MAX']}])", flush=True)

    meta_path = os.path.join(cfg['OUTPUT_DIR'], 'myMetadataTable.csv.gz')
    df[['sample', 'Habitat']].to_csv(meta_path, index=False, compression='gzip')
    print(f"Wrote {meta_path} ({len(df):,} samples)", flush=True)

    genus_path = os.path.join(cfg['OUTPUT_DIR'], 'myGenusTable.csv.gz')
    con.register('final_samples', df[['run_pk']])

    # DuckDB's PIVOT/COPY can't materialize this as a wide table directly: there are
    # 37,503 distinct GTDB genera, and DuckDB's storage has a hard ~262,136-byte
    # physical row-width ceiling (37,503 * 8-byte DOUBLE alone blows past it) --
    # confirmed via `_duckdb.NotImplementedException: Too many columns: tuple width
    # exceeds block size of 262136` on a real run. Instead, pull the long-format
    # (sampleID, genus, relative_abundance) table out of DuckDB -- narrow, no width
    # limit -- and do the actual wide pivot in polars, which has no such ceiling.
    print("Exporting long-format genus table (final included samples only)...", flush=True)
    long_df = con.execute("""
        SELECT g.sampleID, g.genus, g.relative_abundance
        FROM genus_long g
        JOIN final_samples f ON f.run_pk = g.run_pk
    """).pl()
    con.close()
    print(f"  {len(long_df):,} long-format rows", flush=True)

    print("Pivoting to sample x genus wide matrix in polars...", flush=True)
    wide_df = (
        long_df.pivot(on='genus', index='sampleID', values='relative_abundance', aggregate_function='sum')
        .fill_null(0)
        .sort('sampleID')
    )
    print(f"  wide matrix: {wide_df.height:,} samples x {wide_df.width - 1:,} genera", flush=True)

    with gzip.open(genus_path, 'wb') as fh:
        wide_df.write_csv(fh)
    print(f"Wrote {genus_path}", flush=True)
    print(
        "\nNOTE: myGenusTable.csv.gz row order is sorted by 'sampleID' in polars; "
        "myMetadataTable.csv.gz was written sorted by 'sample' in pandas. "
        "run_indicpiper.R re-sorts both by sample before checking they match -- "
        "do not skip that check.",
        flush=True,
    )

    params_path = os.path.join(cfg['OUTPUT_DIR'], 'run_params.R')
    with open(params_path, 'w') as f:
        f.write(f"n_per_habitat <- {n_per_habitat}L\n")
        f.write(f"n_multipatt_perm <- {cfg['N_MULTIPATT_PERM']}L\n")
        f.write(f"n_runs <- {cfg['N_RUNS']}L\n")
        f.write(f"run_cut <- {cfg['RUN_CUT']}L\n")
        f.write(f"p_cut <- {cfg['P_CUT']}\n")
        f.write(f"IndVal_cut <- {cfg['INDVAL_CUT']}\n")
        f.write(f"seed <- {cfg['SEED']}L\n")
        f.write(f"output_csv <- \"{cfg['OUTPUT_CSV']}\"\n")
        f.write(f"meta_path <- \"{meta_path}\"\n")
        f.write(f"genus_path <- \"{genus_path}\"\n")
    print(f"Wrote {params_path}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--config', default='config.yml',
                         help='QC/methodology settings (thresholds, blocklist, combine rules, runIndicPiper params)')
    parser.add_argument('--phase', choices=['metadata', 'genus'], required=True)
    # Per-run overrides for unattended use (e.g. from the main Snakefile, one
    # invocation per SANDPIPER_VERSION) without editing config.yml each time.
    parser.add_argument('--sandpiper-db', help='overrides SANDPIPER_DB')
    parser.add_argument('--output-dir', help='overrides OUTPUT_DIR')
    parser.add_argument('--n-habitats', type=int, help='overrides N_HABITATS')
    parser.add_argument('--output-csv', help='overrides OUTPUT_CSV (written into run_params.R for '
                         'run_indicpiper.R to consume) -- give an absolute per-version path here for '
                         'unattended use, since it otherwise resolves relative to wherever '
                         'run_indicpiper.R is invoked from (indicpiper_custom/IndicPiper/, required for '
                         'its own source() calls), and would collide across concurrent/different builds')
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.sandpiper_db:
        cfg['SANDPIPER_DB'] = args.sandpiper_db
    if args.output_dir:
        cfg['OUTPUT_DIR'] = args.output_dir
    if args.n_habitats:
        cfg['N_HABITATS'] = args.n_habitats
    if args.output_csv:
        cfg['OUTPUT_CSV'] = args.output_csv

    if args.phase == 'metadata':
        phase_metadata(cfg)
    else:
        phase_genus(cfg)


if __name__ == '__main__':
    main()
