import client from './client'
import { Domain, Subdomain, ScanHistory, PaginationParams } from '@/types'

export interface DashboardStats {
  total_domains: number
  total_vulnerabilities: number
  active_scans: number
  high_risk_domains: number
}

export const domainAPI = {
  list: async (params?: PaginationParams) => {
    const response = await client.get<Domain[]>('/api/domains/', { params })
    return response.data
  },

  getDashboardStats: async (): Promise<DashboardStats> => {
    const response = await client.get<DashboardStats>('/api/domains/stats/dashboard')
    return response.data
  },

  get: async (id: number) => {
    const response = await client.get<Domain>(`/api/domains/${id}`)
    return response.data
  },

  create: async (domain_name: string, monitor_mode: 'active' | 'passive' = 'active') => {
    const response = await client.post<Domain>('/api/domains/', { domain_name, monitor_mode })
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
