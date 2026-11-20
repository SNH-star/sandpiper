// Saving a figure's table as a CSV file. A table is { columns: [text], rows: [[value]] }; a blank (null or
// undefined) is an empty cell.

// Excel reads a file as UTF-8 only when it starts with this mark.
const BYTE_ORDER_MARK = '﻿'
const LINE_END = '\r\n'
const OBJECT_URL_LIFETIME_MS = 60000

function cell (value) {
  if (value === null || value === undefined) return ''
  const text = String(value)
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function csvText ({ columns, rows }) {
  const lines = [columns, ...rows].map(line => line.map(cell).join(','))
  return BYTE_ORDER_MARK + lines.join(LINE_END) + LINE_END
}

export function downloadCsv (table, name) {
  const url = URL.createObjectURL(new Blob([csvText(table)], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `${name}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), OBJECT_URL_LIFETIME_MS)
}
