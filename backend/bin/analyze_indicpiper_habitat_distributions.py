#!/usr/bin/env python3
'''One-off analysis: for each of IndicPiper's 13 habitats, summarize the
distribution of nonzero (run, habitat) scores in indicator_habitat_scores
(mean, stddev, median, 10th percentile across the runs that actually match
that habitat -- see docs/superpowers notes from the zero-result-samples
investigation for why only ~10-15% of runs match any given habitat).

Outputs a CSV of the per-habitat stats and a PNG bar chart of median vs.
10th percentile per habitat.

Optionally (--matrix-csv-out / --matrix-png-out) also outputs a metagenome
type (taxon_name) x habitat matrix: each cell is the average IndicPiper
score for that metagenome type and habitat, with zero-result runs of that
metagenome type included in the average (denominator is every run of that
taxon_name, not just the ones that matched).
'''
import argparse
import os
import statistics

import duckdb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def compute_habitat_stats(db_path):
    conn = duckdb.connect(db_path, read_only=True)
    habitats = [r[0] for r in conn.execute(
        "SELECT DISTINCT habitat FROM indicator_habitat_scores ORDER BY habitat").fetchall()]

    stats = []
    for habitat in habitats:
        scores = [r[0] for r in conn.execute(
            "SELECT score FROM indicator_habitat_scores WHERE habitat = ? ORDER BY score",
            [habitat]).fetchall()]
        n = len(scores)
        stats.append({
            'habitat': habitat,
            'n': n,
            'mean': statistics.fmean(scores),
            'stddev': statistics.stdev(scores) if n > 1 else 0.0,
            'median': statistics.median(scores),
            'p10': statistics.quantiles(scores, n=10)[0] if n >= 10 else min(scores),
        })
    conn.close()
    return stats


def write_csv(stats, csv_path):
    with open(csv_path, 'w') as f:
        f.write('habitat,n,mean,stddev,median,p10\n')
        for row in stats:
            f.write('{habitat},{n},{mean},{stddev},{median},{p10}\n'.format(
                habitat=row['habitat'].replace(',', ';'),
                n=row['n'], mean=row['mean'], stddev=row['stddev'],
                median=row['median'], p10=row['p10']))


'''DuckDB expression that canonicalizes taxon_name for grouping: lowercases,
turns underscores into spaces, then keeps only the "<...> metagenome" prefix
-- strips per-sample codes some submitters append after it (e.g.
"vaginal_metagenome UAB003_9_3" and "vibrio metagenome HEM_05" both collapse
to "vaginal metagenome" / "vibrio metagenome"). Verified against the live DB
this only merges those two groups (67 and 4 raw taxon_names respectively);
the other ~390 taxon_names are already genuine distinct NCBI categories and
pass through unchanged.'''
_CANON_TAXON_NAME_SQL = (
    r"regexp_replace(trim(regexp_extract(lower(replace(taxon_name, '_', ' ')), "
    r"'(.*?metagenome)', 1)), '\s+', ' ', 'g')"
)


def compute_metagenome_habitat_matrix(db_path):
    '''For every (canonical taxon_name, habitat) pair: avg = sum(score) /
    total runs of that metagenome type (including runs with zero/no
    IndicPiper match for that habitat) -- so metagenome types dominated by
    non-indicator genera pull their own average down, rather than being
    excluded from it.'''
    conn = duckdb.connect(db_path, read_only=True)
    habitats = [r[0] for r in conn.execute(
        "SELECT DISTINCT habitat FROM indicator_habitat_scores ORDER BY habitat").fetchall()]

    # Only taxon_names that actually say "metagenome" -- excludes single-organism
    # NCBI taxon calls (e.g. "Homo sapiens", "Banana streak virus") that aren't
    # metagenome samples at all, even though they can still show up in this table.
    taxon_totals = conn.execute("""
        SELECT {canon} AS taxon_name, count(*) FROM ncbi_metadata
        WHERE taxon_name ILIKE '%metagenome%'
        GROUP BY 1
    """.format(canon=_CANON_TAXON_NAME_SQL)).fetchall()
    taxon_total_runs = {row[0]: row[1] for row in taxon_totals}

    taxon_habitat_sums = conn.execute("""
        SELECT {canon} AS taxon_name, ihs.habitat, sum(ihs.score)
        FROM indicator_habitat_scores ihs
        JOIN ncbi_metadata nm ON nm.id = ihs.run_id
        WHERE nm.taxon_name ILIKE '%metagenome%'
        GROUP BY 1, ihs.habitat
    """.format(canon=_CANON_TAXON_NAME_SQL.replace('taxon_name', 'nm.taxon_name'))).fetchall()
    conn.close()

    sums = {}
    for taxon_name, habitat, score_sum in taxon_habitat_sums:
        sums[(taxon_name, habitat)] = score_sum

    taxon_names = sorted(taxon_total_runs.keys(), key=lambda t: taxon_total_runs[t], reverse=True)
    matrix = []
    for taxon_name in taxon_names:
        total_runs = taxon_total_runs[taxon_name]
        row = {'taxon_name': taxon_name, 'total_runs': total_runs}
        for habitat in habitats:
            row[habitat] = sums.get((taxon_name, habitat), 0.0) / total_runs
        matrix.append(row)
    return matrix, habitats


