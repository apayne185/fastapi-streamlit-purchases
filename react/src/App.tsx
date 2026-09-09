import type { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router'

import { ProtectedRoute } from './auth/ProtectedRoute'
import { useAuth } from './auth/useAuth'
import { AppShell } from './components/layout/AppShell'
import { BulkUploadPage } from './pages/BulkUploadPage'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { NewPurchasePage } from './pages/NewPurchasePage'
import { NotFoundPage } from './pages/NotFoundPage'
import { PurchasesPage } from './pages/PurchasesPage'
import { RegisterPage } from './pages/RegisterPage'

function RedirectIfAuthenticated({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <Navigate to="/" replace /> : children
}

function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <RedirectIfAuthenticated>
            <LoginPage />
          </RedirectIfAuthenticated>
        }
      />
      <Route
        path="/register"
        element={
          <RedirectIfAuthenticated>
            <RegisterPage />
          </RedirectIfAuthenticated>
        }
      />
      <Route
        path="/*"
        element={
          <AppShell>
            <Routes>
              <Route path="/" element={<PurchasesPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route
                path="/purchases/new"
                element={
                  <ProtectedRoute>
                    <NewPurchasePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/purchases/bulk"
                element={
                  <ProtectedRoute>
                    <BulkUploadPage />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </AppShell>
        }
      />
    </Routes>
  )
}

export default App
