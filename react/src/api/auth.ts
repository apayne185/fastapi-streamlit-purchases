import { apiClient } from './client'
import type { RegisterRequest, Token, User } from './types'

export async function login(username: string, password: string): Promise<Token> {
  const form = new URLSearchParams()
  form.set('username', username)
  form.set('password', password)

  const { data } = await apiClient.post<Token>('/token', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

export async function register(request: RegisterRequest): Promise<User> {
  const { data } = await apiClient.post<User>('/register', request)
  return data
}

export async function fetchCurrentUser(): Promise<User> {
  const { data } = await apiClient.get<User>('/users/me')
  return data
}
