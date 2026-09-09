export interface Token {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
}

export interface User {
  username: string
  role: 'admin' | 'user'
}

export interface RegisterRequest {
  username: string
  password: string
}

export interface RefreshRequest {
  refresh_token: string
}

export const SUPPORTED_CURRENCIES = [
  'USD',
  'EUR',
  'GBP',
  'JPY',
  'CAD',
  'AUD',
  'CHF',
  'SEK',
  'NOK',
  'DKK',
] as const

export type Currency = (typeof SUPPORTED_CURRENCIES)[number]

export interface Purchase {
  id?: number
  customer_name: string
  country: string
  purchase_date: string
  amount: number
  currency: string
  created_at?: string
  updated_at?: string
}

export interface PurchasePage {
  items: Purchase[]
  total: number
  limit: number
  offset: number
}

export interface PurchaseListParams {
  country?: string
  start_date?: string
  end_date?: string
  limit?: number
  offset?: number
}

export interface BulkUploadResult {
  added: number
}

// No response_model declared on the backend for this endpoint — shape taken
// directly from the return statement in fastapi/main.py, not from OpenAPI.
export interface DeletePurchaseResult {
  message: string
}

// No response_model declared on the backend for this endpoint either.
export interface KpiResponse {
  mean_purchases_per_client: Record<string, number>
  clients_per_country: Record<string, number>
  sales_forecast: Record<string, number> | null
}

// Every HTTPException body, except 422 (FastAPI's array shape) and 429
// (slowapi's own shape) — see parseApiError in api/client.ts.
export interface ErrorDetail {
  detail: string
}

export interface ValidationErrorItem {
  loc: (string | number)[]
  msg: string
  type: string
}

export interface ValidationErrorDetail {
  detail: ValidationErrorItem[]
}
