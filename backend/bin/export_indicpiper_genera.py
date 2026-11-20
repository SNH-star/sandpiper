#!/usr/bin/env python3
"""Write the About page's list of IndicPiper indicator genera, grouped by habitat.

Reads IndicPiper's own indicator table (the submodule's genus_habitat_indicators_v*.csv) and writes
vue/src/constants/indicpiperGenera.json: {version, defined_from, habitats: {habitat: [{genus, phylum, indval}]}}, strongest
IndVal first. The About and Run pages read their IndicPiper version and counts from it.
Run again, with the new CSV, whenever the IndicPiper version changes.
"""
import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / 'indicpiper_custom/IndicPiper/genus_habitat_indicators_v2.1.0.csv'
DEFAULT_OUT = ROOT / 'vue/src/constants/indicpiperGenera.json'
INDVAL_DECIMALS = 3
# The Sandpiper release whose community profiles the indicator genera were defined from.
DEFINED_FROM = '2.1.1'


def genera_by_habitat(rows) -> dict[str, list[dict]]:
    """Group indicator rows by habitat; each row's Taxonomy is 'Domain; Phylum; ...; Genus'."""
    habitats: dict[str, list[dict]] = {}
    for row in rows:
        ranks = [rank.strip() for rank in row['Taxonomy'].split(';')]
        habitats.setdefault(row['Habitat'], []).append({
            'genus': ranks[-1], 'phylum': ranks[1] if len(ranks) > 1 else '',
            'indval': round(float(row['IndVal_mean']), INDVAL_DECIMALS)})
    return {habitat: sorted(genera, key=lambda g: (-g['indval'], g['genus'])) for habitat, genera in sorted(habitats.items())}


def version_of(csv_path: Path) -> str:
    """The IndicPiper version in the file name, e.g. genus_habitat_indicators_v2.1.0.csv -> 2.1.0."""
    match = re.search(r'_v(\d+(?:\.\d+)*)\.csv$', csv_path.name)
    if not match:
        raise SystemExit(f'No version in the file name: {csv_path.name}')
    return match.group(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=DEFAULT_CSV)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--defined-from', default=DEFINED_FROM, help='Sandpiper release the genera were defined from')
    args = parser.parse_args()
    with open(args.csv, newline='') as handle:
        habitats = genera_by_habitat(csv.DictReader(handle))
    result = {'version': version_of(args.csv), 'defined_from': args.defined_from, 'habitats': habitats}
    args.out.write_text(json.dumps(result, indent=1) + '\n')
    print(f'IndicPiper {result["version"]}: {sum(len(g) for g in habitats.values())} genera in {len(habitats)} habitats -> {args.out}')


if __name__ == '__main__':
    main()
