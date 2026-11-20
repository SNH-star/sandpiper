// Facts about the IndicPiper indicator set the pages quote, read from the data file (written by
// backend/bin/export_indicpiper_genera.py) so a new IndicPiper version changes the text without editing it.
import indicator from '@/constants/indicpiperGenera.json'

export const INDICATOR_GENERA_BY_HABITAT = indicator.habitats
export const INDICPIPER_VERSION = indicator.version
export const INDICATORS_DEFINED_FROM = indicator.defined_from
export const HABITAT_COUNT = Object.keys(indicator.habitats).length
export const INDICATOR_GENUS_COUNT = Object.values(indicator.habitats).reduce((total, genera) => total + genera.length, 0)
