// Domain risk + UI-facing types layered on top of the API types.
// The base API interfaces remain in their original shape; these add the
// fields the redesigned dashboard renders.

export type RiskLevel = 'high' | 'medium' | 'low' | 'none'
export type VulnType = 's3_bucket_takeover' | 'cname_orphan' | 'dns_orphan'
export type VulnStatus = 'open' | 'false_positive'
export type SubdomainStatus = 'live' | 'orphan' | 'dns_orphan'
export type AlertSeverity = 'high' | 'medium' | 'info'

export interface Domain {
  id: number
  domain_name: string
  enabled: boolean
  last_scanned: string | null
  subdomain_count: number
  open_vulnerabilities: number
  risk: RiskLevel
  source_count: number
}

export interface Subdomain {
  id: number
  domain_id: number
  host: string
  a_records: string[]
  cname_record: string | null
  source: string
  status: SubdomainStatus
  gone: boolean
  // Backend vuln_type is an open set (takeover types or "cve:CVE-…"); keep it
  // a string so live findings flow through, and let vulnTypeMeta interpret it.
  vuln_type: string | null
}

export interface Vulnerability {
  id: number
  host: string
  domain: string
  vuln_type: string
  confidence_score: number
  found_at: string
  status: VulnStatus
}

export interface Alert {
  id: number
  severity: AlertSeverity
  title: string
  host: string
  created_at: string
}

export interface AuditLog {
  id: number
  actor: string
  action: string
  target: string
  source_ip: string
  created_at: string
}

export interface TrendPoint {
  day: number
  new_subdomains: number
  has_vulnerability: boolean
}
