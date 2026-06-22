import React, { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'

function App() {
  const { isAuthenticated, logout, checkAuth } = useAuth()
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    const initAuth = async () => {
      await checkAuth()
      setIsReady(true)
    }
    initAuth()
  }, [checkAuth])

  if (!isReady) {
    return <div>Loading...</div>
  }

  const handleLogout = async () => {
    await logout()
  }

  const handleLoginSuccess = async () => {
    await checkAuth()
  }

  return isAuthenticated ? (
    <DashboardPage onLogout={handleLogout} />
  ) : (
    <LoginPage onLoginSuccess={handleLoginSuccess} />
  )
}

export default App
