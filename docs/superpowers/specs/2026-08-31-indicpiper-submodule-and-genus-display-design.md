# IndicPiper as a real dependency, with genus-level detail on habitat scores

Date: 2026-08-31
Status: approved, pending implementation plan

## Problem

Sandpiper currently regenerates its own IndicPiper habitat-indicator
database from the live Sandpiper duckdb (`indicpiper_custom/scripts/
build_indicpiper_inputs.py` + `run_indicpiper.R`), producing a data-driven
habitat set (25-30 habitats depending on `MIN_HABITAT_SAMPLES`/
`N_HABITATS`) instead of the 13 habitats IndicPiper's own upstream
maintainer curated and published. This throws away curation the upstream
project already did, and requires an expensive 8+ hour, 300GB regeneration
job on every Sandpiper build.

Separately, `indicator_habitat_scores` (the table backing the "IndicPiper
habitat indicators" section on a run's page) stores only a summed score per
`(run_id, habitat)` pair -- which genera actually contributed to that sum is
discarded during the build-time `SUM(relative_abundance) ... GROUP BY
run_id, habitat` aggregation, so the UI can show e.g. "soil: 0.015" but not
which indicator genera (e.g. `Aquipseudomonas`) are actually present in that
sample.

Also, `indicpiper_custom/IndicPiper/` is a nested git checkout of
`https://github.com/cliffbueno/IndicPiper` that `.gitmodules` already
declares as a submodule, but the gitlink was never actually committed to
the parent repo -- `git status` shows it as an untracked plain directory,
not a submodule reference. There's no deliberate mechanism for pulling a
future upstream release.

## Goals

1. Use IndicPiper's own shipped, curated 13-habitat indicator database
   instead of regenerating one from Sandpiper's own data.
2. Make IndicPiper a properly tracked git submodule, so pulling a future
   upstream release is a deliberate, reproducible `git submodule
   update --remote` + commit, not a manual file copy.
3. Show which indicator genera are actually present (by relative
   abundance) next to each habitat's score on a run's page.

## Non-goals

- Keeping the regenerate-from-Sandpiper-data pipeline as part of the
  automated build. It remains available as opt-in manual tooling only.
- Changing how the per-habitat score itself is computed (still the sum of
  `condensed_profiles.relative_abundance` over that habitat's indicator
  genera, for genera present in the run).
- Any frontend code change. The existing detail-expand row in
  `RunMetadataTable.vue` already renders a free-text `description` field;
  the genus list is appended there.

## Design

### 1. Register `indicpiper_custom/IndicPiper` as a real git submodule

`.gitmodules` already has the correct entry (path
`indicpiper_custom/IndicPiper`, url
`https://github.com/cliffbueno/IndicPiper.git`); the working tree is
already checked out at the right commit (`6099836`, 11 commits past the
`v2.0.0` tag -- all README/CI additions, no CSV changes). The only missing
step is committing the gitlink: `git add indicpiper_custom/IndicPiper`.

Future upstream updates: `git submodule update --remote
indicpiper_custom/IndicPiper && git add indicpiper_custom/IndicPiper && git
commit`. No other repo change is required for this to take effect (see
next section).

### 2. Snakefile consumes the submodule's CSV directly, no regeneration

`snakemake/Snakefile` currently has `INDICPIPER_OUTPUT_CSV` point at a
per-version scratch file produced by `build_indicpiper_metadata` ->
`build_indicpiper_genus` -> `run_indicpiper`. Replace this with a glob over
`indicpiper_custom/IndicPiper/genus_habitat_indicators_v*.csv`, selecting
the highest version number found. This means a future submodule bump that
ships a `v3.csv` is picked up automatically, with no Snakefile edit.

Remove `build_indicpiper_metadata`, `build_indicpiper_genus`, and
`run_indicpiper` from the rule graph entirely (they stay defined in
`indicpiper_custom/scripts/` and `config.yml` for optional manual use, but
nothing in the automated build calls them). `add_indicpiper_scores_to_backend_db`
now depends only on `parsed_metadata_done` (plus the submodule's checked-out
CSV, which is part of the repo, not a build product).

`snakemake/prod_config.yml`: remove `INDICPIPER_N_HABITATS` (no longer
read by anything). `INCLUDE_INDICPIPER` keeps its existing on/off meaning
(off = copy the db forward unchanged, matching every other optional stage's
contract).

`indicpiper_custom/config.yml`: re-comment as manual/optional tooling for
regenerating a custom indicator set from Sandpiper's own data, explicitly
noting it is no longer invoked by the Snakefile.

### 3. Guard against a future GTDB-version mismatch

`add_indicpiper_scores()` in `backend/bin/generate_backend_db` joins the
indicator CSV's `Taxonomy` string against `taxonomies.full_name` (rank
prefixes stripped) by exact string match. This only works when the
IndicPiper CSV and Sandpiper's own `condensed_profiles` were built against
the same GTDB release. A future submodule bump to an IndicPiper version
built on a newer GTDB release than Sandpiper's own would silently produce
a near-empty (or empty) `indicator_habitat_scores` table -- the join would
just fail to match most rows, with no error.

