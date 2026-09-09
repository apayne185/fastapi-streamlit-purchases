import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { listPurchases } from '../api/purchases'
import type { PurchaseListParams } from '../api/types'

export const purchasesQueryKey = (params: PurchaseListParams) => ['purchases', params] as const

export function usePurchases(params: PurchaseListParams) {
  return useQuery({
    queryKey: purchasesQueryKey(params),
    queryFn: () => listPurchases(params),
    placeholderData: keepPreviousData,
  })
}
