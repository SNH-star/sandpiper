#!/usr/bin/env python3
"""One-off diagnostic: figure out why the QC query in build_indicpiper_inputs.py
returns 0 rows. Run and paste the output back.

Usage: pixi run -e sandpiper python scripts/diagnose.py --config config.yml
"""
import argparse
import duckdb
import yaml

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.yml')
args = parser.parse_args()
cfg = yaml.safe_load(open(args.config))

con = duckdb.connect(cfg['SANDPIPER_DB'], read_only=True)

def q(sql, label):
    print(f"\n--- {label} ---")
    try:
        print(con.execute(sql).fetch_df().to_string(index=False))
    except Exception as e:
        print(f"ERROR: {e}")

q("SELECT count(*) AS n FROM ncbi_metadata", "ncbi_metadata row count")
q("SELECT count(*) AS n FROM parsed_sample_attributes", "parsed_sample_attributes row count")
q(f"SELECT {cfg['ORGANISM_FIELD']}, count(*) AS n FROM ncbi_metadata "
  f"GROUP BY 1 ORDER BY n DESC LIMIT 15", f"top values of {cfg['ORGANISM_FIELD']}")
q(f"SELECT count(*) AS n FROM ncbi_metadata WHERE {cfg['ORGANISM_FIELD']} ILIKE '%metagenome%'",
  f"{cfg['ORGANISM_FIELD']} ILIKE '%metagenome%' count")
q("SELECT count(*) AS n, avg(bacterial_archaeal_bases) AS mean_bases, "
  "count(bacterial_archaeal_bases) AS non_null_bases FROM parsed_sample_attributes",
  "bacterial_archaeal_bases stats")
q(f"SELECT count(*) AS n FROM parsed_sample_attributes WHERE bacterial_archaeal_bases > {cfg['MIN_BACTERIAL_ARCHAEAL_BASES']}",
  "rows passing bases filter")
q("SELECT smf_warning, count(*) AS n FROM parsed_sample_attributes GROUP BY 1", "smf_warning value counts")
q("SELECT low_complexity, count(*) AS n FROM parsed_sample_attributes GROUP BY 1", "low_complexity value counts")
q("SELECT taxonomy_level, count(*) AS n FROM taxonomies GROUP BY 1 ORDER BY n DESC", "taxonomy_level value counts")
q(f"SELECT name, taxonomy_type, count(*) AS n FROM taxonomies WHERE name = 'unassigned' GROUP BY 1,2",
  "'unassigned' taxonomy rows")
q(f"SELECT count(*) AS n FROM condensed_profiles WHERE taxonomy_type = '{cfg['TAXONOMY_TYPE']}'",
  f"condensed_profiles rows with taxonomy_type='{cfg['TAXONOMY_TYPE']}'")

con.close()

# --- extra diagnostic: is relative_abundance a 0-1 fraction or 0-100 percent? ---
con2 = duckdb.connect(cfg['SANDPIPER_DB'], read_only=True)
print("\n--- relative_abundance range, genus level, gtdb ---")
print(con2.execute(f"""
    SELECT min(cp.relative_abundance) AS min_val, max(cp.relative_abundance) AS max_val,
           avg(cp.relative_abundance) AS avg_val
    FROM condensed_profiles cp
    JOIN taxonomies t ON t.id = cp.taxonomy_id
    WHERE cp.taxonomy_type = '{cfg['TAXONOMY_TYPE']}' AND t.taxonomy_level = 'genus'
""").fetch_df().to_string(index=False))

print("\n--- per-sample sum(relative_abundance) at genus level, first 10 run_ids ---")
print(con2.execute(f"""
    SELECT cp.run_id, sum(cp.relative_abundance) AS genus_sum, count(*) AS n_genera
    FROM condensed_profiles cp
    JOIN taxonomies t ON t.id = cp.taxonomy_id
    WHERE cp.taxonomy_type = '{cfg['TAXONOMY_TYPE']}' AND t.taxonomy_level = 'genus'
    GROUP BY cp.run_id
    LIMIT 10
""").fetch_df().to_string(index=False))
con2.close()
