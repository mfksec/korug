import client from './client'
import { Vulnerability, PaginationParams } from '@/types'

export const vulnerabilityAPI = {
  list: async (params?: PaginationParams & { domain_id?: number }) => {
    const response = await client.get<Vulnerability[]>('/api/vulnerabilities/', { params })
    return response.data
  },

  get: async (id: number) => {
    const response = await client.get<Vulnerability>(`/api/vulnerabilities/${id}`)
    return response.data
  },

  markFalsePositive: async (id: number, reason: string) => {
    const response = await client.put<Vulnerability>(`/api/vulnerabilities/${id}`, {
      is_false_positive: true,
      false_positive_reason: reason,
    })
    return response.data
  },

  unmarkFalsePositive: async (id: number) => {
    const response = await client.put<Vulnerability>(`/api/vulnerabilities/${id}`, {
      is_false_positive: false,
      false_positive_reason: null,
    })
    return response.data
  },
}
