import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MockAdapter from 'axios-mock-adapter'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import type { PurchasePage as PurchasePageResponse } from '../api/types'
import { AuthProvider } from '../auth/AuthProvider'
import { PurchasesPage } from './PurchasesPage'

function page(overrides: Partial<PurchasePageResponse> = {}): PurchasePageResponse {
  return {
    items: [
      {
        id: 1,
        customer_name: 'Katie Brown',
        country: 'Tunisia',
        purchase_date: '2025-02-14',
        amount: 726.97,
        currency: 'USD',
      },
    ],
    total: 1600,
    limit: 100,
    offset: 0,
    ...overrides,
  }
}

function renderPurchasesPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <PurchasesPage />
      </AuthProvider>
    </QueryClientProvider>,
  )
}

describe('PurchasesPage', () => {
  let mock: MockAdapter

  beforeEach(() => {
    mock = new MockAdapter(apiClient)
  })

  it('renders purchases returned by the API', async () => {
    mock.onGet('/purchases/').reply(200, page())

    renderPurchasesPage()

    await waitFor(() => expect(screen.getByText('Katie Brown')).toBeInTheDocument())
    expect(screen.getByText('Tunisia')).toBeInTheDocument()
    expect(screen.getByText('726.97')).toBeInTheDocument()
    expect(screen.getByText('1–100 of 1600')).toBeInTheDocument()
  })

  it('requests the next page on clicking Next, using the offset/limit contract', async () => {
    mock.onGet('/purchases/').reply((config) => {
      const offset = Number(config.params.offset)
      return [200, page({ offset, items: [] })]
    })

    const user = userEvent.setup()
    renderPurchasesPage()

    await waitFor(() => expect(screen.getByText('1–100 of 1600')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Next' }))

    await waitFor(() => expect(screen.getByText('101–200 of 1600')).toBeInTheDocument())
  })

  it('shows a friendly message when the API is unreachable', async () => {
    mock.onGet('/purchases/').networkError()

    renderPurchasesPage()

    await waitFor(() =>
      expect(screen.getByText(/cannot reach the api/i)).toBeInTheDocument(),
    )
  })

  it('resets to the first page when filters change after paginating', async () => {
    mock.onGet('/purchases/').reply((config) => {
      const offset = Number(config.params.offset)
      return [200, page({ offset, items: [] })]
    })

    const user = userEvent.setup()
    renderPurchasesPage()

    await waitFor(() => expect(screen.getByText('1–100 of 1600')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(screen.getByText('101–200 of 1600')).toBeInTheDocument())

    await user.type(screen.getByLabelText('Country'), 'Tunisia')

    await waitFor(() => expect(screen.getByText('1–100 of 1600')).toBeInTheDocument())
  })

  it('disables Export CSV until purchases have loaded', async () => {
    mock.onGet('/purchases/').reply(200, page())

    renderPurchasesPage()

    expect(screen.getByRole('button', { name: /export csv/i })).toBeDisabled()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /export csv/i })).toBeEnabled(),
    )
  })

  it('triggers a CSV download of the current page when Export CSV is clicked', async () => {
    mock.onGet('/purchases/').reply(200, page())

    const user = userEvent.setup()
    renderPurchasesPage()
    await waitFor(() => expect(screen.getByRole('button', { name: /export csv/i })).toBeEnabled())

    const createObjectURL = vi.fn((_blob: Blob) => 'blob:mock-url')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL })

    await user.click(screen.getByRole('button', { name: /export csv/i }))

    expect(createObjectURL).toHaveBeenCalledOnce()
    const blob = createObjectURL.mock.calls[0][0] as Blob
    const text = await blob.text()
    expect(text).toContain('id,customer_name,country,purchase_date,amount,currency')
    expect(text).toContain('Katie Brown')
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock-url')

    vi.unstubAllGlobals()
  })
})
