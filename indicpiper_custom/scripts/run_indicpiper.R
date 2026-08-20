# Runs IndicPiper's runIndicPiper() against the tables built by
# build_indicpiper_inputs.py --phase genus, using the params it computed
# (n_per_habitat especially -- see config.yml for why this is data-derived
# rather than IndicPiper's fixed default of 250).
#
# Usage (from indicpiper_custom/IndicPiper/, so IndicPiper.R's relative
# source() calls and pixi env resolve correctly):
#   pixi run Rscript ../scripts/run_indicpiper.R ../outputs/run_params.R

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) {
  stop("Usage: Rscript run_indicpiper.R <path/to/run_params.R>")
}
source(args[1])   # defines: n_per_habitat, n_multipatt_perm, n_runs, run_cut,
                   # p_cut, IndVal_cut, seed, output_csv, meta_path, genus_path

source("IndicPiper.R")

# Belt-and-braces: build_indicpiper_inputs.py sorts myMetadataTable.csv.gz by
# `sample` in pandas and myGenusTable.csv.gz by `sampleID` in DuckDB
# separately. Confirm they actually agree before runIndicPiper() gets a
# chance to silently misalign rows (it only checks after loading both).
suppressMessages(library(data.table))
meta_check <- fread(meta_path, select = "sample")
genus_check_names <- fread(genus_path, select = "sampleID")
if (!identical(meta_check$sample, genus_check_names$sampleID)) {
  stop("myMetadataTable.csv.gz and myGenusTable.csv.gz sample order do not match. ",
       "Re-run build_indicpiper_inputs.py --phase genus.")
}
rm(meta_check, genus_check_names)

cat(sprintf(
  "Running runIndicPiper(n_per_habitat=%d, n_runs=%d, n_multipatt_perm=%d)\n",
  n_per_habitat, n_runs, n_multipatt_perm
))

runIndicPiper(
  meta = meta_path,
  genus = genus_path,
  n_multipatt_perm = n_multipatt_perm,
  n_runs = n_runs,
  n_per_habitat = n_per_habitat,
  run_cut = run_cut,
  p_cut = p_cut,
  IndVal_cut = IndVal_cut,
  seed = seed,
  output = output_csv
)

cat(sprintf("Done. Indicator table written to %s\n", output_csv))
cat("Next: checkIndicPiper() against meta_test.csv / genus_test.csv (written by ",
    "runIndicPiper() for its last iteration) to sanity-check before trusting this table.\n", sep = "")
