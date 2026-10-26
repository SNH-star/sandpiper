"""
Download the latest SPIRE/Metalog extended-wide metadata files.

Metalog (https://metalog.embl.de) has no per-sample query API, and its
interactive site is bot-gated (Anubis). However the static bulk-download
endpoints serve stable "_latest" files that 302-redirect to the current dated
release, e.g.

    .../metadata/ocean_extended_wide_latest.tsv.gz
        -> .../metadata/ocean_extended_wide_2026-06-07.tsv.gz

We pull those "_latest" files instead of manually copying dated files, so the
join always runs against fresh metadata. The dated target each "_latest"
resolves to is recorded in a manifest alongside the downloads for provenance.

Run before join_metadata.py (the fetch_metalog/join_metalog_metadata rules in
../snakemake/Snakefile do this automatically).
"""

import argparse
import datetime
import gzip
import html
import json
import os
import re
import urllib.error
import urllib.request

import yaml

# Categories Metalog publishes; each has a matching wide file in config.
CATEGORIES = ('animal', 'environmental', 'human', 'ocean')

DEFAULT_BASE_URL = 'https://metalog.embl.de/static/download/metadata'
DEFAULT_SITE_URL = 'https://metalog.embl.de/'
# Metalog states its release date and per-category sample totals on its home
# page; both are plain server-rendered text, so a fetch here keeps Sandpiper's
# About page in step with Metalog instead of relying on hand-transcription.
RELEASE_DATE_RE = re.compile(r'Last metadata update:\s*(\d{4}-\d{2}-\d{2})')
# Each category block reads "<Category> samples Explore all N metagenomic samples".
SAMPLE_COUNT_RE = re.compile(
    r'(Human|Animal|Ocean water|Other environmental) samples\s+'
    r'Explore all ([\d,]+) metagenomic samples')
# The site's labels, mapped onto the category names used everywhere else here.
SITE_CATEGORY_NAMES = {
    'Human': 'human',
    'Animal': 'animal',
    'Ocean water': 'ocean',
    'Other environmental': 'environmental',
}
# A descriptive UA; the static endpoints serve fine to scripted clients, but a
# real UA avoids any future user-agent filtering.
USER_AGENT = 'sandpiper metalog-fetch (+https://metalog.embl.de)'


def load_config(config_path):
    with open(config_path) as f:
        return yaml.safe_load(f)


def download(url, dest):
    """Stream `url` to `dest` atomically; return the final (redirected) URL.

    Any failure (Metalog unreachable, HTTP error, truncated/non-gzip body)
    aborts with a clear message and leaves no partial file. We never fall back
    to a stale local copy: a failed fetch must stop the pipeline so the join
    cannot silently run against out-of-date metadata.
    """
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    tmp = dest + '.tmp.{}'.format(os.getpid())
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            final_url = resp.geturl()
            with open(tmp, 'wb') as out:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
        # Fail loudly on a truncated/HTML response masquerading as a download.
        with gzip.open(tmp, 'rb') as gz:
            gz.read(1)
    except (urllib.error.URLError, OSError) as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise SystemExit("Metalog fetch failed for {} ({}). "
                         "Aborting — not falling back to any local copy.".format(url, e))
    os.replace(tmp, dest)
    return final_url


def fetch_release_info(site_url):
    """Metalog's published release date and per-category sample totals.

    Scraped from the home page rather than derived from the downloaded files:
    these are the numbers Metalog itself advertises, and they legitimately
    differ from row counts in the extended-wide files (which cover only the
    samples carrying extended metadata).

    Returns None -- never raises -- when the page is unreachable or its
    wording has changed. Provenance is a nice-to-have; a build must not fail
    because a marketing string moved. Callers fall back to the last value
    recorded in the front end.
    """
    try:
        request = urllib.request.Request(site_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            page = response.read().decode('utf-8', errors='replace')
    except (urllib.error.URLError, OSError) as e:
        print("  WARNING: could not read {} ({}); release info omitted".format(site_url, e),
              flush=True)
        return None

    # Strip tags first: the date and counts are split across nested inline
    # elements, so they only read as contiguous text once the markup is gone.
    text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', page)))

    date_match = RELEASE_DATE_RE.search(text)
    counts = {SITE_CATEGORY_NAMES[label]: int(number.replace(',', ''))
              for label, number in SAMPLE_COUNT_RE.findall(text)}

    if not date_match and not counts:
        print("  WARNING: {} matched neither the release date nor any sample "
              "counts; release info omitted".format(site_url), flush=True)
        return None

    release = {'source': site_url}
    if date_match:
        release['last_metadata_update'] = date_match.group(1)
    else:
        print("  WARNING: no release date found on {}".format(site_url), flush=True)
    if counts:
        release['sample_counts'] = counts
        release['sample_counts']['total'] = sum(counts.values())
        missing = sorted(set(SITE_CATEGORY_NAMES.values()) - set(counts))
        if missing:
            print("  WARNING: no sample count found for: {}".format(', '.join(missing)),
                  flush=True)
    return release


def main():
    parser = argparse.ArgumentParser(description="Fetch latest Metalog wide metadata files")
    parser.add_argument('--config', default='config.yml', help='Path to config.yml')
    args = parser.parse_args()

    cfg = load_config(args.config)
    base_url = cfg.get('METALOG_BASE_URL', DEFAULT_BASE_URL).rstrip('/')
    download_dir = cfg['METALOG_DOWNLOAD_DIR']
    os.makedirs(download_dir, exist_ok=True)

    manifest = {'fetched_at': datetime.datetime.now().isoformat(timespec='seconds'),
                'base_url': base_url, 'files': {}}
    for category in CATEGORIES:
        name = '{}_extended_wide_latest.tsv.gz'.format(category)
        url = '{}/{}'.format(base_url, name)
        dest = os.path.join(download_dir, name)
        print("Fetching {} -> {}".format(category, url), flush=True)
        resolved = download(url, dest)
        size_mb = os.path.getsize(dest) / 1e6
        print("  saved {} ({:.1f} MB) from {}".format(dest, size_mb, resolved), flush=True)
        manifest['files'][category] = {'url': url, 'resolved': resolved,
                                       'path': dest, 'size_bytes': os.path.getsize(dest)}

    site_url = cfg.get('METALOG_SITE_URL', DEFAULT_SITE_URL)
    print("Reading release info from {}".format(site_url), flush=True)
    release = fetch_release_info(site_url)
    if release:
        manifest['release'] = release
        print("  release {} ({})".format(
            release.get('last_metadata_update', 'date unknown'),
            release.get('sample_counts', {})), flush=True)

    manifest_path = os.path.join(download_dir, 'metalog_fetch_manifest.json')
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print("Wrote manifest {}".format(manifest_path), flush=True)


if __name__ == '__main__':
    main()
