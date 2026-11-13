#!/usr/bin/env bash
# Same inputs as run_summarise_groups.sh, written to a side file so it can be checked before it replaces the real one.
set -euo pipefail
cd "$(dirname "$0")/../.."
KINGFISHER=snakemake/prod/kingfisher_metadata/20261026
python3 backend/bin/summarise_groups.py \
  backend/db/groupSummaries.new.json \
  backend/db/metagenome_assembly_acc_list.csv \
  snakemake/data/per_acc_summary.weebill.csv \
  "$KINGFISHER/parsed_metadata.tsv" \
  "$KINGFISHER/metadata_chunks" \
  snakemake/data/condensed.weebill.csv.gz \
  data/gtdb_r232/bac120_metadata_r232.tsv.gz \
  data/gtdb_r232/ar53_metadata_r232.tsv.gz
