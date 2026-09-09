import { afterEach, describe, expect, it, vi } from 'vitest'

describe('API_URL resolution', () => {
  afterEach(() => {
    delete (window as { __ENV__?: unknown }).__ENV__
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('prefers window.__ENV__.API_URL when set (production/container)', async () => {
    window.__ENV__ = { API_URL: 'https://api.prod.example' }
    const { API_URL } = await import('./config')
    expect(API_URL).toBe('https://api.prod.example')
  })

  it('falls back to VITE_API_URL when window.__ENV__ has no value (dev with .env)', async () => {
    window.__ENV__ = {}
    vi.stubEnv('VITE_API_URL', 'http://localhost:9000')
    const { API_URL } = await import('./config')
    expect(API_URL).toBe('http://localhost:9000')
  })

  it('falls back to the localhost default when nothing else is set (dev with no config)', async () => {
    window.__ENV__ = {}
    const { API_URL } = await import('./config')
    expect(API_URL).toBe('http://localhost:8000')
  })
})
