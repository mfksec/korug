import client from './client'
import { ScanHistory } from '@/types'

export interface EnrichedSubdomain {
  id: number
  subdomain: string
  sources: string[]
  resolved_ips: string[]
  cname: string | null
  is_alive: boolean
  status_code: number | null
  final_url: string | null
  http_title: string | null
  content_length: number | null
  web_server: string | null
  technologies: string[]
  open_ports: OpenPort[]
  is_cloudflare: boolean
  is_gone: boolean
  first_discovered: string | null
}

export interface OpenPort {
  port: number
  proto?: string
  service?: string
  product?: string
  version?: string
}

export interface ScanVulnerability {
  id: number
  subdomain_id: number
  vuln_type: string
  confidence_score: number
  details: string | null
  is_false_positive: boolean
  found_at: string | null
}

export interface IpGroup {
  ip: string
  subdomains: string[]
  count: number
}

export interface ScanStatus {
  id: number
  domain_id: number
  status: string
  is_active: boolean
  scan_timestamp: string | null
  total_subdomains: number
  new_subdomains: number
  vulnerabilities_found: number
  scan_duration_seconds: number | null
  error_message: string | null
}

export interface DnsRecords {
  A: string[]
  AAAA: string[]
  CNAME: string | null
  MX: string[]
  NS: string[]
}

export interface Asset extends EnrichedSubdomain {
  domain_id: number
  domain_name: string
  dns_records: DnsRecords
  resolves: boolean
  is_gone: boolean
  last_seen: string | null
}

export interface Certificate {
  id: number
  subdomain_id: number
  domain_id: number
  issuer: string | null
  common_name: string | null
  sans: string[]
  serial_number: string | null
  not_before: string | null
  not_after: string | null
  source: string | null
  first_seen: string | null
  last_seen: string | null
}

export interface AssetChange {
  id: number
  domain_id: number
  domain_name?: string | null
  subdomain_id: number | null
  scan_id: number | null
  change_type: string
  target: string | null
  old_value: string | null
  new_value: string | null
  detected_at: string | null
}

export interface SubdomainDetail {
  asset: Asset & { gone_at: string | null }
  vulnerabilities: ScanVulnerability[]
  certificates: Certificate[]
  changes: AssetChange[]
}

export interface AssetList {
  total: number
  count: number
  assets: Asset[]
}

export interface ScanResults {
  domain: { id: number; domain_name: string; enabled: boolean; monitor_mode?: 'active' | 'passive'; last_scanned: string | null }
  counts: { subdomains: number; alive: number; vulnerabilities: number; cloudflare: number }
  ip_groups: IpGroup[]
  subdomains: EnrichedSubdomain[]
  vulnerabilities: ScanVulnerability[]
  last_scan: {
    status: string
    scan_timestamp: string | null
    total_subdomains: number
    new_subdomains: number
    vulnerabilities_found: number
    scan_duration_seconds: number | null
  } | null
}

export const scanAPI = {
  triggerScan: async (domain_id: number, portScan?: boolean) => {
    const params = portScan === undefined ? {} : { port_scan: portScan }
    const response = await client.post(`/api/scans/${domain_id}/scan`, null, { params })
    return response.data
  },

  getResults: async (domain_id: number): Promise<ScanResults> => {
    const response = await client.get<ScanResults>(`/api/scans/${domain_id}/results`)
    return response.data
  },

  getHistory: async (domain_id: number, skip = 0, limit = 100) => {
    const response = await client.get<ScanHistory[]>(`/api/scans/history/${domain_id}`, {
      params: { skip, limit },
    })
    return response.data
  },

  cancelScan: async (domain_id: number) => {
    const response = await client.post(`/api/scans/${domain_id}/scan/cancel`)
    return response.data
  },

  getStatus: async (domain_id: number): Promise<{ domain_id: number; last_scan: ScanStatus | null }> => {
    const response = await client.get(`/api/scans/${domain_id}/scan/status`)
    return response.data
  },

  getActiveScans: async (): Promise<ScanStatus[]> => {
    const response = await client.get<ScanStatus[]>('/api/scans/active')
    return response.data
  },

  scanSubdomain: async (subdomain_id: number, portScan?: boolean): Promise<{ asset: Asset; new_vulnerabilities: number }> => {
    const params = portScan === undefined ? {} : { port_scan: portScan }
    const response = await client.post(`/api/scans/subdomain/${subdomain_id}/scan`, null, { params })
    return response.data
  },

  getSubdomainDetail: async (subdomain_id: number): Promise<SubdomainDetail> => {
    const response = await client.get<SubdomainDetail>(`/api/scans/subdomain/${subdomain_id}`)
    return response.data
  },

  refreshCertificates: async (subdomain_id: number): Promise<{ new_certificates: number; certificates: Certificate[] }> => {
    const response = await client.post(`/api/scans/subdomain/${subdomain_id}/certificates/refresh`)
    return response.data
  },

  listAssets: async (params: {
    domain_id?: number
    q?: string
    alive?: boolean
    resolved?: boolean
    gone?: boolean
    sort?: string
    dir?: 'asc' | 'desc'
    skip?: number
    limit?: number
  } = {}): Promise<AssetList> => {
    const response = await client.get<AssetList>('/api/scans/assets', { params })
    return response.data
  },
}
