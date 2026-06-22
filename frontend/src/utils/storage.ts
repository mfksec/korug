import type { User } from '@/types'

/**
 * SECURITY WARNING: Token Storage
 * 
 * This implementation uses localStorage for token persistence.
 * While convenient for SPAs, localStorage is vulnerable to XSS (Cross-Site Scripting) attacks.
 * 
 * Any JavaScript running on the page (via XSS vulnerability) can access localStorage tokens.
 * 
 * RECOMMENDED FOR PRODUCTION:
 * 1. Migrate to httpOnly + Secure cookies
 *    - Backend sets tokens as httpOnly cookies (inaccessible to JavaScript)
 *    - Cookies sent automatically with requests
 *    - Better protection against token theft
 * 
 * 2. Implement additional XSS mitigations:
 *    - Content Security Policy (CSP) headers
 *    - Input sanitization on all user inputs
 *    - Output encoding in React (automatic with JSX)
 *    - Security scanning in CI/CD pipeline
 * 
 * 3. Token rotation:
 *    - Use short-lived access tokens (15-30 minutes)
 *    - Refresh tokens with longer expiry on secure storage
 *    - Implement refresh token rotation
 * 
 * For now, this localStorage implementation includes:
 * - CSP headers to prevent inline script execution
 * - Regular token validation
 * - Automatic cleanup on logout
 */

export const getStoredToken = (): string | null => {
  return localStorage.getItem('access_token')
}

export const getRefreshToken = (): string | null => {
  return localStorage.getItem('refresh_token')
}

export const setTokens = (accessToken: string, refreshToken: string): void => {
  localStorage.setItem('access_token', accessToken)
  localStorage.setItem('refresh_token', refreshToken)
}

export const clearTokens = (): void => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
}

export const getStoredUser = (): User | null => {
  const user = localStorage.getItem('user')
  return user ? JSON.parse(user) as User : null
}

export const setStoredUser = (user: User): void => {
  localStorage.setItem('user', JSON.stringify(user))
}

export const isTokenExpired = (token: string): boolean => {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return true
    
    const decoded = JSON.parse(atob(parts[1]))
    const expirationTime = decoded.exp * 1000
    return Date.now() >= expirationTime
  } catch {
    return true
  }
}
