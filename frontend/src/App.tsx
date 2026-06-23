import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { ProtectedRoute } from '@/components/routing/ProtectedRoute'
import { AppLayout } from '@/components/layout/AppLayout'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { VulnerabilitiesPage } from './pages/VulnerabilitiesPage'
import { AlertsPage } from './pages/AlertsPage'
import { SettingsPage } from './pages/SettingsPage'
import { AuditLogsPage } from './pages/AuditLogsPage'
import { UsersPage } from './pages/UsersPage'
import { IntegrationsPage } from './pages/IntegrationsPage'
import { ProfilePage } from './pages/ProfilePage'
import { NotFound } from './pages/NotFound'

/** Route guard that only admits admins; others bounce to the dashboard. */
const RequireAdmin: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAdmin, isLoading } = useAuth()
  if (isLoading) return <LoadingSpinner message="Loading..." />
  return isAdmin ? <>{children}</> : <Navigate to="/dashboard" replace />
}

function App() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <LoadingSpinner message="Loading..." />
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage onLoginSuccess={() => {}} />}
        />

        {/* Authenticated app shell */}
        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/vulnerabilities" element={<VulnerabilitiesPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/integrations" element={<IntegrationsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/audit-logs" element={<AuditLogsPage />} />
          <Route path="/users" element={<RequireAdmin><UsersPage /></RequireAdmin>} />
        </Route>

        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
