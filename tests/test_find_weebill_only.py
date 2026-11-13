"""bin/find_weebill_only.py: runs Weebill introduced, i.e. in its table but with no SingleM marker-gene hits."""
import gzip
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'bin'))

import find_weebill_only  # noqa: E402

MORE_RUNS = os.path.join(os.path.dirname(__file__), '..', 'test', 'data', 'more_runs')
WEEBILL_HEADER = 'sample\tcoverage\ttaxonomy\n'
OTU_HEADER = 'gene\tsample\tsequence\tnum_hits\tcoverage\ttaxonomy\n'


def _gz(path, text):
    with gzip.open(str(path), 'wt') as handle:
        handle.write(text)
    return str(path)


def test_runs_only_in_the_weebill_table_are_the_ones_it_introduced():
    assert find_weebill_only.weebill_only_accessions({'A', 'B', 'C'}, {'B'}) == ['A', 'C']


def test_runs_with_marker_hits_are_never_listed_and_the_result_is_sorted_without_repeats():
    assert find_weebill_only.weebill_only_accessions({'SRR2', 'ERR1', 'SRR1'}, {'SRR1', 'XXX'}) == ['ERR1', 'SRR2']
    assert find_weebill_only.weebill_only_accessions(set(), {'A'}) == []
    assert find_weebill_only.weebill_only_accessions({'A'}, {'A'}) == []


def test_samples_are_read_from_the_sample_column_whatever_its_position(tmp_path):
    weebill = _gz(tmp_path / 'w.csv.gz', WEEBILL_HEADER + 'A\t1.0\tRoot; d__Bacteria\nA\t2.0\tRoot; d__Archaea\nB\t3.0\tRoot\n')
    otu = _gz(tmp_path / 'o.csv.gz', OTU_HEADER + 'g1\tB\tACGT\t1\t1.0\tRoot\n')
    assert find_weebill_only.read_samples(weebill) == {'A', 'B'}
    assert find_weebill_only.read_samples(otu) == {'B'}


def test_a_file_without_a_sample_column_is_refused_with_a_clear_message(tmp_path):
    bad = _gz(tmp_path / 'bad.csv.gz', 'gene\tcoverage\nx\t1\n')
    with pytest.raises(ValueError, match='sample'):
        find_weebill_only.read_samples(bad)


def test_the_script_writes_one_accession_per_line_and_reports_the_counts(tmp_path, capsys):
    weebill = _gz(tmp_path / 'w.csv.gz', WEEBILL_HEADER + 'A\t1\tRoot\nB\t1\tRoot\nC\t1\tRoot\n')
    otu = _gz(tmp_path / 'o.csv.gz', OTU_HEADER + 'g\tB\tACGT\t1\t1\tRoot\n')
    out = tmp_path / 'only.txt'
    counts = find_weebill_only.main([weebill, otu, str(out)])
    assert out.read_text().splitlines() == ['A', 'C']
    assert counts == {'weebill_runs': 3, 'singlem_runs': 1, 'weebill_only': 2}
    assert '2' in capsys.readouterr().out


def test_the_shipped_test_tables_give_the_same_answer_as_a_plain_python_reading():
    def samples(name):
        with gzip.open(os.path.join(MORE_RUNS, name), 'rt') as handle:
            header = handle.readline().rstrip('\n').split('\t')
            column = header.index('sample')
            return {line.split('\t')[column] for line in handle if line.strip()}

    expected = sorted(samples('condensed.csv.gz') - samples('otu_table.csv.gz'))
    got = find_weebill_only.weebill_only_accessions(
        find_weebill_only.read_samples(os.path.join(MORE_RUNS, 'condensed.csv.gz')),
        find_weebill_only.read_samples(os.path.join(MORE_RUNS, 'otu_table.csv.gz')))
    assert got == expected
