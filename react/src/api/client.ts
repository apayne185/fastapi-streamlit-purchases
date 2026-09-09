import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

import { API_URL } from '../config'
import { clearTokens, loadTokens, saveTokens } from './tokenStorage'
import type { ErrorDetail, Token, ValidationErrorDetail } from './types'

const AUTH_ENDPOINTS = ['/token', '/token/refresh', '/register']

declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    _retried?: boolean
  }
}

export const apiClient = axios.create({ baseURL: API_URL })

let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler
}

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const tokens = loadTokens()
  if (tokens?.accessToken) {
    config.headers.set('Authorization', `Bearer ${tokens.accessToken}`)
  }
  return config
})

let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const tokens = loadTokens()
  if (!tokens?.refreshToken) {
    throw new Error('No refresh token available')
  }
  const { data } = await axios.post<Token>(`${API_URL}/token/refresh`, {
    refresh_token: tokens.refreshToken,
  })
  saveTokens({ accessToken: data.access_token, refreshToken: data.refresh_token })
  return data.access_token
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const { config, response } = error
    if (!config || response?.status !== 401) {
      throw error
    }

    const isAuthEndpoint = AUTH_ENDPOINTS.some((path) => config.url?.includes(path))
    if (isAuthEndpoint || config._retried) {
      throw error
    }

    try {
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null
      })
      const newAccessToken = await refreshPromise

      config._retried = true
      config.headers.set('Authorization', `Bearer ${newAccessToken}`)
      return apiClient.request(config)
    } catch {
      clearTokens()
      onUnauthorized?.()
      throw error
    }
  },
)

export function parseApiError(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return 'Something went wrong. Please try again.'
  }

  if (error.response?.status === 429) {
    return 'Too many requests — please slow down and try again shortly.'
  }

  const data = error.response?.data as
    | ErrorDetail
    | ValidationErrorDetail
    | undefined

  if (Array.isArray(data?.detail)) {
    const [first] = data.detail
    return first ? `${first.loc.at(-1)}: ${first.msg}` : 'Invalid request.'
  }

  if (typeof data?.detail === 'string') {
    return data.detail
  }

  if (!error.response) {
    return 'Cannot reach the API. Is the backend running?'
  }

  return 'Something went wrong. Please try again.'
}
