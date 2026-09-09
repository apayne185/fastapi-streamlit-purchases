import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MockAdapter from 'axios-mock-adapter'
import { beforeEach, describe, expect, it } from 'vitest'

import { apiClient } from '../api/client'
import { clearTokens, loadTokens, saveTokens } from '../api/tokenStorage'
import { AuthProvider } from './AuthProvider'
import { useAuth } from './useAuth'

function Probe() {
  const auth = useAuth()
  return (
    <div>
      <span data-testid="state">
        {auth.isLoading ? 'loading' : auth.isAuthenticated ? `in:${auth.user?.role}` : 'out'}
      </span>
      <button onClick={() => auth.login('alice', 'password123')}>login</button>
      <button onClick={() => auth.register('bob', 'password123')}>register</button>
      <button onClick={() => auth.logout()}>logout</button>
    </div>
  )
}

describe('AuthProvider', () => {
  let mock: MockAdapter

  beforeEach(() => {
    mock = new MockAdapter(apiClient)
    clearTokens()
  })

  it('starts logged out with no stored tokens', async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('out'))
  })

  it('hydrates the user from stored tokens on boot', async () => {
    saveTokens({ accessToken: 'a', refreshToken: 'r' })
    mock.onGet('/users/me').reply(200, { username: 'alice', role: 'admin' })

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('in:admin'))
  })

  it('logs in, storing tokens and fetching the role', async () => {
    mock.onPost('/token').reply(200, {
      access_token: 'a',
      refresh_token: 'r',
      token_type: 'bearer',
    })
    mock.onGet('/users/me').reply(200, { username: 'alice', role: 'user' })

    const user = userEvent.setup()
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('out'))

    await act(() => user.click(screen.getByText('login')))

    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('in:user'))
    expect(loadTokens()).toEqual({ accessToken: 'a', refreshToken: 'r' })
  })

  it('register chains into login automatically', async () => {
    mock.onPost('/register').reply(200, { username: 'bob', role: 'user' })
    mock.onPost('/token').reply(200, {
      access_token: 'a',
      refresh_token: 'r',
      token_type: 'bearer',
    })
    mock.onGet('/users/me').reply(200, { username: 'bob', role: 'user' })

    const user = userEvent.setup()
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('out'))

    await act(() => user.click(screen.getByText('register')))

    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('in:user'))
  })

  it('logout clears user state and stored tokens', async () => {
    saveTokens({ accessToken: 'a', refreshToken: 'r' })
    mock.onGet('/users/me').reply(200, { username: 'alice', role: 'user' })

    const user = userEvent.setup()
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('in:user'))

    await act(() => user.click(screen.getByText('logout')))

    expect(screen.getByTestId('state')).toHaveTextContent('out')
    expect(loadTokens()).toBeNull()
  })
})
