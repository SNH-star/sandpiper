"""
bioproject_similarity.py
- Compares one run's fields with the other runs of its BioProject, so run
  pages can show how much of the information is shared and star the fields
  that are unique to this run. Pure functions: callers decide which fields to
  pass in.
"""
import math
from collections import Counter
from typing import Any, Mapping, Sequence


def _normalise(value: Any) -> Any:
    """Comparison key for a value, or None when it is blank."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text == '':
        return None
    try:
        number = float(text)
    except ValueError:
        return text
    return number if math.isfinite(number) else text


def _modal_values(peers: Sequence[Mapping[str, Any]], field: str) -> set:
    counts = Counter(
        key for key in (_normalise(peer.get(field)) for peer in peers) if key is not None)
    if not counts:
        return set()
    top = max(counts.values())
    return {key for key, n in counts.items() if n == top}


def compare_to_peers(run: Mapping[str, Any], peers: Sequence[Mapping[str, Any]]) -> dict | None:
    """Share of `run`'s fields that agree with the other runs of its BioProject.

    A field is shared when the run's value equals the most common value among
    the peers. Fields blank on the run, or on every peer, are not comparable
    and are ignored. `n_fields` is every comparable field, so the percentage
    covers exactly the fields that can be starred. Returns None when there is
    nothing to compare against.
    """
    if not peers:
        return None
    unique_fields = []
    n_fields = 0
    for field, value in run.items():
        key = _normalise(value)
        modal = _modal_values(peers, field)
        if key is None or not modal:
            continue
        n_fields += 1
        if key not in modal:
            unique_fields.append(field)
    if n_fields == 0:
        return None
    return {
        'n_other_runs': len(peers),
        'n_fields': n_fields,
        'percent_shared': round(100 * (n_fields - len(unique_fields)) / n_fields),
        'unique_fields': unique_fields,
    }
