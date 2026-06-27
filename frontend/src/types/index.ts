// Auth types
export interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

export interface User {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
  created_at: string
  last_login: string | null
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type?: string
}

// Domain types
export interface Domain {
  id: number
  domain_name: string
  enabled: boolean
  monitor_mode: 'active' | 'passive'
  last_scanned: string | null
  created_at: string
  updated_at: string
}

export interface Subdomain {
  id: number
  subdomain: string
  a_records: string[]
  aaaa_records: string[]
  cname_record: string | null
  mx_records: string[]
  ns_records: string[]
  first_discovered: string
  last_seen: string
}

// Vulnerability types
export interface Vulnerability {
  id: number
  subdomain_id: number
  domain_id: number
  vuln_type: string  // takeover types (s3_bucket_takeover, cname_orphan, …) or "cve:CVE-…"
  confidence_score: number
  details: string | null
  found_at: string
  is_false_positive: boolean
  false_positive_reason: string | null
}

// Scan types
export interface ScanHistory {
  id: number
  domain_id: number
  scan_timestamp: string
  total_subdomains: number
  new_subdomains: number
  vulnerabilities_found: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  error_message: string | null
  scan_duration_seconds: number | null
}

export interface ScanProgress {
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  message: string
}

// API response types
export interface ApiError {
  detail: string
}

export interface PaginationParams {
  skip?: number
  limit?: number
}
