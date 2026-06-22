import client from './client'
import { Vulnerability, PaginationParams } from '@/types'

interface VulnStats {
  total: number
  critical: number
  high: number
  medium: number
  low: number
  avg_confidence: number
  by_type: Record<string, number>
}

interface TimelineData {
  date: string
  count: number
}

interface ConfidenceDistribution {
  severity: string
  score_range: string
  count: number
  percentage: number
}

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
    const response = await client.patch<Vulnerability>(`/api/vulnerabilities/${id}`, {
      is_false_positive: true,
      false_positive_reason: reason,
    })
    return response.data
  },

  unmarkFalsePositive: async (id: number) => {
    const response = await client.patch<Vulnerability>(`/api/vulnerabilities/${id}`, {
      is_false_positive: false,
      false_positive_reason: null,
    })
    return response.data
  },

  // Chart/Analytics endpoints
  getStats: async (): Promise<VulnStats> => {
    const response = await client.get<VulnStats>('/api/vulnerabilities/stats/summary')
    return response.data
  },

  getTimeline: async (days: number = 30): Promise<TimelineData[]> => {
    const response = await client.get<TimelineData[]>('/api/vulnerabilities/stats/timeline', {
      params: { days }
    })
    return response.data
  },

  getConfidenceDistribution: async (): Promise<ConfidenceDistribution[]> => {
    const response = await client.get<ConfidenceDistribution[]>('/api/vulnerabilities/stats/confidence-distribution')
    return response.data
  },
}
