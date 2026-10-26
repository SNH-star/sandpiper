#!/usr/bin/env python3
'''Reads the metagenome-type x habitat matrix CSVs (output of
analyze_indicpiper_habitat_distributions.py --matrix-csv-out /
--matrix-q10-csv-out / --matrix-q25-csv-out), applies the same hierarchical
clustering (average linkage, Euclidean, both axes) used to render
indicpiper_metagenome_habitat_clustered.png -- computed once from the mean
matrix so all three sheets share one row/column order and stay directly
comparable -- and writes a single .xlsx with one sheet per statistic (mean,
Q10, Q25), each with a 3-color-scale conditional format over the data cells
so Excel renders the same heatmap look natively, plus a bottom row giving the
sample count (n) backing each habitat column.
'''
import argparse
import csv

import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage

from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter


def read_matrix_csv(csv_path):
    with open(csv_path) as f:
        reader = csv.reader(f)
        header = next(reader)
        habitats = header[2:]
        matrix = []
        for row in reader:
            taxon_name = row[0]
            total_runs = int(row[1])
            values = [float(v) for v in row[2:]]
            matrix.append({'taxon_name': taxon_name, 'total_runs': total_runs,
                            **dict(zip(habitats, values))})
    return matrix, habitats


def read_sample_counts_csv(csv_path):
    with open(csv_path) as f:
        reader = csv.reader(f)
        next(reader)  # header: habitat,n
        return {habitat: int(n) for habitat, n in reader}


def cluster_matrix(matrix, habitats):
    '''Clusters `matrix` (list of {'taxon_name': ..., habitat: value, ...}
    dicts) and returns the row/column order as label lists, so the same
    order can be replayed against other matrices sharing the same taxa and
    habitats (see reorder_matrix_like).'''
    data = np.array([[row[h] for h in habitats] for row in matrix])
    row_labels = [row['taxon_name'] for row in matrix]

    row_linkage = linkage(data, method='average', metric='euclidean')
    col_linkage = linkage(data.T, method='average', metric='euclidean')

    row_order = dendrogram(row_linkage, no_plot=True)['leaves']
    col_order = dendrogram(col_linkage, no_plot=True)['leaves']

    data_ordered = data[row_order][:, col_order]
    row_labels_ordered = [row_labels[i] for i in row_order]
    habitats_ordered = [habitats[i] for i in col_order]
    return data_ordered, row_labels_ordered, habitats_ordered


def reorder_matrix_like(matrix, habitats, row_labels_ordered, habitats_ordered):
    '''Reorders a Q10/Q25 matrix into the row/column order already computed
    from the mean matrix, by taxon_name/habitat lookup rather than
    re-clustering -- keeps all three sheets in the exact same layout so a
    given row/column means the same taxon/habitat everywhere.'''
    by_taxon = {row['taxon_name']: row for row in matrix}
    missing_taxa = [t for t in row_labels_ordered if t not in by_taxon]
    if missing_taxa:
        raise ValueError('taxa present in the mean matrix but missing here: {}'.format(missing_taxa[:5]))
    missing_habitats = [h for h in habitats_ordered if h not in habitats]
    if missing_habitats:
        raise ValueError('habitats present in the mean matrix but missing here: {}'.format(missing_habitats))

    data_ordered = np.array([[by_taxon[t][h] for h in habitats_ordered] for t in row_labels_ordered])
    return data_ordered


