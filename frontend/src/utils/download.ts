// Client-side file download helpers: trigger a browser download from an
// in-memory Blob, and build CSV text from tabular data.

/** Trigger a browser download for an in-memory Blob. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  // Revoke on the next tick so the click has been dispatched first.
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

type CsvCell = string | number | null | undefined

/** Escape one CSV field per RFC 4180 (quote when it contains , " or newline). */
function csvField(value: CsvCell): string {
  const s = value == null ? '' : String(value)
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

/** Build CSV text from a header row plus data rows. */
export function toCsv(header: string[], rows: CsvCell[][]): string {
  return [header, ...rows].map((r) => r.map(csvField).join(',')).join('\r\n')
}

/** Build a CSV file and download it. Prepends a UTF-8 BOM so Excel reads
 * non-ASCII correctly. */
export function downloadCsv(filename: string, header: string[], rows: CsvCell[][]): void {
  const blob = new Blob(['﻿' + toCsv(header, rows)], { type: 'text/csv;charset=utf-8' })
  downloadBlob(blob, filename)
}
