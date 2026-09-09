import { describe, expect, it } from 'vitest'

import { previewCsv, toCsv } from './csv'

function csvFile(content: string): File {
  return new File([content], 'sample.csv', { type: 'text/csv' })
}

describe('previewCsv', () => {
  it('parses headers and up to maxRows data rows', async () => {
    const file = csvFile(
      'customer_name,country,purchase_date,amount\n' +
        'James Morgan,British Virgin Islands,2024-12-05,418.15\n' +
        'Jeffrey Friedman,New Caledonia,2024-03-07,352.13\n',
    )

    const preview = await previewCsv(file)

    expect(preview.headers).toEqual(['customer_name', 'country', 'purchase_date', 'amount'])
    expect(preview.rows).toHaveLength(2)
    expect(preview.rows[0]).toEqual(['James Morgan', 'British Virgin Islands', '2024-12-05', '418.15'])
  })

  it('truncates to maxRows even when the file has more data rows', async () => {
    const rows = Array.from({ length: 10 }, (_, i) => `Customer ${i},US,2024-01-01,10.00`).join('\n')
    const file = csvFile(`customer_name,country,purchase_date,amount\n${rows}\n`)

    const preview = await previewCsv(file, 5)

    expect(preview.rows).toHaveLength(5)
  })

  it('returns empty headers/rows for an empty file', async () => {
    const preview = await previewCsv(csvFile(''))
    expect(preview).toEqual({ headers: [], rows: [] })
  })
})

describe('toCsv', () => {
  it('joins headers and rows with commas and newlines', () => {
    const csv = toCsv(['name', 'amount'], [['Jane', 10], ['Bob', 20]])
    expect(csv).toBe('name,amount\nJane,10\nBob,20')
  })

  it('quotes values containing commas, quotes, or newlines', () => {
    const csv = toCsv(['name'], [['Doe, Jane'], ['Say "hi"'], ['multi\nline']])
    expect(csv).toBe('name\n"Doe, Jane"\n"Say ""hi"""\n"multi\nline"')
  })
})