def write_sheet(ws, data_ordered, row_labels_ordered, habitats_ordered, sample_counts, row_total_runs):
    # taxon_name (NCBI metagenome type) down the rows, habitat (IndicPiper)
    # across the columns -- natural spreadsheet orientation, both axes still
    # in hclust order.
    n_habitats = len(habitats_ordered)
    n_taxa = len(row_labels_ordered)
    n_samples_col = 2 + n_habitats

    header_font = Font(bold=True)
    ws.cell(row=1, column=1, value='taxon_name').font = header_font
    for j, habitat in enumerate(habitats_ordered):
        c = ws.cell(row=1, column=2 + j, value=habitat)
        c.font = header_font
        c.alignment = Alignment(text_rotation=45)
    ws.cell(row=1, column=n_samples_col, value='n samples').font = header_font

    for i, taxon_name in enumerate(row_labels_ordered):
        ws.cell(row=2 + i, column=1, value=taxon_name).font = header_font
        for j in range(n_habitats):
            ws.cell(row=2 + i, column=2 + j, value=float(data_ordered[i, j]))
        ws.cell(row=2 + i, column=n_samples_col, value=row_total_runs[taxon_name]).font = header_font

    first_data_col = get_column_letter(2)
    last_data_col = get_column_letter(1 + n_habitats)
    data_range = '{}2:{}{}'.format(first_data_col, last_data_col, 1 + n_taxa)

    rule = ColorScaleRule(
        start_type='min', start_color='2C3E7A',
        mid_type='percentile', mid_value=50, mid_color='F5E56B',
        end_type='max', end_color='D62839')
    ws.conditional_formatting.add(data_range, rule)

    # Footer row: sample count (n) backing each habitat column. Left outside
    # the conditional-formatting range above so it isn't colored as if it
    # were a score. The n-samples column above it is skipped -- it's a
    # per-row count, not a per-habitat one, so there's nothing to put there.
    footer_row = 2 + n_taxa
    ws.cell(row=footer_row, column=1, value='n samples').font = header_font
    for j, habitat in enumerate(habitats_ordered):
        c = ws.cell(row=footer_row, column=2 + j, value=sample_counts[habitat])
        c.font = header_font

    ws.freeze_panes = 'B2'
    ws.column_dimensions['A'].width = 30
    for j in range(n_habitats):
        ws.column_dimensions[get_column_letter(2 + j)].width = 10
    ws.column_dimensions[get_column_letter(n_samples_col)].width = 12
    ws.row_dimensions[1].height = 60


def write_xlsx(sheets, xlsx_path, row_total_runs):
    '''sheets: list of (title, data_ordered, row_labels_ordered, habitats_ordered, sample_counts).'''
    wb = Workbook()
    for i, (title, data_ordered, row_labels_ordered, habitats_ordered, sample_counts) in enumerate(sheets):
        ws = wb.active if i == 0 else wb.create_sheet()
        ws.title = title
        write_sheet(ws, data_ordered, row_labels_ordered, habitats_ordered, sample_counts, row_total_runs)
    wb.save(xlsx_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix-csv', required=True, help='mean matrix CSV (drives the row/column clustering)')
    parser.add_argument('--matrix-q10-csv', help='Q10 matrix CSV, same taxa/habitats as --matrix-csv')
    parser.add_argument('--matrix-q25-csv', help='Q25 matrix CSV, same taxa/habitats as --matrix-csv')
    parser.add_argument('--sample-counts-csv', required=True, help='per-habitat sample count CSV (habitat,n)')
    parser.add_argument('--xlsx-out', required=True)
    args = parser.parse_args()

    sample_counts = read_sample_counts_csv(args.sample_counts_csv)

    matrix, habitats = read_matrix_csv(args.matrix_csv)
    row_total_runs = {row['taxon_name']: row['total_runs'] for row in matrix}
    data_ordered, row_labels_ordered, habitats_ordered = cluster_matrix(matrix, habitats)
    sheets = [('mean', data_ordered, row_labels_ordered, habitats_ordered, sample_counts)]

    if args.matrix_q10_csv:
        q10_matrix, q10_habitats = read_matrix_csv(args.matrix_q10_csv)
        q10_data_ordered = reorder_matrix_like(q10_matrix, q10_habitats, row_labels_ordered, habitats_ordered)
        sheets.append(('Q10', q10_data_ordered, row_labels_ordered, habitats_ordered, sample_counts))

    if args.matrix_q25_csv:
        q25_matrix, q25_habitats = read_matrix_csv(args.matrix_q25_csv)
        q25_data_ordered = reorder_matrix_like(q25_matrix, q25_habitats, row_labels_ordered, habitats_ordered)
        sheets.append(('Q25', q25_data_ordered, row_labels_ordered, habitats_ordered, sample_counts))

    write_xlsx(sheets, args.xlsx_out, row_total_runs)
    print('wrote', args.xlsx_out, '-', len(sheets), 'sheet(s),',
          len(habitats_ordered), 'habitats x', len(row_labels_ordered), 'taxa')
