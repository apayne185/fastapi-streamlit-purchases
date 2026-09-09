import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient, parseApiError, setUnauthorizedHandler } from './client'
import { clearTokens, loadTokens, saveTokens } from './tokenStorage'

describe('apiClient auth interceptor', () => {
  let mock: MockAdapter
  let globalMock: MockAdapter

  beforeEach(() => {
    mock = new MockAdapter(apiClient)
    globalMock = new MockAdapter(axios)
    clearTokens()
    setUnauthorizedHandler(null)
  })

  it('attaches the stored access token as a Bearer header', async () => {
    saveTokens({ accessToken: 'access-1', refreshToken: 'refresh-1' })
    mock.onGet('/purchases/').reply((config) => {
      expect(config.headers?.Authorization).toBe('Bearer access-1')
      return [200, { items: [], total: 0, limit: 500, offset: 0 }]
    })

    await apiClient.get('/purchases/')
  })

  it('silently refreshes on 401, retries once, and rotates both tokens', async () => {
    saveTokens({ accessToken: 'stale-access', refreshToken: 'refresh-1' })

    let purchaseCallCount = 0
    mock.onGet('/purchase/1').reply((config) => {
      purchaseCallCount += 1
      if (config.headers?.Authorization === 'Bearer stale-access') {
        return [401, { detail: 'Invalid or expired token' }]
      }
      expect(config.headers?.Authorization).toBe('Bearer fresh-access')
      return [200, { id: 1 }]
    })

    globalMock.onPost('http://localhost:8000/token/refresh').reply((config) => {
      expect(JSON.parse(config.data)).toEqual({ refresh_token: 'refresh-1' })
      return [
        200,
        {
          access_token: 'fresh-access',
          refresh_token: 'fresh-refresh',
          token_type: 'bearer',
        },
      ]
    })

    const response = await apiClient.get('/purchase/1')

    expect(response.status).toBe(200)
    expect(purchaseCallCount).toBe(2)
    expect(loadTokens()).toEqual({
      accessToken: 'fresh-access',
      refreshToken: 'fresh-refresh',
    })
  })

  it('shares one in-flight refresh across concurrent 401s', async () => {
    saveTokens({ accessToken: 'stale-access', refreshToken: 'refresh-1' })

    let refreshCallCount = 0
    globalMock.onPost('http://localhost:8000/token/refresh').reply(() => {
      refreshCallCount += 1
      return [
        200,
        { access_token: 'fresh-access', refresh_token: 'fresh-refresh', token_type: 'bearer' },
      ]
    })

    mock.onGet('/purchase/1').reply((config) =>
      config.headers?.Authorization === 'Bearer stale-access'
        ? [401, { detail: 'Invalid or expired token' }]
        : [200, { id: 1 }],
    )
    mock.onGet('/purchase/2').reply((config) =>
      config.headers?.Authorization === 'Bearer stale-access'
        ? [401, { detail: 'Invalid or expired token' }]
        : [200, { id: 2 }],
    )

    await Promise.all([apiClient.get('/purchase/1'), apiClient.get('/purchase/2')])

    expect(refreshCallCount).toBe(1)
  })

  it('clears tokens and calls the unauthorized handler when refresh itself fails', async () => {
    saveTokens({ accessToken: 'stale-access', refreshToken: 'dead-refresh' })
    const handler = vi.fn()
    setUnauthorizedHandler(handler)

    mock.onGet('/purchase/1').reply(401, { detail: 'Invalid or expired token' })
    globalMock
      .onPost('http://localhost:8000/token/refresh')
      .reply(401, { detail: 'Invalid or expired refresh token' })

    await expect(apiClient.get('/purchase/1')).rejects.toBeTruthy()

    expect(loadTokens()).toBeNull()
    expect(handler).toHaveBeenCalledOnce()
  })

  it('does not attempt refresh when the login request itself 401s', async () => {
    globalMock.onPost('http://localhost:8000/token').reply(401, {
      detail: 'Incorrect username or password',
    })
    let refreshAttempted = false
    globalMock.onPost('http://localhost:8000/token/refresh').reply(() => {
      refreshAttempted = true
      return [200, {}]
    })

    await expect(
      axios.post('http://localhost:8000/token', { username: 'a', password: 'b' }),
    ).rejects.toBeTruthy()

    expect(refreshAttempted).toBe(false)
  })
})

describe('parseApiError', () => {
  it('extracts the detail string from a standard error body', () => {
    const error = {
      isAxiosError: true,
      response: { status: 400, data: { detail: 'Unsupported currency' } },
    }
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(true)
    expect(parseApiError(error)).toBe('Unsupported currency')
  })

  it('formats FastAPI 422 validation array errors', () => {
    const error = {
      isAxiosError: true,
      response: {
        status: 422,
        data: { detail: [{ loc: ['query', 'amount'], msg: 'must be positive', type: 'value_error' }] },
      },
    }
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(true)
    expect(parseApiError(error)).toBe('amount: must be positive')
  })

  it('gives a generic message for 429 rate-limit bodies (non-detail shape)', () => {
    const error = {
      isAxiosError: true,
      response: { status: 429, data: { error: 'Rate limit exceeded: 100 per 1 minute' } },
    }
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(true)
    expect(parseApiError(error)).toMatch(/too many requests/i)
  })

  it('reports unreachable API when there is no response at all', () => {
    const error = { isAxiosError: true, response: undefined }
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(true)
    expect(parseApiError(error)).toMatch(/cannot reach the api/i)
  })
})
