import { useEffect, useMemo, useState, ReactNode } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider, CssBaseline } from '@mui/material'
import { useAuth } from '@/hooks/useAuth'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { ProtectedRoute } from '@/components/routing/ProtectedRoute'
import { AppLayout } from '@/components/layout/AppLayout'
import { createAppTheme, ColorModeContext, AppMode, MODE_STORAGE_KEY } from '@/styles/theme'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { DomainsPage } from './pages/DomainsPage'
import { DomainDetailPage } from './pages/DomainDetailPage'
import { AssetsPage } from './pages/AssetsPage'
import { VulnerabilitiesPage } from './pages/VulnerabilitiesPage'
import { AlertsPage } from './pages/AlertsPage'
import { IntegrationsPage } from './pages/IntegrationsPage'
import { SettingsPage } from './pages/SettingsPage'
import { ProfilePage } from './pages/ProfilePage'
import { AuditLogsPage } from './pages/AuditLogsPage'
import { UsersPage } from './pages/UsersPage'
import { NotFound } from './pages/NotFound'

/** Route guard that only admits admins; others bounce to the dashboard. */
function RequireAdmin({ children }: { children: ReactNode }) {
  const { isAdmin, isLoading } = useAuth()
  if (isLoading) return <LoadingSpinner message="Loading…" />
  return isAdmin ? <>{children}</> : <Navigate to="/dashboard" replace />
}

function ThemeModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<AppMode>(
    () => (localStorage.getItem(MODE_STORAGE_KEY) as AppMode) || 'dark'
  )
  useEffect(() => { localStorage.setItem(MODE_STORAGE_KEY, mode) }, [mode])

  const ctx = useMemo(() => ({
    mode,
    toggle: () => setMode((m) => (m === 'dark' ? 'light' : 'dark')),
    set: (m: AppMode) => setMode(m),
  }), [mode])

  const theme = useMemo(() => createAppTheme(mode), [mode])

  return (
    <ColorModeContext.Provider value={ctx}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ColorModeContext.Provider>
  )
}

function App() {
  const { isAuthenticated, checkAuth } = useAuth()
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    const init = async () => { await checkAuth(); setIsReady(true) }
    init()
  }, [checkAuth])

  return (
    <ThemeModeProvider>
      {!isReady ? (
        <LoadingSpinner message="Loading…" />
      ) : (
        <BrowserRouter>
          <Routes>
            <Route
              path="/login"
              element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage onLoginSuccess={() => {}} />}
            />

            <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/domains" element={<DomainsPage />} />
              <Route path="/domains/:id" element={<DomainDetailPage />} />
              <Route path="/assets" element={<AssetsPage />} />
              <Route path="/vulnerabilities" element={<VulnerabilitiesPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/integrations" element={<IntegrationsPage />} />
              <Route path="/audit-logs" element={<AuditLogsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/users" element={<RequireAdmin><UsersPage /></RequireAdmin>} />
            </Route>

            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      )}
    </ThemeModeProvider>
  )
}

export default App
