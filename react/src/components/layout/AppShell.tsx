import type { ReactNode } from 'react'
import { NavLink } from 'react-router'

import { useAuth } from '../../auth/useAuth'
import { Button } from '../ui/Button'

const NAV_LINK_CLASS = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium ${
    isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'
  }`

export function AppShell({ children }: { children: ReactNode }) {
  const { user, isAuthenticated, isAdmin, logout } = useAuth()

  return (
    <div className="min-h-svh bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-6">
            <span className="text-lg font-semibold text-slate-900">PulseMetrics</span>
            <nav className="flex gap-1">
              <NavLink to="/" end className={NAV_LINK_CLASS}>
                Purchases
              </NavLink>
              <NavLink to="/dashboard" className={NAV_LINK_CLASS}>
                Dashboard
              </NavLink>
              {isAuthenticated && (
                <>
                  <NavLink to="/purchases/new" className={NAV_LINK_CLASS}>
                    New Purchase
                  </NavLink>
                  <NavLink to="/purchases/bulk" className={NAV_LINK_CLASS}>
                    Bulk Upload
                  </NavLink>
                </>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <>
                <span className="text-sm text-slate-600">
                  {user?.username}
                  {isAdmin && (
                    <span className="ml-1.5 rounded bg-indigo-100 px-1.5 py-0.5 text-xs font-medium text-indigo-700">
                      admin
                    </span>
                  )}
                </span>
                <Button variant="secondary" onClick={logout}>
                  Sign out
                </Button>
              </>
            ) : (
              <NavLink to="/login" className={NAV_LINK_CLASS}>
                Sign in
              </NavLink>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  )
}
