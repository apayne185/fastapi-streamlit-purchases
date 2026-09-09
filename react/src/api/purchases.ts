import { apiClient } from './client'
import type {
  BulkUploadResult,
  DeletePurchaseResult,
  KpiResponse,
  Purchase,
  PurchaseListParams,
  PurchasePage,
} from './types'

export async function listPurchases(params: PurchaseListParams): Promise<PurchasePage> {
  const { data } = await apiClient.get<PurchasePage>('/purchases/', { params })
  return data
}

export async function getPurchase(id: number): Promise<Purchase> {
  const { data } = await apiClient.get<Purchase>(`/purchase/${id}`)
  return data
}

export async function createPurchase(purchase: Purchase): Promise<Purchase> {
  const { data } = await apiClient.post<Purchase>('/purchase/', purchase)
  return data
}

export async function bulkUploadPurchases(file: File): Promise<BulkUploadResult> {
  const form = new FormData()
  form.append('file', file)
  // No explicit Content-Type: axios/the browser set multipart/form-data with
  // the correct boundary automatically for a FormData body.
  const { data } = await apiClient.post<BulkUploadResult>('/purchase/bulk/', form)
  return data
}

export async function deletePurchase(id: number): Promise<DeletePurchaseResult> {
  const { data } = await apiClient.delete<DeletePurchaseResult>(`/purchase/${id}`)
  return data
}

export async function fetchKpis(forecastDays?: number): Promise<KpiResponse> {
  const { data } = await apiClient.get<KpiResponse>('/purchases/kpis', {
    params: forecastDays ? { forecast_days: forecastDays } : undefined,
  })
  return data
}
