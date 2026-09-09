import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MockAdapter from 'axios-mock-adapter'
import { beforeEach, describe, expect, it } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'

import { apiClient } from '../api/client'
import { clearTokens } from '../api/tokenStorage'
import { AuthProvider } from '../auth/AuthProvider'
import { LoginPage } from './LoginPage'

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<div>Home</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  let mock: MockAdapter

  beforeEach(() => {
    mock = new MockAdapter(apiClient)
    clearTokens()
  })

  it('logs in with valid credentials and navigates home', async () => {
    mock.onPost('/token').reply((config) => {
      expect(config.headers?.['Content-Type']).toBe('application/x-www-form-urlencoded')
      expect(config.data).toBe('username=clitestuser&password=password123')
      return [200, { access_token: 'a', refresh_token: 'r', token_type: 'bearer' }]
    })
    mock.onGet('/users/me').reply(200, { username: 'clitestuser', role: 'user' })

    const user = userEvent.setup()
    renderLoginPage()

    await user.type(screen.getByLabelText('Username'), 'clitestuser')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => expect(screen.getByText('Home')).toBeInTheDocument())
  })

  it('shows the backend error message on bad credentials', async () => {
    mock.onPost('/token').reply(401, { detail: 'Incorrect username or password' })

    const user = userEvent.setup()
    renderLoginPage()

    await user.type(screen.getByLabelText('Username'), 'wrong')
    await user.type(screen.getByLabelText('Password'), 'wrong12345')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() =>
      expect(screen.getByText('Incorrect username or password')).toBeInTheDocument(),
    )
  })
})
