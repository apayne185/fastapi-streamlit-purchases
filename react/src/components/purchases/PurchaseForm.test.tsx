import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MockAdapter from 'axios-mock-adapter'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../../api/client'
import { PurchaseForm } from './PurchaseForm'

function renderForm(onCreated?: () => void) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <PurchaseForm onCreated={onCreated} />
    </QueryClientProvider>,
  )
}

describe('PurchaseForm', () => {
  let mock: MockAdapter

  beforeEach(() => {
    mock = new MockAdapter(apiClient)
  })

  it('rejects a non-positive amount before hitting the API', async () => {
    const user = userEvent.setup()
    renderForm()

    await user.type(screen.getByLabelText('Customer name'), 'Jane Doe')
    await user.type(screen.getByLabelText('Country'), 'France')
    await user.type(screen.getByLabelText('Purchase date'), '2026-01-01')
    await user.clear(screen.getByLabelText('Amount'))
    await user.type(screen.getByLabelText('Amount'), '0')
    await user.click(screen.getByRole('button', { name: /add purchase/i }))

    await waitFor(() =>
      expect(screen.getByText('Amount must be greater than 0')).toBeInTheDocument(),
    )
    expect(mock.history.post.length).toBe(0)
  })

  it('submits a valid purchase and surfaces the backend 400 for unsupported currency', async () => {
    mock.onPost('/purchase/').reply(400, { detail: 'Unsupported currency' })

    const user = userEvent.setup()
    renderForm()

    await user.type(screen.getByLabelText('Customer name'), 'Jane Doe')
    await user.type(screen.getByLabelText('Country'), 'France')
    await user.type(screen.getByLabelText('Purchase date'), '2026-01-01')
    await user.clear(screen.getByLabelText('Amount'))
    await user.type(screen.getByLabelText('Amount'), '42.50')
    await user.click(screen.getByRole('button', { name: /add purchase/i }))

    await waitFor(() => expect(screen.getByText('Unsupported currency')).toBeInTheDocument())
  })

  it('resets the form and calls onCreated after a successful submit', async () => {
    mock.onPost('/purchase/').reply(200, {
      id: 1,
      customer_name: 'Jane Doe',
      country: 'France',
      purchase_date: '2026-01-01',
      amount: 42.5,
      currency: 'USD',
    })
    const onCreated = vi.fn()

    const user = userEvent.setup()
    renderForm(onCreated)

    await user.type(screen.getByLabelText('Customer name'), 'Jane Doe')
    await user.type(screen.getByLabelText('Country'), 'France')
    await user.type(screen.getByLabelText('Purchase date'), '2026-01-01')
    await user.clear(screen.getByLabelText('Amount'))
    await user.type(screen.getByLabelText('Amount'), '42.50')
    await user.click(screen.getByRole('button', { name: /add purchase/i }))

    await waitFor(() => expect(onCreated).toHaveBeenCalledOnce())
    expect(screen.getByLabelText('Customer name')).toHaveValue('')
  })
})
