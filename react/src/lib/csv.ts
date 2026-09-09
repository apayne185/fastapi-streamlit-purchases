export interface CsvPreview {
  headers: string[]
  rows: string[][]
}

// Preview-only: splits on commas without quote/escape handling, matching the
// simple format sample_purchases.csv and the backend's csv.DictReader usage
// actually use. Full parsing/validation happens server-side on upload.
export async function previewCsv(file: File, maxRows = 5): Promise<CsvPreview> {
  const text = await file.text()
  const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0)
  if (lines.length === 0) {
    return { headers: [], rows: [] }
  }
  const [headerLine, ...dataLines] = lines
  const headers = headerLine.split(',').map((h) => h.trim())
  const rows = dataLines.slice(0, maxRows).map((line) => line.split(',').map((cell) => cell.trim()))
  return { headers, rows }
}

export function toCsv(headers: string[], rows: (string | number)[][]): string {
  const escape = (value: string | number) => {
    const str = String(value)
    return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str
  }
  return [headers, ...rows].map((row) => row.map(escape).join(',')).join('\n')
}
