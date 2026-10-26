# Per-run IndicPiper habitat chart with genus-level breakdown

Date: 2026-08-31
Status: implemented 2026-09-01, verified against backend/db/sandpiper_40.duckdb

## Problem

The "IndicPiper habitat indicators" section on a run's page
(`vue/src/components/RunMetadata.vue`) currently shows a plain
`RunMetadataTable` list: habitat name and a single summed score, e.g.
`soil: 0.015`. It gives no sense of *which* genera are actually driving
that number for this specific run, and a flat number list undersells what's
actually a rich per-genus signal.

The user wants this replaced with a horizontal stacked-bar visualization,
one bar per habitat this run matched, each bar's segments showing the
contributing genera, with a hover/focus tooltip revealing the full
genus-by-genus percentage breakdown (reference image: a generic SaaS-style
"Genera breakdown by environment" chart, restyled to Sandpiper's own theme
and using real per-run IndicPiper data instead of a fixed generic legend).

## Key finding: no new computation needed

`add_indicpiper_scores()` in `backend/bin/generate_backend_db` already
computes each individual genus's `relative_abundance` for a run, inside the
subquery that currently feeds both `score` (via `sum()`) and `genera` (via
`string_agg()`, names only, no percentages). That per-genus value is
discarded the moment `GROUP BY g.run_id, i.habitat` collapses it. Persisting
it instead of discarding it is a small addition to a stage that already
exists and already runs this exact query -- not a new join, not a new data
source, not new per-request computation.

## Design

### 1. Data model: a proper child table, not a packed string

Add `indicator_habitat_genus_scores(run_id, habitat, genus,
relative_abundance)` -- one row per nonzero (run, habitat, genus) triple.
Same sparse-table convention already used throughout this schema
(`Tag`/`RunTag`, and `IndicatorHabitatScore` itself -- see their docstrings
in `api/models.py`). `indicator_habitat_scores.score` remains the sum (bar
length); the new child table drives the stacked segments and tooltip.

`add_indicpiper_scores()`'s existing query already produces exactly these
values before its `GROUP BY`. The new table's `INSERT` reuses the same
`FROM`/`JOIN` (condensed_profiles joined to taxonomies, joined to the
IndicPiper submodule's indicator CSV), just without collapsing per-genus
rows:

```sql
INSERT INTO indicator_habitat_genus_scores (run_id, habitat, genus, relative_abundance)
SELECT g.run_id, i.habitat, g.genus_name, g.relative_abundance
FROM (
    -- same per-(run, genus) relative_abundance subquery already used for
    -- score/genera above
) g
JOIN indicpiper_indicators i ON i.taxonomy = g.genus
WHERE g.relative_abundance > 0
```

Runs alongside the existing `INSERT INTO indicator_habitat_scores` in the
same function -- both read from the same underlying data, computed once.
The existing `genera` string column on `indicator_habitat_scores` (added
earlier this session) becomes redundant once this lands, since it's now a
strictly-lossy derivative of the new child table -- worth removing at
implementation time rather than maintaining two representations of the same
information; the API layer would compute a "top genera, comma-joined"
summary from the child table on the rare path that still needs one (e.g.
older-database fallback, see below).

### 2. API (`backend/api/api.py`)

`indicpiper_rows(run_id)` gets richer: for each matched habitat, also
attach that habitat's genus breakdown (name + relative_abundance, sorted
descending) from the new child table, so the frontend gets everything it
needs for both the bar and the tooltip in one response, no second request.

Compatibility: the same "check the table/column exists before querying it"
pattern already implemented for `genera` this session applies here too --
a database built before `indicator_habitat_genus_scores` existed should
degrade to the old flat (habitat, score) view rather than erroring, exactly
like the existing `_indicator_habitat_scores_has_genera()` guard (which,
per the finding above, should become
`_indicator_habitat_genus_scores_exists()` checking for the new table
instead, once the child table replaces the `genera` column).

### 3. Frontend

New component, e.g. `vue/src/components/IndicPiperHabitatChart.vue`,
replacing the current `RunMetadataTable` usage in the "IndicPiper habitat
indicators" section of `RunMetadata.vue`. One horizontal stacked bar per
habitat this run matched (typically a handful, not all 13 -- same sparsity
as today), bar length = habitat score, segments = that habitat's
contributing genera. Color palette via `d3.scaleOrdinal` (d3 is already a
dependency, used hand-rolled in `Sunburst3.vue` -- no new library needed),
styled to the site's existing turquoise/serif theme
(`vue/src/assets/scss/_variables.scss`), not the reference image's generic
palette. Small per-habitat line icons are an optional v2 polish item, out
of scope for the first implementation.

### 4. Accessibility

Hover-only genus detail isn't enough on its own. Reuse the existing
info-icon "toggle details" pattern already in `RunMetadataTable.vue`: each
bar gets a focusable trigger that expands an inline text region with the
same genus/percentage list, so keyboard users and screen readers get the
same information a mouse-hover would reveal -- no new interaction pattern
invented, just the one already established elsewhere on this page.

## Non-goals

- No global/database-wide aggregate chart (e.g. on About or Home) -- this
  is per-run only, specific to each run's own page.
- No custom habitat icons in the first pass.
- No change to how `score` itself is computed (still the sum of indicator
  genera's relative abundance).

## Status: implemented

Implemented 2026-09-01 once `sandpiper_40.duckdb` was available:
`indicator_habitat_genus_scores` (`backend/api/models.py`,
`add_indicpiper_scores()` in `backend/bin/generate_backend_db`), the richer
`indicpiper_rows()` in `backend/api/api.py`, and
`vue/src/components/IndicPiperHabitatChart.vue` replacing the flat table in
`RunMetadata.vue`. The `genera` string column on `indicator_habitat_scores`
was dropped as planned. See Verification below for what was checked.

## Verification (once implemented)

- `add_indicpiper_scores()`: after a build, confirm
  `indicator_habitat_genus_scores` has a row per nonzero (run, habitat,
  genus) triple, and that summing `relative_abundance` per (run, habitat)
  matches `indicator_habitat_scores.score` for the same pair (sanity check
  that the two tables agree, since both derive from the same underlying
  query).
- API: hit a run's metadata endpoint, confirm each matched habitat's
  response includes a genus breakdown that sums to (approximately) that
  habitat's score.
- Frontend: visually confirm bar segment widths are proportional to each
  genus's share of the habitat's total, tooltip/expanded-detail content
  matches the API's genus list exactly, and keyboard-only navigation can
  reach the same detail a mouse hover shows.