def compute_metagenome_habitat_matrix_quantile(db_path, quantile):
    '''Same shape and denominator convention as compute_metagenome_habitat_matrix
    (one row per canonical taxon_name, one column per habitat, total_runs is
    every run of that metagenome type), but each cell is `quantile` of the
    per-run score distribution instead of the mean: runs of that taxon_name
    with no match for this habitat contribute a score of 0 to that
    distribution rather than being excluded, so a Q10/Q25 cell is directly
    comparable to the mean matrix's cell-for-cell zero-inclusive average.'''
    conn = duckdb.connect(db_path, read_only=True)
    habitats = [r[0] for r in conn.execute(
        "SELECT DISTINCT habitat FROM indicator_habitat_scores ORDER BY habitat").fetchall()]

    taxon_totals = conn.execute("""
        SELECT {canon} AS taxon_name, count(*) FROM ncbi_metadata
        WHERE taxon_name ILIKE '%metagenome%'
        GROUP BY 1
    """.format(canon=_CANON_TAXON_NAME_SQL)).fetchall()
    taxon_total_runs = {row[0]: row[1] for row in taxon_totals}

    quantile_rows = conn.execute("""
        WITH runs AS (
            SELECT id AS run_id, {canon} AS taxon_name
            FROM ncbi_metadata
            WHERE taxon_name ILIKE '%metagenome%'
        )
        SELECT r.taxon_name, h.habitat,
               quantile_cont(coalesce(s.score, 0.0), ?) AS q
        FROM runs r
        CROSS JOIN (SELECT DISTINCT habitat FROM indicator_habitat_scores) h
        LEFT JOIN indicator_habitat_scores s
          ON s.run_id = r.run_id AND s.habitat = h.habitat
        GROUP BY r.taxon_name, h.habitat
    """.format(canon=_CANON_TAXON_NAME_SQL), [quantile]).fetchall()
    conn.close()

    q_values = {(taxon_name, habitat): q for taxon_name, habitat, q in quantile_rows}

    taxon_names = sorted(taxon_total_runs.keys(), key=lambda t: taxon_total_runs[t], reverse=True)
    matrix = []
    for taxon_name in taxon_names:
        row = {'taxon_name': taxon_name, 'total_runs': taxon_total_runs[taxon_name]}
        for habitat in habitats:
            row[habitat] = q_values.get((taxon_name, habitat), 0.0)
        matrix.append(row)
    return matrix, habitats


def compute_habitat_sample_counts(db_path):
    '''Per habitat, the number of metagenome-labeled runs that had a nonzero
    IndicPiper score for that habitat -- the sample size backing each column
    of the metagenome x habitat matrices (mean/Q10/Q25 alike, since it's the
    same underlying (run, habitat) score table).'''
    conn = duckdb.connect(db_path, read_only=True)
    rows = conn.execute("""
        SELECT ihs.habitat, count(*)
        FROM indicator_habitat_scores ihs
        JOIN ncbi_metadata nm ON nm.id = ihs.run_id
        WHERE nm.taxon_name ILIKE '%metagenome%'
        GROUP BY 1
    """).fetchall()
    conn.close()
    return {habitat: n for habitat, n in rows}


def write_matrix_csv(matrix, habitats, csv_path):
    with open(csv_path, 'w') as f:
        f.write('taxon_name,total_runs,' + ','.join(habitats) + '\n')
        for row in matrix:
            values = ','.join(str(row[h]) for h in habitats)
            f.write('{},{},{}\n'.format(row['taxon_name'].replace(',', ';'), row['total_runs'], values))


