# Sanity-checks runIndicPiper()'s output via IndicPiper.R's own
# checkIndicPiper(): re-derives per-habitat indicator abundances from the
# last iteration's saved meta_test.csv/genus_test.csv (written by
# runIndicPiper() itself) and checks that each habitat's indicator genera
# are actually more abundant "on target" than everywhere else.
#
# Usage (from indicpiper_custom/IndicPiper/, so IndicPiper.R's relative
# source() calls, checkIndicPiper()'s relative defaults (meta_test.csv,
# genus_test.csv, genus_habitat_indicators_custom.csv), and the pixi env
# resolve correctly):
#   pixi run Rscript ../scripts/check_indicpiper.R

source("IndicPiper.R")

checkIndicPiper()

cat("Done. Target-vs-off-target abundance summary printed above; ",
    "boxplot written to IndicPiper_SummedAbund.pdf. A real signal looks ",
    "like 'target' medians clearly higher than 'non-indicator'/'off-target' ",
    "ones per habitat -- if they're indistinguishable, the indicator table ",
    "is not trustworthy as-is.\n", sep = "")
