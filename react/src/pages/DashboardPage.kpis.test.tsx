import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

describe('DashboardPage KPI/forecast section', () => {
  let mock: MockAdapter

  beforeEach(() => {
    mock = new MockAdapter(apiClient)
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
      ]),
    )
  })

  it('does not fetch KPIs until Compute KPIs is clicked', async () => {
    let kpiCallCount = 0
    mock.onGet('/purchases/kpis').reply(() => {
      kpiCallCount += 1
      return [200, { mean_purchases_per_client: {}, clients_per_country: {}, sales_forecast: null }]
    })

    renderDashboard()
    await waitFor(() => expect(screen.getByRole('button', { name: /compute kpis/i })).toBeEnabled())

    expect(kpiCallCount).toBe(0)
  })

  it('fetches and renders KPIs with the entered forecast horizon', async () => {
    mock.onGet('/purchases/kpis').reply((config) => {
      expect(config.params.forecast_days).toBe(5)
      return [
        200,
        {
          mean_purchases_per_client: { Alice: 100 },
          clients_per_country: { France: 1 },
          sales_forecast: { 'Day 1': 42.5 },
        },
      ]
    })

    const user = userEvent.setup()
    renderDashboard()

    await user.click(screen.getByRole('button', { name: /compute kpis/i }))

    await waitFor(() => expect(screen.getByText('Avg Purchase per Client')).toBeInTheDocument())
    expect(screen.getByText('Sales Forecast — Next 5 Days')).toBeInTheDocument()
  })

  it('surfaces the documented 400 when there is not enough data for a forecast', async () => {
    mock.onGet('/purchases/kpis').reply(400, { detail: 'Not enough data for forecast' })

    const user = userEvent.setup()
    renderDashboard()

    await user.click(screen.getByRole('button', { name: /compute kpis/i }))

    await waitFor(() =>
      expect(screen.getByText('Not enough data for forecast')).toBeInTheDocument(),
    )
  })

  it('surfaces the documented 404 when there is no purchase data at all', async () => {
    mock.onGet('/purchases/kpis').reply(404, { detail: 'No purchase data' })

    const user = userEvent.setup()
    renderDashboard()

    await user.click(screen.getByRole('button', { name: /compute kpis/i }))

    await waitFor(() => expect(screen.getByText('No purchase data')).toBeInTheDocument())
  })
})
