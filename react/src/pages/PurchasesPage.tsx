import { useState } from 'react'

import { parseApiError } from '../api/client'
import { PurchaseFilters, type PurchaseFilterValues } from '../components/purchases/PurchaseFilters'
import { PurchasePagination } from '../components/purchases/PurchasePagination'
import { PurchaseTable } from '../components/purchases/PurchaseTable'
import { usePurchases } from '../hooks/usePurchases'

const EMPTY_FILTERS: PurchaseFilterValues = { country: '', startDate: '', endDate: '' }

export function PurchasesPage() {
  const [filters, setFilters] = useState<PurchaseFilterValues>(EMPTY_FILTERS)
  const [offset, setOffset] = useState(0)
  const [limit, setLimit] = useState(100)

  const { data, isLoading, isError, error } = usePurchases({
    limit,
    offset,
    country: filters.country || undefined,
    start_date: filters.startDate || undefined,
    end_date: filters.endDate || undefined,
  })

  const handleFiltersChange = (next: PurchaseFilterValues) => {
    setFilters(next)
    setOffset(0)
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900">Purchases</h1>

      <div className="mt-4">
        <PurchaseFilters values={filters} onChange={handleFiltersChange} />
      </div>

      {isError && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {parseApiError(error)}
        </p>
      )}

      <div className="mt-4">
        <PurchaseTable purchases={data?.items ?? []} isLoading={isLoading} />
      </div>

      {data && (
        <PurchasePagination
          offset={offset}
          limit={limit}
          total={data.total}
          onOffsetChange={setOffset}
          onLimitChange={(newLimit) => {
            setLimit(newLimit)
            setOffset(0)
          }}
        />
      )}
    </div>
  )
}
