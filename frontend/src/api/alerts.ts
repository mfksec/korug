import client from './client'

export interface Alert {
  id: number
  domain: string
  alert_type: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  message: string
  created_at: string
  resolved_at: string | null
  is_resolved: boolean
}

export interface AlertStats {
  total: number
  active: number
  resolved: number
  by_severity: {
    critical: number
    high: number
    medium: number
    low: number
  }
}

export const alertAPI = {
  list: async (status: 'all' | 'active' | 'resolved' = 'all', limit: number = 100) => {
    const response = await client.get<Alert[]>('/api/alerts/', {
      params: { status, limit }
    })
    return response.data
  },

  get: async (id: number) => {
    const response = await client.get<Alert>(`/api/alerts/${id}`)
    return response.data
  },

  resolve: async (id: number) => {
    const response = await client.post<Alert>(`/api/alerts/${id}/resolve`)
    return response.data
  },

  unresolve: async (id: number) => {
    const response = await client.post<Alert>(`/api/alerts/${id}/unresolve`)
    return response.data
  },

  delete: async (id: number) => {
    await client.delete(`/api/alerts/${id}`)
  },

  getStats: async (): Promise<AlertStats> => {
    const response = await client.get<AlertStats>('/api/alerts/stats/summary')
    return response.data
  },
}
