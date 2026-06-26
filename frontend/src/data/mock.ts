import { Domain, Subdomain, Vulnerability, Alert, AuditLog, TrendPoint } from '@/types/domain'

/**
 * Mock data so the redesigned UI renders without the backend.
 * Replace each export with a call to the corresponding `@/api/*` module
 * (e.g. `domainsApi.list()`) when wiring to the live FastAPI service.
 */

export const mockDomains: Domain[] = [
  { id: 1, domain_name: 'acme-corp.com', enabled: true, subdomain_count: 148, open_vulnerabilities: 3, risk: 'high', source_count: 4, last_scanned: '12 min ago' },
  { id: 2, domain_name: 'acme-internal.net', enabled: true, subdomain_count: 62, open_vulnerabilities: 1, risk: 'medium', source_count: 3, last_scanned: '1 h ago' },
  { id: 3, domain_name: 'acmelabs.io', enabled: true, subdomain_count: 97, open_vulnerabilities: 0, risk: 'low', source_count: 4, last_scanned: '3 h ago' },
  { id: 4, domain_name: 'getacme.app', enabled: true, subdomain_count: 34, open_vulnerabilities: 2, risk: 'high', source_count: 2, last_scanned: '5 h ago' },
  { id: 5, domain_name: 'acme-cdn.com', enabled: false, subdomain_count: 21, open_vulnerabilities: 0, risk: 'none', source_count: 2, last_scanned: '2 d ago' },
  { id: 6, domain_name: 'acmepay.io', enabled: true, subdomain_count: 55, open_vulnerabilities: 1, risk: 'medium', source_count: 3, last_scanned: '8 h ago' },
  { id: 7, domain_name: 'staging-acme.dev', enabled: true, subdomain_count: 18, open_vulnerabilities: 0, risk: 'low', source_count: 1, last_scanned: '1 d ago' },
  { id: 8, domain_name: 'acme-mail.net', enabled: false, subdomain_count: 9, open_vulnerabilities: 0, risk: 'none', source_count: 1, last_scanned: '4 d ago' },
]

const subTemplates: Omit<Subdomain, 'id' | 'domain_id' | 'host'>[] = [
  { a_records: ['52.18.44.21'], cname_record: null, source: 'subfinder', status: 'live', vuln_type: null },
  { a_records: ['52.18.44.30'], cname_record: null, source: 'amass', status: 'live', vuln_type: null },
  { a_records: [], cname_record: 'acme-assets.s3.amazonaws.com', source: 'subfinder', status: 'orphan', vuln_type: 's3_bucket_takeover' },
  { a_records: [], cname_record: 'acme.ghost.io', source: 'urlscan', status: 'orphan', vuln_type: 'cname_orphan' },
  { a_records: ['52.18.44.9'], cname_record: null, source: 'dns', status: 'live', vuln_type: null },
  { a_records: ['10.0.3.12'], cname_record: null, source: 'amass', status: 'live', vuln_type: null },
  { a_records: [], cname_record: 'staging-acme.herokudns.com', source: 'subfinder', status: 'orphan', vuln_type: 'cname_orphan' },
  { a_records: ['52.18.44.77'], cname_record: null, source: 'shodan', status: 'live', vuln_type: null },
  { a_records: ['151.101.1.10'], cname_record: 'acme.fastly.net', source: 'dns', status: 'live', vuln_type: null },
  { a_records: ['52.18.44.40'], cname_record: null, source: 'amass', status: 'live', vuln_type: null },
  { a_records: ['52.18.44.55'], cname_record: null, source: 'subfinder', status: 'live', vuln_type: null },
  { a_records: [], cname_record: null, source: 'urlscan', status: 'dns_orphan', vuln_type: 'dns_orphan' },
  { a_records: ['52.18.44.61'], cname_record: null, source: 'subfinder', status: 'live', vuln_type: null },
  { a_records: ['52.18.44.12'], cname_record: null, source: 'shodan', status: 'live', vuln_type: null },
]
const leaves = ['www', 'api', 'assets', 'blog', 'mail', 'dev', 'staging', 'vpn', 'cdn', 'git', 'shop', 'legacy', 'docs', 'admin']

export function mockSubdomains(domain: Domain): Subdomain[] {
  return subTemplates.map((t, i) => ({
    ...t, id: domain.id * 100 + i, domain_id: domain.id, host: `${leaves[i]}.${domain.domain_name}`,
  }))
}

