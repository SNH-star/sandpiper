#!/usr/bin/env python3
import argparse
import os
import duckdb


def export_indicpiper_csv(con, out_path):
    """One row per sample with >=1 nonzero IndicPiper habitat match: Run,
    Environment (all matched habitats packed into one field, e.g.
    "Wastewater (7.8%), Soil (3.1%)", strongest match first). Samples with
    no habitat match are not included -- indicator_habitat_scores is sparse
    by design (see its docstring in api/models.py).
    """
    con.execute(f"""
        COPY (
            SELECT
                nm.acc AS "Run",
                string_agg(printf('%s (%.1f%%)', ihs.habitat, ihs.score * 100), ', ' ORDER BY ihs.score DESC) AS "Environment"
            FROM indicator_habitat_scores ihs
            JOIN ncbi_metadata nm ON nm.id = ihs.run_id
            GROUP BY nm.acc
            ORDER BY nm.acc
        ) TO '{out_path}' (HEADER, DELIMITER ',')
    """)


def export_metalog_csv(con, out_path):
    """One row per sample in parsed_sample_attributes: Run, plus every
    meta_* column (discovered dynamically, not hardcoded -- the metalog
    schema evolves, see models.py's ParsedSampleAttribute). NULL values are
    written as the literal string "NaN", not left blank.
    """
    meta_columns = [r[0] for r in con.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'parsed_sample_attributes' AND starts_with(column_name, 'meta_')
        ORDER BY column_name
    """).fetchall()]
    if not meta_columns:
        raise Exception("No meta_* columns found on parsed_sample_attributes -- "
                         "is INCLUDE_METALOG disabled for this build?")
    select_list = ', '.join(f'psa."{c}"' for c in meta_columns)
    con.execute(f"""
        COPY (
            SELECT nm.acc AS "Run", {select_list}
            FROM parsed_sample_attributes psa
            JOIN ncbi_metadata nm ON nm.id = psa.run_id
            ORDER BY nm.acc
        ) TO '{out_path}' (HEADER, DELIMITER ',', NULLSTR 'NaN')
    """)


def main(db_path, output_dir, include_indicpiper=True, include_metalog=True):
    os.makedirs(output_dir, exist_ok=True)
    con = duckdb.connect(db_path, read_only=True)
    if include_indicpiper:
        export_indicpiper_csv(con, os.path.join(output_dir, 'indicpiper_results.csv'))
    if include_metalog:
        export_metalog_csv(con, os.path.join(output_dir, 'metalog_results.csv'))
    con.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Export IndicPiper habitat results and metalog metadata to CSV")
    parser.add_argument("db_path", help="Path to the finished DuckDB database file")
    parser.add_argument("output_dir", help="Directory to write indicpiper_results.csv and metalog_results.csv into")
    # Driven by INCLUDE_INDICPIPER_CSV/INCLUDE_METALOG_CSV in prod_config.yml
    # -- each export is independently skippable.
    parser.add_argument("--skip-indicpiper", action="store_true", help="Don't write indicpiper_results.csv")
    parser.add_argument("--skip-metalog", action="store_true", help="Don't write metalog_results.csv")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.db_path, args.output_dir,
         include_indicpiper=not args.skip_indicpiper,
         include_metalog=not args.skip_metalog)
