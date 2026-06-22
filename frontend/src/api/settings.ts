import client from './client'

export interface UserSettings {
  theme: 'light' | 'dark'
  notifications_enabled: boolean
  email_alerts: boolean
  scan_frequency: 'daily' | 'weekly' | 'monthly'
  export_format: 'json' | 'csv' | 'pdf'
}

export interface UserSettingsResponse {
  user_id: number
  settings: UserSettings
  updated_at: string
}

export interface APIKey {
  id: number
  name: string
  key: string
  created_at: string
  last_used: string | null
  is_active: boolean
}

export interface AuditLog {
  id: number
  user_id: number
  action: string
  resource: string | null
  details: string | null
  ip_address: string | null
  user_agent: string | null
  timestamp: string
  status: string
}

export interface AuditStats {
  total_actions: number
  by_action: Record<string, number>
  last_login: string
  api_keys_active: number
}

export const settingsAPI = {
  // User Settings
  getSettings: async (): Promise<UserSettingsResponse> => {
    const response = await client.get<UserSettingsResponse>('/api/settings/settings/user')
    return response.data
  },

  updateSettings: async (settings: UserSettings): Promise<UserSettingsResponse> => {
    const response = await client.post<UserSettingsResponse>('/api/settings/settings/user', settings)
    return response.data
  },

  // API Keys
  listApiKeys: async (): Promise<APIKey[]> => {
    const response = await client.get<APIKey[]>('/api/settings/apikeys')
    return response.data
  },

  createApiKey: async (name: string): Promise<APIKey> => {
    const response = await client.post<APIKey>('/api/settings/apikeys', { name })
    return response.data
  },

  revokeApiKey: async (keyId: number): Promise<APIKey> => {
    const response = await client.post<APIKey>(`/api/settings/apikeys/${keyId}/revoke`)
    return response.data
  },

  deleteApiKey: async (keyId: number) => {
    await client.delete(`/api/settings/apikeys/${keyId}`)
  },

  // Audit Logs
  listAuditLogs: async (limit: number = 100): Promise<AuditLog[]> => {
    const response = await client.get<AuditLog[]>('/api/settings/audit-logs', {
      params: { limit }
    })
    return response.data
  },

  getAuditLog: async (logId: number): Promise<AuditLog> => {
    const response = await client.get<AuditLog>(`/api/settings/audit-logs/${logId}`)
    return response.data
  },

  getAuditStats: async (): Promise<AuditStats> => {
    const response = await client.get<AuditStats>('/api/settings/audit-logs/stats/summary')
    return response.data
  },
}
