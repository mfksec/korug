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
  open_ports: number[]
  is_cloudflare: boolean
  first_discovered: string | null
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

export interface ScanResults {
  domain: { id: number; domain_name: string; enabled: boolean; last_scanned: string | null }
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
  triggerScan: async (domain_id: number) => {
    const response = await client.post(`/api/scans/${domain_id}/scan`)
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
}