def write_sample_counts_csv(counts, habitats, csv_path):
    with open(csv_path, 'w') as f:
        f.write('habitat,n\n')
        for habitat in habitats:
            f.write('{},{}\n'.format(habitat.replace(',', ';'), counts[habitat]))


def write_matrix_heatmap(matrix, habitats, png_path, chunk_size=None):
    '''Renders one heatmap PNG per chunk_size rows (all rows in one image if
    chunk_size is None) -- 3,890 rows in a single image can't show legible
    per-row labels no matter the resolution, so splitting into ~500-row
    sections lets every row get an actual readable label.'''
    import numpy as np

    if chunk_size is None:
        chunks = [(0, matrix)]
    else:
        chunks = [(start, matrix[start:start + chunk_size])
                  for start in range(0, len(matrix), chunk_size)]

    base, ext = os.path.splitext(png_path)
    for start, chunk in chunks:
        data = np.array([[row[h] for h in habitats] for row in chunk])
        labels = [row['taxon_name'] for row in chunk]

        fig_height = max(6, len(labels) * 0.1)
        fig, ax = plt.subplots(figsize=(10, fig_height))
        im = ax.imshow(data, aspect='auto', cmap='viridis')
        ax.set_xticks(range(len(habitats)))
        ax.set_xticklabels(habitats, rotation=45, ha='right')
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=6)

        ax.set_xlabel('Environments')
        ax.set_ylabel('Metagenome type (taxon_name)')
        title_range = 'rows {}-{}'.format(start + 1, start + len(chunk))
        ax.set_title('Average IndicPiper score per metagenome type x habitat ({})\n'
                     '(zero-result runs included in the average; sorted by total run count)'.format(title_range))
        fig.colorbar(im, ax=ax, label='IndVal (average)')
        fig.tight_layout()

        out_path = png_path if chunk_size is None else '{}_{:02d}{}'.format(base, start // chunk_size + 1, ext)
        fig.savefig(out_path, dpi=100, bbox_inches='tight')
        plt.close(fig)


def _cluster_matrix(matrix, habitats):
    '''Shared by write_clustered_heatmap and write_clustered_heatmap_paginated:
    hierarchically clusters both axes (average linkage, Euclidean distance on
    the raw score values) and returns the reordered data/labels plus the
    linkages themselves (needed to draw dendrograms).'''
    import numpy as np
    from scipy.cluster.hierarchy import dendrogram, linkage

    data = np.array([[row[h] for h in habitats] for row in matrix])
    row_labels = [row['taxon_name'] for row in matrix]

    row_linkage = linkage(data, method='average', metric='euclidean')
    col_linkage = linkage(data.T, method='average', metric='euclidean')

    row_order = dendrogram(row_linkage, no_plot=True)['leaves']
    col_order = dendrogram(col_linkage, no_plot=True)['leaves']

    data_ordered = data[row_order][:, col_order]
    row_labels_ordered = [row_labels[i] for i in row_order]
    habitats_ordered = [habitats[i] for i in col_order]

    return data_ordered, row_labels_ordered, habitats_ordered, row_linkage, col_linkage


def write_clustered_heatmap_paginated(matrix, habitats, png_path, page_size=100):
    '''Same clustering/row order as write_clustered_heatmap, but split into
    pages of page_size rows for readability. Each page keeps the column
    dendrogram (cheap to redraw identically on every page) but drops the row
    dendrogram -- a dendrogram's branches span the whole tree, not a
    contiguous slice of leaves, so it can't be split into per-page subtrees
    without approximation. Rows are still in the correct clustered order
    across all pages; see the single full-height image for the row tree.'''
    import numpy as np
    from scipy.cluster.hierarchy import dendrogram

    data_ordered, row_labels_ordered, habitats_ordered, _, col_linkage = _cluster_matrix(matrix, habitats)

    base, ext = os.path.splitext(png_path)
    n_pages = (len(row_labels_ordered) + page_size - 1) // page_size
    for page_i in range(n_pages):
        start = page_i * page_size
        page_data = data_ordered[start:start + page_size]
        page_labels = row_labels_ordered[start:start + page_size]

        fig = plt.figure(figsize=(12, max(6, len(page_labels) * 0.18)))
        gs = fig.add_gridspec(2, 2, width_ratios=[8, 0.3], height_ratios=[1.2, 8],
                              wspace=0.15, hspace=0.15)
        ax_col_dendro = fig.add_subplot(gs[0, 0])
        ax_heatmap = fig.add_subplot(gs[1, 0])
        ax_cbar = fig.add_subplot(gs[1, 1])

        dendrogram(col_linkage, ax=ax_col_dendro, no_labels=True, color_threshold=0)
        ax_col_dendro.axis('off')

        im = ax_heatmap.imshow(page_data, aspect='auto', cmap='viridis', origin='upper')
        ax_heatmap.set_xticks(range(len(habitats_ordered)))
        ax_heatmap.set_xticklabels(habitats_ordered, rotation=45, ha='left')
        ax_heatmap.xaxis.tick_top()
        ax_heatmap.set_yticks(range(len(page_labels)))
        ax_heatmap.set_yticklabels(page_labels, fontsize=7)

        fig.colorbar(im, cax=ax_cbar, label='IndVal (average)')
        fig.suptitle('Hierarchically clustered (page {}/{}, rows {}-{})\n'
                     'Columns clustered; rows in clustered order (see full row dendrogram separately)'.format(
                         page_i + 1, n_pages, start + 1, start + len(page_labels)))

        out_path = '{}_{:02d}{}'.format(base, page_i + 1, ext)
        fig.savefig(out_path, dpi=100, bbox_inches='tight')
        plt.close(fig)


def write_clustered_heatmap(matrix, habitats, png_path):
    '''Hierarchically clusters both axes of the metagenome-type x habitat
    matrix (average linkage, Euclidean distance on the raw score values) and
    renders a clustermap. Transposed relative to the raw matrix: metagenome
    types (the many-item, long-label axis) run along the x-axis with their
    dendrogram on top and labels below (the same proven layout as the plain
    heatmap) -- putting a dendrogram and its matching labels on OPPOSITE
    sides of the heatmap guarantees they can never overlap, regardless of
    label length. Habitats (only 13, short names) run along the y-axis with
    their dendrogram and labels both on the left, which is safe at that
    scale.'''
    from scipy.cluster.hierarchy import dendrogram

    data_ordered, row_labels_ordered, habitats_ordered, row_linkage, col_linkage = \
        _cluster_matrix(matrix, habitats)
    # Transpose: x-axis = metagenome types (row_linkage/row_labels_ordered),
    # y-axis = habitats (col_linkage/habitats_ordered).
    data_t = data_ordered.T
    n_cols = len(row_labels_ordered)  # metagenome types, on x-axis now
    n_rows = len(habitats_ordered)    # habitats, on y-axis now

    fig_width = max(14, n_cols * 0.15)
    fig = plt.figure(figsize=(fig_width, 10))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.2, n_cols * 0.15, 0.3], height_ratios=[3.5, 8],
                          wspace=0.08, hspace=0.08)

    ax_col_dendro = fig.add_subplot(gs[0, 1])  # metagenome dendrogram, top
    ax_row_dendro = fig.add_subplot(gs[1, 0])  # habitat dendrogram, left
    ax_heatmap = fig.add_subplot(gs[1, 1])
    ax_cbar = fig.add_subplot(gs[1, 2])

    dendrogram(row_linkage, ax=ax_col_dendro, no_labels=True, color_threshold=0)
    ax_col_dendro.axis('off')

    # Leaf index 0 is plotted at the bottom by scipy's 'left' orientation;
    # imshow's default origin='upper' puts row index 0 at the top -- invert
    # the dendrogram's y-axis so leaf order visually lines up with the
    # heatmap rows it was used to reorder.
    dendrogram(col_linkage, ax=ax_row_dendro, orientation='left', no_labels=True, color_threshold=0)
    ax_row_dendro.invert_yaxis()
    ax_row_dendro.axis('off')

    im = ax_heatmap.imshow(data_t, aspect='auto', cmap='viridis', origin='upper')
    ax_heatmap.set_xticks(range(n_cols))
    ax_heatmap.set_xticklabels(row_labels_ordered, rotation=45, ha='right', fontsize=6)
    ax_heatmap.set_yticks(range(n_rows))
    ax_heatmap.set_yticklabels(habitats_ordered)
    ax_heatmap.yaxis.tick_left()

    fig.colorbar(im, cax=ax_cbar, label='IndVal (average)')
    fig.suptitle('Hierarchically clustered: average IndicPiper score per metagenome type x habitat\n'
                '(zero-result runs included in the average; both axes clustered, average linkage / Euclidean)')
    fig.savefig(png_path, dpi=100, bbox_inches='tight')
    plt.close(fig)


