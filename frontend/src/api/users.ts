import client from './client'
import { User } from '@/types'

export interface CreateUserPayload {
  username: string
  email: string
  password: string
  role: string
}

export interface AdminUpdateUserPayload {
  email?: string
  role?: string
  is_active?: boolean
}

export const userAPI = {
  list: async (): Promise<User[]> => {
    const res = await client.get<User[]>('/api/users/')
    return res.data
  },

  create: async (payload: CreateUserPayload): Promise<User> => {
    const res = await client.post<User>('/api/users/', payload)
    return res.data
  },

  update: async (id: number, payload: AdminUpdateUserPayload): Promise<User> => {
    const res = await client.patch<User>(`/api/users/${id}`, payload)
    return res.data
  },

  remove: async (id: number): Promise<void> => {
    await client.delete(`/api/users/${id}`)
  },

  resetPassword: async (id: number, newPassword: string): Promise<void> => {
    await client.post(`/api/users/${id}/password`, { new_password: newPassword })
  },

  // Self-service
  updateProfile: async (email: string): Promise<User> => {
    const res = await client.patch<User>('/api/users/me', { email })
    return res.data
  },

  changePassword: async (currentPassword: string, newPassword: string): Promise<void> => {
    await client.post('/api/users/me/password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },
}
