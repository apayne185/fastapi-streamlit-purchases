import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MockAdapter from 'axios-mock-adapter'
import { beforeEach, describe, expect, it } from 'vitest'

import { apiClient } from '../api/client'
import { clearTokens, saveTokens } from '../api/tokenStorage'
import type { PurchasePage } from '../api/types'
import { AuthProvider } from '../auth/AuthProvider'
import { PurchasesPage } from './PurchasesPage'

function page(): PurchasePage {
  return {
    items: [
      {
        id: 42,
        customer_name: 'Katie Brown',
        country: 'Tunisia',
        purchase_date: '2025-02-14',
        amount: 726.97,
        currency: 'USD',
      },
    ],
    total: 1,
    limit: 100,
    offset: 0,
  }
}

function renderAs(role: 'admin' | 'user' | null) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  if (role) {
    saveTokens({ accessToken: 'a', refreshToken: 'r' })
  }
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <PurchasesPage />
      </AuthProvider>
    </QueryClientProvider>,
  )
}

describe('PurchasesPage delete action', () => {
  let mock: MockAdapter

  beforeEach(() => {
    mock = new MockAdapter(apiClient)
    mock.onGet('/purchases/').reply(200, page())
    clearTokens()
  })

  it('shows no delete button for an unauthenticated viewer', async () => {
    renderAs(null)
    await waitFor(() => expect(screen.getByText('Katie Brown')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument()
  })

  it('shows no delete button for a non-admin user', async () => {
    mock.onGet('/users/me').reply(200, { username: 'alice', role: 'user' })
    renderAs('user')
    await waitFor(() => expect(screen.getByText('Katie Brown')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument()
  })

  it('shows a delete button for an admin, gated behind a confirm dialog', async () => {
    mock.onGet('/users/me').reply(200, { username: 'admin', role: 'admin' })
    mock.onDelete('/purchase/42').reply(200, { message: 'Purchase 42 deleted' })

    const user = userEvent.setup()
    renderAs('admin')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument())

    // No delete request until confirmed
    await user.click(screen.getByRole('button', { name: 'Delete' }))
    expect(mock.history.delete.length).toBe(0)
    expect(screen.getByText(/delete purchase #42/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByText(/delete purchase #42/i)).not.toBeInTheDocument()
    expect(mock.history.delete.length).toBe(0)

    await user.click(screen.getByRole('button', { name: 'Delete' }))
    const dialog = screen.getByRole('alertdialog')
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(mock.history.delete.length).toBe(1))
  })

  it('surfaces a 403 from the backend gracefully if it somehow occurs', async () => {
    mock.onGet('/users/me').reply(200, { username: 'admin', role: 'admin' })
    mock.onDelete('/purchase/42').reply(403, { detail: 'Admin access required' })

    const user = userEvent.setup()
    renderAs('admin')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'Delete' }))
    const dialog = screen.getByRole('alertdialog')
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(screen.getByText('Admin access required')).toBeInTheDocument())
    expect(dialog).toBeInTheDocument()
  })
})