export const mockVulnerabilities: Vulnerability[] = [
  { id: 1, host: 'assets.acme-corp.com', domain: 'acme-corp.com', vuln_type: 's3_bucket_takeover', confidence_score: 95, found_at: '12 min ago', status: 'open' },
  { id: 2, host: 'blog.acme-corp.com', domain: 'acme-corp.com', vuln_type: 'cname_orphan', confidence_score: 85, found_at: '14 min ago', status: 'open' },
  { id: 3, host: 'legacy.acme-corp.com', domain: 'acme-corp.com', vuln_type: 'dns_orphan', confidence_score: 82, found_at: '1 h ago', status: 'open' },
  { id: 4, host: 'old.getacme.app', domain: 'getacme.app', vuln_type: 's3_bucket_takeover', confidence_score: 96, found_at: '5 h ago', status: 'open' },
  { id: 5, host: 'cdn-test.getacme.app', domain: 'getacme.app', vuln_type: 'cname_orphan', confidence_score: 84, found_at: '5 h ago', status: 'open' },
  { id: 6, host: 'static.acme-internal.net', domain: 'acme-internal.net', vuln_type: 'cname_orphan', confidence_score: 85, found_at: '1 h ago', status: 'open' },
  { id: 7, host: 'pay-staging.acmepay.io', domain: 'acmepay.io', vuln_type: 'dns_orphan', confidence_score: 80, found_at: '8 h ago', status: 'open' },
  { id: 8, host: 'mirror.acmelabs.io', domain: 'acmelabs.io', vuln_type: 's3_bucket_takeover', confidence_score: 94, found_at: '2 d ago', status: 'open' },
  { id: 9, host: 'beta.acmelabs.io', domain: 'acmelabs.io', vuln_type: 'cname_orphan', confidence_score: 83, found_at: '2 d ago', status: 'false_positive' },
  { id: 10, host: 'tmp.acme-corp.com', domain: 'acme-corp.com', vuln_type: 'dns_orphan', confidence_score: 81, found_at: '3 d ago', status: 'false_positive' },
]

export const mockAlerts: Alert[] = [
  { id: 1, severity: 'high', title: 'S3 bucket takeover detected', host: 'assets.acme-corp.com', created_at: '12 min ago' },
  { id: 2, severity: 'high', title: 'CNAME orphan detected', host: 'blog.acme-corp.com', created_at: '14 min ago' },
  { id: 3, severity: 'medium', title: 'DNS orphan detected', host: 'legacy.acme-corp.com', created_at: '1 h ago' },
  { id: 4, severity: 'info', title: 'Scan completed', host: 'acmelabs.io', created_at: '3 h ago' },
  { id: 5, severity: 'high', title: 'S3 bucket takeover detected', host: 'old.getacme.app', created_at: '5 h ago' },
  { id: 6, severity: 'info', title: '14 new subdomains discovered', host: 'acme-corp.com', created_at: '12 min ago' },
]

export const mockAuditLogs: AuditLog[] = [
  { id: 1, actor: 'admin', action: 'auth.login', target: 'session #4821', source_ip: '10.0.0.4', created_at: '12 min ago' },
  { id: 2, actor: 'scanner', action: 'scan.started', target: 'acme-corp.com', source_ip: '127.0.0.1', created_at: '12 min ago' },
  { id: 3, actor: 'admin', action: 'domain.add', target: 'getacme.app', source_ip: '10.0.0.4', created_at: '2 h ago' },
  { id: 4, actor: 'j.rivera', action: 'vuln.flag_fp', target: 'beta.acmelabs.io', source_ip: '10.0.0.9', created_at: '2 d ago' },
  { id: 5, actor: 'admin', action: 'settings.update', target: 'slack_webhook', source_ip: '10.0.0.4', created_at: '1 d ago' },
  { id: 6, actor: 'j.rivera', action: 'report.export', target: 'acme-corp.com', source_ip: '10.0.0.9', created_at: '1 d ago' },
  { id: 7, actor: 'scanner', action: 'scan.completed', target: 'acmelabs.io', source_ip: '127.0.0.1', created_at: '3 h ago' },
  { id: 8, actor: 'admin', action: 'domain.delete', target: 'acme-mail.net', source_ip: '10.0.0.4', created_at: '4 d ago' },
]

export const mockTrend: TrendPoint[] = [8, 5, 12, 6, 9, 4, 7, 15, 3, 11, 6, 9, 5, 14].map((n, i) => ({
  day: i + 1, new_subdomains: n, has_vulnerability: [3, 7, 13].includes(i),
}))
