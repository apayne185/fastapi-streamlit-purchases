import { useState, type ChangeEvent } from 'react'

import { parseApiError } from '../../api/client'
import { useBulkUpload } from '../../hooks/useBulkUpload'
import { previewCsv, type CsvPreview } from '../../lib/csv'
import { Button } from '../ui/Button'
import { CsvPreviewTable } from './CsvPreviewTable'

export function BulkUploadForm() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<CsvPreview | null>(null)
  const bulkUpload = useBulkUpload()

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] ?? null
    setFile(selected)
    bulkUpload.reset()
    setPreview(selected ? await previewCsv(selected) : null)
  }

  const handleUpload = async () => {
    if (!file) return
    try {
      await bulkUpload.mutateAsync(file)
      setFile(null)
      setPreview(null)
    } catch {
      // surfaced via bulkUpload.isError/error below
    }
  }

  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <input
        type="file"
        accept=".csv,text/csv"
        aria-label="CSV file"
        onChange={(event) => void handleFileChange(event)}
        className="text-sm text-slate-700"
      />

      {preview && preview.rows.length > 0 && (
        <div>
          <p className="mb-2 text-sm text-slate-600">Preview (first {preview.rows.length} rows):</p>
          <CsvPreviewTable preview={preview} />
        </div>
      )}

      {bulkUpload.isError && (
        <p className="text-sm text-red-600">{parseApiError(bulkUpload.error)}</p>
      )}
      {bulkUpload.isSuccess && (
        <p className="text-sm text-emerald-600">Added {bulkUpload.data.added} purchases.</p>
      )}

      <Button
        disabled={!file || bulkUpload.isPending}
        onClick={() => void handleUpload()}
        className="self-start"
      >
        {bulkUpload.isPending ? 'Uploading…' : 'Upload'}
      </Button>
    </div>
  )
}
