import client from './client'

export interface SlackStatus {
  enabled: boolean
  webhook_configured: boolean
  webhook_url: string // masked
}

export interface EmailStatus {
  enabled: boolean
  smtp_host: string
  smtp_port: number
  smtp_user: string
  password_configured: boolean
  smtp_password: string // masked
  use_tls: boolean
  from_address: string
  to_addresses: string
}

export const RECON_KEY_FIELDS = [
  'shodan_api_key', 'virustotal_api_key', 'securitytrails_api_key',
  'binaryedge_api_key', 'urlscan_api_key', 'censys_api_id', 'censys_api_secret',
] as const
export type ReconKeyField = typeof RECON_KEY_FIELDS[number]

// Masked status: `${field}` (masked value) + `${field}_configured` flag.
export type ReconKeysStatus = Record<string, string | boolean>
export type ReconKeysUpdate = Partial<Record<ReconKeyField, string | null>>

export interface IntegrationsResponse {
  slack: SlackStatus
  email: EmailStatus
  recon_keys: ReconKeysStatus
}

export interface SlackUpdate {
  enabled: boolean
  webhook_url?: string | null
}

export interface EmailUpdate {
  enabled: boolean
  smtp_host?: string | null
  smtp_port: number
  smtp_user?: string | null
  smtp_password?: string | null
  use_tls: boolean
  from_address?: string | null
  to_addresses?: string | null
}

export interface TestResult {
  status: string
  message: string
}

export const integrationAPI = {
  get: async (): Promise<IntegrationsResponse> => {
    const res = await client.get<IntegrationsResponse>('/api/integrations/')
    return res.data
  },

  updateSlack: async (payload: SlackUpdate): Promise<SlackStatus> => {
    const res = await client.put<SlackStatus>('/api/integrations/slack', payload)
    return res.data
  },

  updateEmail: async (payload: EmailUpdate): Promise<EmailStatus> => {
    const res = await client.put<EmailStatus>('/api/integrations/email', payload)
    return res.data
  },

  testSlack: async (): Promise<TestResult> => {
    const res = await client.post<TestResult>('/api/integrations/slack/test')
    return res.data
  },

  testEmail: async (): Promise<TestResult> => {
    const res = await client.post<TestResult>('/api/integrations/email/test')
    return res.data
  },

  updateReconKeys: async (payload: ReconKeysUpdate): Promise<ReconKeysStatus> => {
    const res = await client.put<ReconKeysStatus>('/api/integrations/recon-keys', payload)
    return res.data
  },
}
