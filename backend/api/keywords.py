"""
keywords.py
- Shared parsing for the `keywords:` search key (metagenome and amplicon).

A keywords value is comma-separated terms. Each term is an exact phrase that
must appear in at least one searched field, and every term must match, so a
sample that hits in several fields is still one result.
"""

MAX_KEYWORD_TERMS = 10


def parse_keyword_terms(value: str) -> list[str]:
    """'sponge reef, coral' -> ['sponge reef', 'coral'] (blanks and repeats dropped)."""
    terms, seen = [], set()
    for raw in value.split(','):
        term = raw.strip()
        if term and term.lower() not in seen:
            seen.add(term.lower())
            terms.append(term)
    return terms[:MAX_KEYWORD_TERMS]


LIKE_ESCAPE = '!'  # not a backslash: DuckDB rejects `ESCAPE '\\'` as a two-character escape


def like_pattern(term: str) -> str:
    """Substring LIKE pattern for `term` with its own wildcards escaped (escape char: LIKE_ESCAPE)."""
    escaped = (term.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
               .replace('%', LIKE_ESCAPE + '%').replace('_', LIKE_ESCAPE + '_'))
    return f'%{escaped}%'
