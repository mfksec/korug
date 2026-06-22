import client from './client'
import { ScanHistory } from '@/types'

export const scanAPI = {
  triggerScan: async (domain_id: number) => {
    const response = await client.post(`/api/scans/${domain_id}/scan`)
    return response.data
  },

  getProgress: async (domain_id: number) => {
    const response = await client.get(`/api/scans/${domain_id}/progress`)
    return response.data
  },

  getResults: async (domain_id: number) => {
    const response = await client.get(`/api/scans/${domain_id}/results`)
    return response.data
  },

  getHistory: async (domain_id: number, skip = 0, limit = 100) => {
    const response = await client.get<ScanHistory[]>(`/api/scans/history/${domain_id}`, {
      params: { skip, limit },
    })
    return response.data
  },

  cancel: async (domain_id: number) => {
    const response = await client.post(`/api/scans/${domain_id}/cancel`)
    return response.data
  },
}
