#!/usr/bin/env python

#=======================================================================
# Unit tests for extend_parsed_metadata.py
#=======================================================================

import unittest
import os.path
import tempfile
import extern

script = os.path.join(os.path.dirname(__file__), '../extend_parsed_metadata.py')


def write(path, rows):
    with open(path, 'w') as f:
        for row in rows:
            f.write('\t'.join(row) + '\n')


def read(path):
    with open(path) as f:
        return [line.rstrip('\n').split('\t') for line in f]


class Tests(unittest.TestCase):
    def _run(self, parsed_rows, ext_rows):
        with tempfile.TemporaryDirectory() as d:
            parsed = os.path.join(d, 'parsed.tsv')
            ext = os.path.join(d, 'ext.tsv')
            out = os.path.join(d, 'out.tsv')
            write(parsed, parsed_rows)
            write(ext, ext_rows)
            extern.run(
                f'{script} --parsed-metadata {parsed} '
                f'--metalog-extension {ext} --output {out}')
            return read(out)

    def test_appends_meta_columns_and_keeps_native(self):
        parsed = [
            ['run', 'latitude', 'collection_year'],
            ['ERR1', '-42.0', '2014'],
            ['ERR2', '10.5', '2018'],
        ]
        ext = [
            ['run', 'meta_sex', 'meta_environment_biome'],
            ['ERR1', 'male', 'soil'],
            ['ERR2', 'female', 'marine'],
        ]
        out = self._run(parsed, ext)
        self.assertEqual(
            ['run', 'latitude', 'collection_year', 'meta_sex', 'meta_environment_biome'],
            out[0])
        # native values untouched, meta values appended
        self.assertEqual(['ERR1', '-42.0', '2014', 'male', 'soil'], out[1])
        self.assertEqual(['ERR2', '10.5', '2018', 'female', 'marine'], out[2])

    def test_run_absent_from_extension_gets_empty_meta(self):
        parsed = [
            ['run', 'latitude'],
            ['ERR1', '-42.0'],
            ['ERR_missing', '99.9'],
        ]
        ext = [
            ['run', 'meta_sex'],
            ['ERR1', 'male'],
        ]
        out = self._run(parsed, ext)
        self.assertEqual(['ERR1', '-42.0', 'male'], out[1])
        # run not in extension -> empty meta cell, native preserved
        self.assertEqual(['ERR_missing', '99.9', ''], out[2])

    def test_passthrough_when_no_extension(self):
        parsed = [
            ['run', 'latitude'],
            ['ERR1', '-42.0'],
        ]
        with tempfile.TemporaryDirectory() as d:
            parsed_path = os.path.join(d, 'parsed.tsv')
            out_path = os.path.join(d, 'out.tsv')
            write(parsed_path, parsed)
            extern.run(
                f'{script} --parsed-metadata {parsed_path} --output {out_path}')
            self.assertEqual(parsed, read(out_path))

    def test_column_name_collision_fails(self):
        parsed = [['run', 'meta_sex'], ['ERR1', 'x']]
        ext = [['run', 'meta_sex'], ['ERR1', 'male']]
        with self.assertRaises(Exception):
            self._run(parsed, ext)


if __name__ == '__main__':
    unittest.main()
