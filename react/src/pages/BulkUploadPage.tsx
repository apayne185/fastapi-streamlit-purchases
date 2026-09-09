import { BulkUploadForm } from '../components/purchases/BulkUploadForm'

export function BulkUploadPage() {
  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900">Bulk Upload</h1>
      <div className="mt-4">
        <BulkUploadForm />
      </div>
    </div>
  )
}
