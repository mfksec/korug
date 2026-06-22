import client from './client'
import { Domain, Subdomain, ScanHistory, PaginationParams } from '@/types'

export const domainAPI = {
  list: async (params?: PaginationParams) => {
    const response = await client.get<Domain[]>('/api/domains/', { params })
    return response.data
  },

  get: async (id: number) => {
    const response = await client.get<Domain>(`/api/domains/${id}`)
    return response.data
  },

  create: async (domain_name: string) => {
    const response = await client.post<Domain>('/api/domains/', { domain_name })
    return response.data
  },

  update: async (id: number, data: Partial<Domain>) => {
    const response = await client.put<Domain>(`/api/domains/${id}`, data)
    return response.data
  },

  delete: async (id: number) => {
    await client.delete(`/api/domains/${id}`)
  },

  getSubdomains: async (domainId: number) => {
    const response = await client.get<Subdomain[]>(`/api/scans/${domainId}/results`)
    return response.data
  },

  getScanHistory: async (domainId: number, params?: PaginationParams) => {
    const response = await client.get<ScanHistory[]>(`/api/scans/history/${domainId}`, { params })
    return response.data
  },
}
