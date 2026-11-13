"""Which runs get an IndicPiper warning, for the Statistics page's coverage bar.

Mirrors the two warnings a run page shows (vue/src/utils/indicpiper.js): the
organism names no habitat IndicPiper was built from, or the strongest habitat
signal disagrees with the habitat the organism label names. Keep the habitat
table below in step with that file.
"""
import re
from typing import Dict, Optional, Tuple

# Only explicit habitat labels are compared; ambiguous organism names are omitted.
RECORDED_HABITATS: Dict[str, str] = {
    'soil metagenome': 'soil',
    'wastewater metagenome': 'wastewater',
    'human oral metagenome': 'human oral',
    'human saliva metagenome': 'human oral',
    'human skin metagenome': 'human skin',
    'human vaginal metagenome': 'human vaginal',
    'marine sediment metagenome': 'marine sediment',
    'glacier metagenome': 'glacier',
    'hydrothermal vent metagenome': 'hydrothermal vent',
    'freshwater sediment metagenome': 'freshwater sediment',
    'freshwater metagenome': 'freshwater water',
    'freshwater water metagenome': 'freshwater water',
    'phyllosphere metagenome': 'phyllosphere',
    'rhizosphere metagenome': 'soil',
    **{f'{host} gut metagenome': 'mammalian gut'
       for host in ('human', 'pig', 'bovine', 'sheep', 'canine', 'goat', 'mammalian')},
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
