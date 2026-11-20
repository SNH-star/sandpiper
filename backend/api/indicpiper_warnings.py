"""Which runs get an IndicPiper warning, for the Statistics page's coverage bar.

Mirrors the two warnings a run page shows (vue/src/utils/indicpiper.js): the
organism names no habitat IndicPiper was built from, or the strongest habitat
signal disagrees with the habitat the organism label names.
"""
import re
from typing import Dict, Optional, Tuple

# Organism label -> IndicPiper habitat, from Table S4 of the IndicPiper paper (the exact strings its habitat search
# uses). The API image holds only backend/, so it cannot read the website's copy, vue/src/constants/
# indicpiperHabitats.json; tests/test_indicpiper_warnings.py fails if the two differ.
# Next release: read IndicPiper's own mapping instead.
RECORDED_HABITATS: Dict[str, str] = {
    # freshwater sediment
    'freshwater sediment metagenome': 'freshwater sediment',
    # freshwater water
    'aquatic metagenome': 'freshwater water',
    'freshwater metagenome': 'freshwater water',
    'lake water metagenome': 'freshwater water',
    'pond metagenome': 'freshwater water',
    'riverine metagenome': 'freshwater water',
    # glacier
    'glacier metagenome': 'glacier',
    'ice metagenome': 'glacier',
    # human oral
    'human oral metagenome': 'human oral',
    'human saliva metagenome': 'human oral',
    # human skin
    'human skin metagenome': 'human skin',
    # human vaginal
    'human vaginal metagenome': 'human vaginal',
    # hydrothermal vent
    'hydrothermal vent metagenome': 'hydrothermal vent',
    # mammalian gut
    'human gut metagenome': 'mammalian gut',
    'pig gut metagenome': 'mammalian gut',
    'bovine gut metagenome': 'mammalian gut',
    'sheep gut metagenome': 'mammalian gut',
    'goat gut metagenome': 'mammalian gut',
    # marine sediment
    'marine sediment metagenome': 'marine sediment',
    # marine water
    'marine metagenome': 'marine water',
    'seawater metagenome': 'marine water',
    # phyllosphere
    'phyllosphere metagenome': 'phyllosphere',
    # soil
    'soil metagenome': 'soil',
    'rhizosphere metagenome': 'soil',
    # wastewater
    'wastewater metagenome': 'wastewater',
}

NONE, UNCOVERED, EXPECTED = 'none', 'uncovered', 'expected'


def canonical_organism(organism: str) -> str:
    """The organism label as the run page compares it: lower case, single
    spaces, and nothing after the word "metagenome"."""
    text = re.sub(r'\s+', ' ', organism.lower().replace('_', ' ')).strip()
    return re.sub(r'(metagenome).*$', r'\1', text)


def classify_organism(organism: object) -> Tuple[str, Optional[str]]:
    """('none', None) for no usable label, ('uncovered', None) when it names no
    habitat IndicPiper covers, else ('expected', the habitat it names)."""
    if not isinstance(organism, str):
        return NONE, None
    canonical = canonical_organism(organism)
    if not canonical or canonical == 'unspecified':
        return NONE, None
    habitat = RECORDED_HABITATS.get(canonical)
    return (EXPECTED, habitat) if habitat else (UNCOVERED, None)


def mapped_organisms(run_counts: Dict[object, int]) -> Dict[str, str]:
    """organism label -> expected habitat, for the labels that name a covered habitat."""
    mapped = {}
    for organism in run_counts:
        kind, habitat = classify_organism(organism)
        if kind == EXPECTED:
            mapped[organism] = habitat
    return mapped


def count_cautions(run_counts: Dict[object, int], mismatched_runs: int) -> int:
    """Runs with a warning: every run whose label is uncovered, plus the runs
    whose strongest signal contradicts their (covered) label.

    run_counts: organism label -> runs with IndicPiper scores.
    """
    uncovered = sum(runs for organism, runs in run_counts.items() if classify_organism(organism)[0] == UNCOVERED)
    return uncovered + mismatched_runs
