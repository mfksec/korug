import axios, { AxiosInstance, AxiosError } from 'axios'

/**
 * SECURITY NOTE: Token Refresh & Auto-Retry
 * 
 * This client implements automatic token refresh on 401 responses.
 * It reads the refresh token from localStorage and exchanges it for a new access token.
 * 
 * SECURITY RISKS & MITIGATIONS:
 * 
 * 1. Refresh Token Theft (localStorage → XSS)
 *    Risk: If XSS occurs, attacker can steal refresh token (7-day validity)
 *    Status: Partially addressed by CSP headers, but full mitigation requires httpOnly cookies
 *    Action: Use httpOnly secure cookies in production
 * 
 * 2. Token Leakage in Logs
 *    Risk: Full tokens could appear in error logs if not careful
 *    Status: This implementation does NOT log full tokens
 *    Action: Maintain this practice; use token ID or user ID instead
 * 
 * 3. Silent Token Refresh Loop
 *    Risk: If refresh endpoint is broken, this could create infinite loop
 *    Status: Error handling stops loop and redirects to login
 *    Action: Monitor for excessive refresh token errors
 * 
 * PRODUCTION IMPROVEMENTS:
 * - Migrate to httpOnly + Secure cookies for token storage
 * - Implement token rotation (new refresh token on each refresh)
 * - Add max refresh attempts before forcing re-login
 * - Use request signing/fingerprinting to detect token reuse
 * - Implement refresh token revocation on logout
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const client: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle token refresh
client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as (typeof error.config & { _retry?: boolean })
    if (error.response?.status === 401 && !originalRequest?._retry) {
      if (originalRequest) {
        originalRequest._retry = true
      }
      try {
        const refresh_token = localStorage.getItem('refresh_token')
        if (!refresh_token) {
          throw new Error('No refresh token')
        }
        
        const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
          refresh_token,
        })
        
        const { access_token } = response.data
        localStorage.setItem('access_token', access_token)
        client.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
        return client(originalRequest!)
      } catch (refreshError) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }
    return Promise.reject(error)
  }
)

export default client

