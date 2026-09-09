import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import MockAdapter from 'axios-mock-adapter'
import { beforeEach, describe, expect, it } from 'vitest'

import { apiClient } from '../api/client'
import type { PurchasePage } from '../api/types'
import { DashboardPage } from './DashboardPage'

function page(items: PurchasePage['items']): PurchasePage {
  return { items, total: items.length, limit: 500, offset: 0 }
}

function renderDashboard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardPage />
    </QueryClientProvider>,
  )
}

function tileValue(label: string): string | null {
  const labelEl = screen.getByText(label)
  return labelEl.parentElement?.querySelector('p:last-child')?.textContent ?? null
}

describe('DashboardPage', () => {
  let mock: MockAdapter

  beforeEach(() => {
    mock = new MockAdapter(apiClient)
  })

  it('computes KPI tiles from the current page of purchases', async () => {
    mock.onGet('/purchases/').reply(
      200,
      page([
        {
          id: 1,
          customer_name: 'Alice',
          country: 'France',
          purchase_date: '2026-01-01',
          amount: 100,
          currency: 'USD',
        },
        {
          id: 2,
          customer_name: 'Bob',
          country: 'France',
          purchase_date: '2026-01-02',
          amount: 50,
          currency: 'USD',
        },
      ]),
    )

    renderDashboard()

    await waitFor(() => expect(tileValue('Total Revenue')).toBe('USD 150.00'))
    expect(tileValue('Total Purchases')).toBe('2')
    expect(tileValue('Avg Order Value')).toBe('USD 75.00')
    expect(tileValue('Unique Customers')).toBe('2')
  })

  it('converts amounts to the selected display currency before aggregating', async () => {
    mock.onGet('/purchases/').reply(
      200,
      page([
        {
          id: 1,
          customer_name: 'Alice',
          country: 'France',
          purchase_date: '2026-01-01',
          amount: 100,
          currency: 'EUR',
        },
      ]),
    )

    renderDashboard()

    // 100 EUR -> 108 USD (RATES_TO_USD.EUR = 1.08), displayed in USD by default
    await waitFor(() => expect(tileValue('Total Revenue')).toBe('USD 108.00'))
  })

  it('shows a message when there are no purchases', async () => {
    mock.onGet('/purchases/').reply(200, page([]))

    renderDashboard()

    await waitFor(() => expect(screen.getByText('No purchases found.')).toBeInTheDocument())
  })

  it('shows a friendly error when the API is unreachable', async () => {
    mock.onGet('/purchases/').networkError()

    renderDashboard()

    await waitFor(() =>
      expect(screen.getByText(/cannot reach the api/i)).toBeInTheDocument(),
    )
  })
})
