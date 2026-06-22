import { useState, useCallback } from 'react'
import { authAPI } from '@/api/auth'
import { User, LoginRequest } from '@/types'
import { setTokens, clearTokens, getStoredToken, getRefreshToken } from '@/utils/storage'

export const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!!getStoredToken())
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const login = useCallback(async (credentials: LoginRequest) => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await authAPI.login(credentials)
      setTokens(response.access_token, response.refresh_token)
      
      // Fetch user info
      const userInfo = await authAPI.me()
      setUser(userInfo)
      setIsAuthenticated(true)
      return true
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Login failed'
      setError(message)
      return false
    } finally {
      setIsLoading(false)
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

  const checkAuth = useCallback(async () => {
    const token = getStoredToken()
    if (!token) {
      setIsAuthenticated(false)
      return false
    }

    try {
      const userInfo = await authAPI.me()
      setUser(userInfo)
      setIsAuthenticated(true)
      return true
    } catch (err) {
      clearTokens()
      setIsAuthenticated(false)
      return false
    }
  }, [])

  return {
    isAuthenticated,
    user,
    isLoading,
    error,
    login,
    logout,
    checkAuth,
  }
}
