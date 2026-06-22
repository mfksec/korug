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

export const getStoredUser = (): any => {
  const user = localStorage.getItem('user')
  return user ? JSON.parse(user) : null
}

export const setStoredUser = (user: any): void => {
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
