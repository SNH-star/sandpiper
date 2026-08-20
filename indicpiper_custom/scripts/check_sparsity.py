#!/usr/bin/env python3
"""One-off check: how sparse would a dense sample x habitat indicator-score
matrix be against the live sandpiper_40.duckdb, using
genus_habitat_indicators_custom.csv. Informs whether the new IndicPiper
scores table should be normalized (sparse rows) or wide (dense columns) --
see the design discussion in indicpiper_custom/outputs/.
"""
import duckdb
import pandas as pd

con = duckdb.connect(
    "/home/herholdt/sandpiper-advanced-search/backend/db/sandpiper_40.duckdb",
    read_only=True,
)

ind = pd.read_csv("IndicPiper/genus_habitat_indicators_custom.csv")
con.register("indicators", ind[["Taxonomy", "Habitat"]])

con.execute(r"""
    CREATE TEMP TABLE genus_long AS
    SELECT
        cp.run_id,
        -- genus_habitat_indicators_custom.csv's Taxonomy has GTDB rank prefixes
        -- stripped (IndicPiper.R:258's gsub("Root; |d__|p__|c__|o__|f__|g__", ...)
        -- inside runIndicPiper() itself, before it writes the output CSV) --
        -- t.full_name still has them (e.g. "d__Archaea; p__X; ..."), so an exact
        -- match against the raw name always misses. Strip the same way here.
        regexp_replace(t.full_name, 'd__|p__|c__|o__|f__|g__', '', 'g') AS genus,
        cp.relative_abundance
    FROM condensed_profiles cp
    JOIN taxonomies t ON t.id = cp.taxonomy_id
    WHERE cp.taxonomy_type = 'gtdb' AND t.taxonomy_level = 'genus'
""")

scores = con.execute("""
    SELECT g.run_id, i.Habitat, sum(g.relative_abundance) AS score
    FROM genus_long g
    JOIN indicators i ON i.Taxonomy = g.genus
    GROUP BY g.run_id, i.Habitat
""").df()

n_samples = con.execute(
    "SELECT count(DISTINCT run_id) FROM condensed_profiles WHERE taxonomy_type='gtdb'"
).fetchone()[0]
n_habitats = ind["Habitat"].nunique()
dense_cells = n_samples * n_habitats

print("Nonzero (sample, habitat) score rows:", len(scores))
print("Dense matrix would be:", dense_cells, "cells")
print("Sparsity (nonzero / dense):", round(len(scores) / dense_cells * 100, 2), "%")
print()
per_sample = scores.groupby("run_id").size()
print("Habitats per sample (median/mean):", per_sample.median(), "/", round(per_sample.mean(), 2))
print("Samples with >=1 nonzero habitat score:", scores["run_id"].nunique(), "of", n_samples)
