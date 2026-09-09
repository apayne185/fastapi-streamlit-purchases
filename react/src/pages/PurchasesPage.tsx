import { useState } from 'react'

import { parseApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { DeletePurchaseButton } from '../components/purchases/DeletePurchaseButton'
import { PurchaseFilters, type PurchaseFilterValues } from '../components/purchases/PurchaseFilters'
import { PurchasePagination } from '../components/purchases/PurchasePagination'
import { PurchaseTable } from '../components/purchases/PurchaseTable'
import { Button } from '../components/ui/Button'
import { usePurchases } from '../hooks/usePurchases'
import { toCsv } from '../lib/csv'

const EMPTY_FILTERS: PurchaseFilterValues = { country: '', startDate: '', endDate: '' }
const CSV_HEADERS = ['id', 'customer_name', 'country', 'purchase_date', 'amount', 'currency']

export function PurchasesPage() {
  const { isAdmin } = useAuth()
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

  const handleExport = () => {
    const items = data?.items ?? []
    const rows = items.map((item) => [
      item.id ?? '',
      item.customer_name,
      item.country,
      item.purchase_date,
      item.amount,
      item.currency,
    ])
    const blob = new Blob([toCsv(CSV_HEADERS, rows)], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'purchases.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Purchases</h1>
        <Button variant="secondary" onClick={handleExport} disabled={!data?.items.length}>
          Export CSV
        </Button>
      </div>

      <div className="mt-4">
        <PurchaseFilters values={filters} onChange={handleFiltersChange} />
      </div>

      {isError && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {parseApiError(error)}
        </p>
      )}

      <div className="mt-4">
        <PurchaseTable
          purchases={data?.items ?? []}
          isLoading={isLoading}
          renderRowActions={
            isAdmin
              ? (purchase) =>
                  purchase.id !== undefined && <DeletePurchaseButton purchaseId={purchase.id} />
              : undefined
          }
        />
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
