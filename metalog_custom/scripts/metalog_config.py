"""Shared config handling for the metalog_custom scripts.

Paths in config.yml may be relative; they are resolved against the directory
holding config.yml, so the repo can live anywhere (nothing is tied to one
checkout's absolute path). A build can also override the download and output
locations from the command line, which is how the Snakefile gives every build
its own version-scoped scratch directory.
"""

import os

import yaml

CATEGORIES = ('animal', 'environmental', 'human', 'ocean')
WIDE_FILE_TEMPLATE = '{}_extended_wide_latest.tsv.gz'

# Config keys whose values are filesystem paths.
PATH_KEYS = (
    'METALOG_DOWNLOAD_DIR',
    'METALOG_ANIMAL', 'METALOG_ENVIRONMENTAL', 'METALOG_HUMAN', 'METALOG_OCEAN',
    'KINGFISHER_METADATA',
    'OUTPUT_DIR',
)


def load_config(config_path):
    """Load config.yml, resolving any relative path against its directory."""
    with open(config_path) as f:
        cfg = yaml.safe_load(f) or {}
    base_dir = os.path.dirname(os.path.abspath(config_path))
    for key in PATH_KEYS:
        value = cfg.get(key)
        if value and not os.path.isabs(value):
            cfg[key] = os.path.normpath(os.path.join(base_dir, value))
    return cfg


def apply_download_dir(cfg, download_dir):
    """Point the download dir and the four wide-file paths at `download_dir`."""
    cfg['METALOG_DOWNLOAD_DIR'] = download_dir
    for category in CATEGORIES:
        cfg['METALOG_' + category.upper()] = os.path.join(
            download_dir, WIDE_FILE_TEMPLATE.format(category))
    return cfg