def write_chart(stats, png_path):
    stats_sorted = sorted(stats, key=lambda r: r['p10'], reverse=True)
    labels = [r['habitat'] for r in stats_sorted]
    p10s = [r['p10'] for r in stats_sorted]

    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(list(x), p10s)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_xlabel('Environments')
    ax.set_ylabel('IndVal')
    ax.set_title('IndicPiper habitat score: 10th percentile\n(across runs with a nonzero score for that habitat)')
    fig.tight_layout()
    fig.savefig(png_path, dpi=150, bbox_inches='tight')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, help='duckdb file, e.g. backend/db/sandpiper_40.duckdb')
    parser.add_argument('--csv-out', required=True, help='output CSV path for per-habitat stats')
    parser.add_argument('--png-out', required=True, help='output PNG path for the chart')
    parser.add_argument('--matrix-csv-out', help='output CSV path for the metagenome x habitat matrix')
    parser.add_argument('--matrix-png-out', help='output PNG path for the metagenome x habitat heatmap')
    parser.add_argument('--matrix-chunk-size', type=int,
                        help='split the heatmap into sections of this many rows each, e.g. 500 '
                             '(default: one single image with all rows)')
    parser.add_argument('--matrix-clustered-png-out',
                        help='output PNG path for the hierarchically clustered version of the heatmap '
                             '(both axes reordered by average-linkage/Euclidean clustering)')
    parser.add_argument('--matrix-clustered-page-size', type=int,
                        help='split the clustered heatmap into pages of this many rows each, e.g. 100 '
                             '(default: one single image with all rows and both dendrograms)')
    parser.add_argument('--matrix-q10-csv-out',
                        help='output CSV path for the metagenome x habitat matrix of 10th-percentile '
                             '(Q10) scores instead of the mean, same shape/denominator as --matrix-csv-out')
    parser.add_argument('--matrix-q25-csv-out',
                        help='output CSV path for the metagenome x habitat matrix of 25th-percentile '
                             '(Q25) scores instead of the mean, same shape/denominator as --matrix-csv-out')
    parser.add_argument('--sample-counts-csv-out',
                        help='output CSV path for the per-habitat sample count (n) backing each column '
                             'of the metagenome x habitat matrices')
    args = parser.parse_args()

    stats = compute_habitat_stats(args.db)
    write_csv(stats, args.csv_out)
    write_chart(stats, args.png_out)

    for row in stats:
        print('{habitat}: n={n} mean={mean:.4f} stddev={stddev:.4f} median={median:.4f} p10={p10:.4f}'.format(**row))

    if (args.matrix_csv_out or args.matrix_png_out or args.matrix_clustered_png_out):
        matrix, habitats = compute_metagenome_habitat_matrix(args.db)
        if args.matrix_csv_out:
            write_matrix_csv(matrix, habitats, args.matrix_csv_out)
        if args.matrix_png_out:
            write_matrix_heatmap(matrix, habitats, args.matrix_png_out, chunk_size=args.matrix_chunk_size)
        if args.matrix_clustered_png_out:
            if args.matrix_clustered_page_size:
                write_clustered_heatmap_paginated(
                    matrix, habitats, args.matrix_clustered_png_out,
                    page_size=args.matrix_clustered_page_size)
            else:
                write_clustered_heatmap(matrix, habitats, args.matrix_clustered_png_out)

    if args.matrix_q10_csv_out:
        q10_matrix, q10_habitats = compute_metagenome_habitat_matrix_quantile(args.db, 0.10)
        write_matrix_csv(q10_matrix, q10_habitats, args.matrix_q10_csv_out)

    if args.matrix_q25_csv_out:
        q25_matrix, q25_habitats = compute_metagenome_habitat_matrix_quantile(args.db, 0.25)
        write_matrix_csv(q25_matrix, q25_habitats, args.matrix_q25_csv_out)

    if args.sample_counts_csv_out:
        counts = compute_habitat_sample_counts(args.db)
        write_sample_counts_csv(counts, sorted(counts.keys()), args.sample_counts_csv_out)
