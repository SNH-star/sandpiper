#!/usr/bin/env bash
# Rebuilds vue/src/constants/groupSummaries.json (Statistics page panels c-e).
# Streams the 5.3 GB condensed table once, so expect it to take a while.
set -euo pipefail
cd "$(dirname "$0")/../.."

KINGFISHER=snakemake/prod/kingfisher_metadata/20261026
# The website database, opened read-only, for the most widely detected taxa of each group.
DB=${SANDPIPER_DB:-backend/db/sandpiper_43.duckdb}

python3 backend/bin/summarise_groups.py \
  --db "$DB" \
  vue/src/constants/groupSummaries.json \
  backend/db/metagenome_assembly_acc_list.csv \
  snakemake/data/per_acc_summary.weebill.csv \
  "$KINGFISHER/parsed_metadata.tsv" \
  "$KINGFISHER/metadata_chunks" \
  snakemake/data/condensed.weebill.csv.gz \
  data/gtdb_r232/bac120_metadata_r232.tsv.gz \
  data/gtdb_r232/ar53_metadata_r232.tsv.gz
