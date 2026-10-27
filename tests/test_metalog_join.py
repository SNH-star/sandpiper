import gzip
import os
import sys

import pytest

SCRIPTS = os.path.join(os.path.dirname(__file__), '..', 'metalog_custom', 'scripts')
sys.path.insert(0, SCRIPTS)

import join_metadata  # noqa: E402
import metalog_config  # noqa: E402

METALOG_HEADER = ['spire_sample_name', 'ph', 'host']


def _write_gz(path, header, rows):
    with gzip.open(path, 'wt') as f:
        f.write('\t'.join(header) + '\n')
        for row in rows:
            f.write('\t'.join(row) + '\n')


def _write_tsv(path, header, rows):
    with open(path, 'w') as f:
        f.write('\t'.join(header) + '\n')
        for row in rows:
            f.write('\t'.join(row) + '\n')


@pytest.fixture()
def metalog_files(tmp_path):
    """Four tiny metalog files, one biosample each (SAMEA1 .. SAMEA4)."""
    paths = {}
    for i, category in enumerate(metalog_config.CATEGORIES, start=1):
        path = tmp_path / metalog_config.WIDE_FILE_TEMPLATE.format(category)
        _write_gz(path, METALOG_HEADER, [['SAMEA%d' % i, '7.%d' % i, 'host%d' % i]])
        paths[category] = str(path)
    return paths


def test_relative_config_paths_resolve_against_the_config_directory(tmp_path):
    cfg_dir = tmp_path / 'nested' / 'conf'
    cfg_dir.mkdir(parents=True)
    config = cfg_dir / 'config.yml'
    config.write_text("OUTPUT_DIR: 'outputs'\nMETALOG_DOWNLOAD_DIR: '../dl'\n"
                      "KINGFISHER_METADATA: '/abs/kf.tsv'\n")
    cfg = metalog_config.load_config(str(config))
    assert cfg['OUTPUT_DIR'] == str(cfg_dir / 'outputs')
    assert cfg['METALOG_DOWNLOAD_DIR'] == str(tmp_path / 'nested' / 'dl')
    assert cfg['KINGFISHER_METADATA'] == '/abs/kf.tsv'   # absolute paths are untouched


def test_download_dir_override_sets_all_four_wide_file_paths():
    cfg = metalog_config.apply_download_dir({}, '/scratch/x/downloads')
    assert cfg['METALOG_DOWNLOAD_DIR'] == '/scratch/x/downloads'
    assert cfg['METALOG_OCEAN'] == '/scratch/x/downloads/ocean_extended_wide_latest.tsv.gz'
    assert set(k for k in cfg if k.startswith('METALOG_') and k != 'METALOG_DOWNLOAD_DIR') == {
        'METALOG_ANIMAL', 'METALOG_ENVIRONMENTAL', 'METALOG_HUMAN', 'METALOG_OCEAN'}


def test_join_streams_several_kingfisher_files_with_different_headers(tmp_path, metalog_files):
    # Real kingfisher chunks each have their own column set; only run + biosample are shared.
    chunk_a = tmp_path / 'a.tsv'
    chunk_b = tmp_path / 'b.tsv'
    _write_tsv(chunk_a, ['run', 'biosample', 'extra_a'],
               [['SRR1', 'SAMEA1', 'x'], ['SRR2', 'NOPE', 'y']])
    _write_tsv(chunk_b, ['biosample', 'other_b', 'run'],
               [['SAMEA3', 'z', 'SRR3']])
    file_list = tmp_path / 'files.txt'
    file_list.write_text('%s\n%s\n' % (chunk_a, chunk_b))

    metalog, cols = join_metadata.load_metalog(metalog_files)
    slim = tmp_path / 'slim.tsv'
    join_metadata.join_and_write(join_metadata.read_file_list(str(file_list)), metalog, cols,
                                 None, str(slim))

    lines = slim.read_text().splitlines()
    assert lines[0].split('\t') == ['run', 'meta_host', 'meta_ph']
    assert sorted(l.split('\t')[0] for l in lines[1:]) == ['SRR1', 'SRR3']   # SRR2 has no metalog match


def test_full_output_refuses_files_whose_headers_differ(tmp_path, metalog_files):
    chunk_a = tmp_path / 'a.tsv'
    chunk_b = tmp_path / 'b.tsv'
    _write_tsv(chunk_a, ['run', 'biosample', 'col_a'], [['SRR1', 'SAMEA1', 'x']])
    _write_tsv(chunk_b, ['run', 'biosample', 'col_b'], [['SRR3', 'SAMEA3', 'z']])
    metalog, cols = join_metadata.load_metalog(metalog_files)
    with pytest.raises(SystemExit, match='headers differ'):
        join_metadata.join_and_write([str(chunk_a), str(chunk_b)], metalog, cols,
                                     str(tmp_path / 'full.tsv'), str(tmp_path / 'slim.tsv'))


def test_single_file_mode_still_writes_full_and_slim(tmp_path, metalog_files):
    chunk = tmp_path / 'one.tsv'
    _write_tsv(chunk, ['run', 'biosample', 'col'], [['SRR1', 'SAMEA2', 'x'], ['SRR2', 'NOPE', 'y']])
    metalog, cols = join_metadata.load_metalog(metalog_files)
    full, slim = tmp_path / 'full.tsv', tmp_path / 'slim.tsv'
    join_metadata.join_and_write([str(chunk)], metalog, cols, str(full), str(slim))
    assert len(full.read_text().splitlines()) == 3          # header + both runs
    assert len(slim.read_text().splitlines()) == 2          # header + matched run only
