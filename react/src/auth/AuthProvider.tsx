import { useCallback, useEffect, useState, type ReactNode } from 'react'

import { fetchCurrentUser, login as loginRequest, register as registerRequest } from '../api/auth'
import { setUnauthorizedHandler } from '../api/client'
import { clearTokens, loadTokens, saveTokens } from '../api/tokenStorage'
import type { User } from '../api/types'
import { AuthContext, type AuthContextValue } from './AuthContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    return () => setUnauthorizedHandler(null)
  }, [logout])

  useEffect(() => {
    // Boot-time check against localStorage + network, not a render-derivable
    // value — an effect is the right tool here, not a lint false positive.
    if (!loadTokens()) {
      setIsLoading(false)
      return
    }
    fetchCurrentUser()
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const token = await loginRequest(username, password)
    saveTokens({ accessToken: token.access_token, refreshToken: token.refresh_token })
    const me = await fetchCurrentUser()
    setUser(me)
  }, [])

  const register = useCallback(async (username: string, password: string) => {
    await registerRequest({ username, password })
    await login(username, password)
  }, [login])

  const value: AuthContextValue = {
    user,
    isAuthenticated: user !== null,
    isAdmin: user?.role === 'admin',
    isLoading,
    login,
    register,
    logout,
  }

  return <AuthContext value={value}>{children}</AuthContext>
}
