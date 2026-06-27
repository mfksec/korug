import client from './client'
import type { AssetChange } from './scans'

export type { AssetChange }

export interface ChangeList {
  total: number
  count: number
  changes: AssetChange[]
}

export interface ChangeStats {
  total: number
  since_days: number
  by_type: Record<string, number>
}

export const changeAPI = {
  list: async (params: {
    domain_id?: number
    change_type?: string
    since_days?: number
    sort?: string
    dir?: 'asc' | 'desc'
    skip?: number
    limit?: number
  } = {}): Promise<ChangeList> => {
    const response = await client.get<ChangeList>('/api/changes/', { params })
    return response.data
  },

  getStats: async (sinceDays = 7): Promise<ChangeStats> => {
    const response = await client.get<ChangeStats>('/api/changes/stats/summary', {
      params: { since_days: sinceDays },
    })
    return response.data
  },
}
