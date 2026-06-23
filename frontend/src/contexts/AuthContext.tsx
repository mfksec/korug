import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { authAPI } from '@/api/auth'
import { User, LoginRequest } from '@/types'
import { setTokens, clearTokens, getStoredToken } from '@/utils/storage'

interface AuthContextValue {
  isAuthenticated: boolean
  user: User | null
  isAdmin: boolean
  isLoading: boolean
  error: string | null
  login: (credentials: LoginRequest) => Promise<boolean>
  logout: () => Promise<void>
  checkAuth: () => Promise<boolean>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!!getStoredToken())
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const login = useCallback(async (credentials: LoginRequest): Promise<boolean> => {
    setError(null)
    try {
      const response = await authAPI.login(credentials)
      setTokens(response.access_token, response.refresh_token)
      const userInfo = await authAPI.me()
      setUser(userInfo)
      setIsAuthenticated(true)
      return true
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed')
      return false
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await authAPI.logout()
    } catch (err) {
      console.error('Logout error:', err)
    } finally {
      clearTokens()
      setUser(null)
      setIsAuthenticated(false)
    }
  }, [])

  const checkAuth = useCallback(async (): Promise<boolean> => {
    if (!getStoredToken()) {
      setIsAuthenticated(false)
      return false
    }
    try {
      const userInfo = await authAPI.me()
      setUser(userInfo)
      setIsAuthenticated(true)
      return true
    } catch {
      clearTokens()
      setIsAuthenticated(false)
      return false
    }
  }, [])

  const refreshUser = useCallback(async () => {
    try {
      setUser(await authAPI.me())
    } catch (err) {
      console.error('Failed to refresh user:', err)
    }
  }, [])

  useEffect(() => {
    checkAuth().finally(() => setIsLoading(false))
  }, [checkAuth])

  const value: AuthContextValue = {
    isAuthenticated,
    user,
    isAdmin: user?.role === 'admin',
    isLoading,
    error,
    login,
    logout,
    checkAuth,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
