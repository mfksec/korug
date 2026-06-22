import client from './client'
import { LoginRequest, LoginResponse } from '@/types'

export const authAPI = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const response = await client.post('/api/auth/login', credentials)
    return response.data
  },

  logout: async (): Promise<void> => {
    await client.post('/api/auth/logout')
  },

  me: async () => {
    const response = await client.get('/api/auth/me')
    return response.data
  },

  refreshToken: async (refresh_token: string): Promise<{ access_token: string }> => {
    const response = await client.post('/api/auth/refresh', { refresh_token })
    return response.data
  },
}
