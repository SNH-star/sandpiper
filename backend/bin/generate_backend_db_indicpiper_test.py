#!/usr/bin/env python3

import csv
import importlib.machinery
import importlib.util
import os
import tempfile
import unittest

import duckdb

# generate_backend_db has no .py extension (it's a CLI entry point), so it
# can't be imported with a normal `import` statement -- load it by path.
# spec_from_file_location can't infer a loader from an extensionless file, so
# the loader is passed explicitly (it returns None otherwise on Python 3.12).
_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), 'generate_backend_db')
_loader = importlib.machinery.SourceFileLoader('generate_backend_db', _SCRIPT_PATH)
_spec = importlib.util.spec_from_file_location('generate_backend_db', _SCRIPT_PATH, loader=_loader)
generate_backend_db = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generate_backend_db)

# Run with the project's pixi env, e.g.:
#   .pixi/envs/sandpiper/bin/python -m pytest backend/bin/generate_backend_db_indicpiper_test.py -v
# A bare `python3 -m pytest` fails at collection (ModuleNotFoundError: polars)
# because importing this test also executes generate_backend_db's own
# module-level imports.


def _write_indicator_csv(path, rows):
    # Same header shape as indicpiper_custom/IndicPiper/genus_habitat_indicators_custom.csv
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Taxonomy', 'Habitat', 'PercRunsInd', 'IndVal_mean', 'IndVal_se',
            'IndVal_min', 'IndVal_max', 'PVal_mean', 'PVal_se', 'PVal_min', 'PVal_max',
        ])
        for row in rows:
            writer.writerow(row)


def _make_minimal_db(db_path):
    '''Builds just enough schema for add_indicpiper_scores() to run: one
    ncbi_metadata row, one genus-level taxonomies row, one condensed_profiles
    row referencing it. Raw SQL (not db.create_all()) so this test doesn't
    depend on Flask app context, matching add_indicpiper_scores() itself
    connecting directly via duckdb.connect(db_path) (see the comment at
    generate_backend_db:1436-1448 on why db.session can't be used here).
    '''
    conn = duckdb.connect(db_path)
    conn.execute("CREATE SEQUENCE ncbi_metadata_id_seq")
    conn.execute("CREATE TABLE ncbi_metadata (id INTEGER PRIMARY KEY DEFAULT nextval('ncbi_metadata_id_seq'), acc VARCHAR)")
    conn.execute("INSERT INTO ncbi_metadata (id, acc) VALUES (1, 'SRRTEST01')")

    conn.execute("CREATE SEQUENCE taxonomies_id_seq")
    conn.execute("""
        CREATE TABLE taxonomies (
            id INTEGER PRIMARY KEY DEFAULT nextval('taxonomies_id_seq'),
            taxonomy_level VARCHAR NOT NULL,
            parent_id INTEGER,
            name VARCHAR NOT NULL,
            full_name VARCHAR NOT NULL,
            taxonomy_type VARCHAR NOT NULL
        )
    """)
    conn.execute("""
        INSERT INTO taxonomies (id, taxonomy_level, name, full_name, taxonomy_type)
        VALUES (1, 'genus', 'Hodarchaeum',
                'd__Archaea; p__Asgardarchaeota; c__Heimdallarchaeia; o__Hodarchaeales; f__Hodarchaeaceae; g__Hodarchaeum',
                'gtdb')
    """)

    conn.execute("CREATE SEQUENCE condensed_profiles_id_seq")
    conn.execute("""
        CREATE TABLE condensed_profiles (
            id INTEGER PRIMARY KEY DEFAULT nextval('condensed_profiles_id_seq'),
            run_id INTEGER NOT NULL,
            coverage DOUBLE NOT NULL,
            filled_coverage DOUBLE NOT NULL,
            relative_abundance DOUBLE NOT NULL,
            taxonomy_id INTEGER NOT NULL,
            taxonomy_type VARCHAR NOT NULL
        )
    """)
    conn.execute("""
        INSERT INTO condensed_profiles
            (id, run_id, coverage, filled_coverage, relative_abundance, taxonomy_id, taxonomy_type)
        VALUES (1, 1, 0.3, 0.3, 0.3, 1, 'gtdb')
    """)
    conn.close()


class AddIndicpiperScoresTest(unittest.TestCase):
    def test_persists_ind_val_mean_and_p_val_mean_per_genus(self):
        with tempfile.TemporaryDirectory() as d:
            db_path = os.path.join(d, 'test.duckdb')
            csv_path = os.path.join(d, 'indicators.csv')
            _make_minimal_db(db_path)
            _write_indicator_csv(csv_path, [
                ['Archaea; Asgardarchaeota; Heimdallarchaeia; Hodarchaeales; '
                 'Hodarchaeaceae; Hodarchaeum',
                 'marine sediment', 100, 0.569071166615969, 0.00298103667197125,
                 0.481914640943097, 0.614053434561189, 0.0099009900990099, 0,
                 0.0099009900990099, 0.0099009900990099],
            ])

            generate_backend_db.add_indicpiper_scores(db_path, csv_path)

            conn = duckdb.connect(db_path)
            row = conn.execute("""
                SELECT run_id, habitat, genus, relative_abundance, ind_val_mean, p_val_mean
                FROM indicator_habitat_genus_scores
            """).fetchone()
            conn.close()

            self.assertEqual(row[0], 1)
            self.assertEqual(row[1], 'marine sediment')
            self.assertEqual(row[2], 'Hodarchaeum')
            self.assertAlmostEqual(row[3], 0.3)
            self.assertAlmostEqual(row[4], 0.569071166615969)
            self.assertAlmostEqual(row[5], 0.0099009900990099)

    def test_rerun_against_pre_existing_two_column_table_adds_columns(self):
        '''add_indicpiper_scores() must stay re-runnable against a DB that
        already has the old (pre-this-change) indicator_habitat_genus_scores
        schema -- see generate_backend_db:1436-1448 on why this stage can be
        applied to an existing live DB after the fact.
        '''
        with tempfile.TemporaryDirectory() as d:
            db_path = os.path.join(d, 'test.duckdb')
            csv_path = os.path.join(d, 'indicators.csv')
            _make_minimal_db(db_path)

            conn = duckdb.connect(db_path)
            conn.execute("CREATE SEQUENCE indicator_habitat_genus_scores_id_seq")
            conn.execute("""
                CREATE TABLE indicator_habitat_genus_scores (
                    id INTEGER PRIMARY KEY DEFAULT nextval('indicator_habitat_genus_scores_id_seq'),
                    run_id INTEGER NOT NULL,
                    habitat VARCHAR NOT NULL,
                    genus VARCHAR NOT NULL,
                    relative_abundance DOUBLE NOT NULL
                )
            """)
            conn.close()

            _write_indicator_csv(csv_path, [
                ['Archaea; Asgardarchaeota; Heimdallarchaeia; Hodarchaeales; '
                 'Hodarchaeaceae; Hodarchaeum',
                 'marine sediment', 100, 0.5, 0.001, 0.4, 0.6, 0.01, 0, 0.01, 0.01],
            ])

            generate_backend_db.add_indicpiper_scores(db_path, csv_path)  # must not raise

            conn = duckdb.connect(db_path)
            ind_val = conn.execute(
                "SELECT ind_val_mean FROM indicator_habitat_genus_scores"
            ).fetchone()[0]
            conn.close()
            self.assertAlmostEqual(ind_val, 0.5)


if __name__ == '__main__':
    unittest.main()
