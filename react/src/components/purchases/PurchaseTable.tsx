import type { ReactNode } from 'react'

import type { Purchase } from '../../api/types'

interface PurchaseTableProps {
  purchases: Purchase[]
  isLoading: boolean
  renderRowActions?: (purchase: Purchase) => ReactNode
}

export function PurchaseTable({ purchases, isLoading, renderRowActions }: PurchaseTableProps) {
  if (isLoading) {
    return <p className="py-8 text-center text-sm text-slate-500">Loading purchases…</p>
  }

  if (purchases.length === 0) {
    return <p className="py-8 text-center text-sm text-slate-500">No purchases found.</p>
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-slate-600">ID</th>
            <th className="px-4 py-2 text-left font-medium text-slate-600">Customer</th>
            <th className="px-4 py-2 text-left font-medium text-slate-600">Country</th>
            <th className="px-4 py-2 text-left font-medium text-slate-600">Date</th>
            <th className="px-4 py-2 text-right font-medium text-slate-600">Amount</th>
            <th className="px-4 py-2 text-left font-medium text-slate-600">Currency</th>
            {renderRowActions && <th className="px-4 py-2" />}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {purchases.map((purchase) => (
            <tr key={purchase.id}>
              <td className="px-4 py-2 text-slate-500">{purchase.id}</td>
              <td className="px-4 py-2 text-slate-900">{purchase.customer_name}</td>
              <td className="px-4 py-2 text-slate-700">{purchase.country}</td>
              <td className="px-4 py-2 text-slate-700">{purchase.purchase_date}</td>
              <td className="px-4 py-2 text-right text-slate-900">
                {purchase.amount.toFixed(2)}
              </td>
              <td className="px-4 py-2 text-slate-700">{purchase.currency}</td>
              {renderRowActions && (
                <td className="px-4 py-2 text-right">{renderRowActions(purchase)}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