After the insert, compare the number of distinct indicator taxa that
matched at least one genus in `taxonomies` against the total distinct
taxa in the CSV. If the matched fraction is implausibly low (e.g. under
50%), raise an exception naming the likely cause (GTDB version mismatch
between the IndicPiper submodule and this Sandpiper build's own taxonomy)
instead of silently continuing.

### 4. Genus-level detail on habitat scores

`genus_habitat_indicators_v2.csv` has no separate `Genus` column, only the
full `Taxonomy` lineage (e.g. `Bacteria; Pseudomonadota; ...;
Aquipseudomonas`). Derive the terminal genus name as the last
`;`-delimited segment of `Taxonomy`.

Schema change: add `genera VARCHAR` to `indicator_habitat_scores`
(`backend/api/models.py`).

Build-time change: in `add_indicpiper_scores()`'s existing `INSERT ...
GROUP BY g.run_id, i.habitat` query, alongside `sum(g.relative_abundance)
AS score`, add `string_agg(genus_name, ', ' ORDER BY g.relative_abundance
DESC) AS genera`, where `genus_name` is the last `;`-segment of the
stripped taxonomy string. This is computed in the same aggregation pass,
so no new table and no extra query at read time.

API change: `indicpiper_rows()` in `backend/api/api.py` appends the genus
list to the existing `description` string, e.g.:

> Summed relative abundance, in this run, of the genera IndicPiper
> identified as indicators of the "soil" habitat. Indicator genera present
> in this run, by abundance: Aquipseudomonas, Bacillus, ...

No frontend change: `RunMetadataTable.vue`'s existing detail-expand row
already renders `description` as free text.

## Testing / verification

No existing pytest suite covers this backend code path. Verification is
manual, against a real (or representative sample of) duckdb build:

- After registering the submodule: `git submodule status` shows a clean,
  committed gitlink (no `-`/`+` prefix).
- After the Snakefile change: `snakemake -n` (dry run) shows
  `add_indicpiper_scores_to_backend_db` no longer depends on
  `run_indicpiper_done`, and resolves `INDICPIPER_OUTPUT_CSV` to the
  submodule's `genus_habitat_indicators_v2.csv`.
- After the `generate_backend_db` change: run `--stage indicpiper` against
  a test/small duckdb and confirm `indicator_habitat_scores` has exactly
  13 distinct habitat values, `genera` is populated (non-null, comma
  list) for every row, and the sanity-check guard doesn't fire on a
  matching-version build.
- Spot-check one real run's `indicpiper_rows()` output via
  `GET /run/<accession>` (or equivalent) and confirm the description text
  lists genus names, matching what's independently computable from
  `condensed_profiles` for that run and habitat.

## Open questions / risks

- None blocking. The sanity-check threshold (50%) in section 3 is a
  starting guess; if it fires spuriously on a legitimate build, loosen it
  based on the actual matched fraction observed on a real GTDB-version
  match.
