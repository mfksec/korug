// Adapter layer: fetch the live FastAPI endpoints (@/api/*) and map their
// responses onto the UI-facing types the redesigned pages render
// (@/types/domain). UI-only fields the API doesn't store — per-domain
// subdomain/issue counts, a risk roll-up, relative "x ago" timestamps — are
// derived here so the pages stay presentational.

import { domainAPI, type DashboardStats } from '@/api/domains'
import { vulnerabilityAPI } from '@/api/vulnerabilities'
import { alertAPI } from '@/api/alerts'
import { scanAPI, type Asset } from '@/api/scans'
import { settingsAPI } from '@/api/settings'
import type { Vulnerability as ApiVuln, Domain as ApiDomain } from '@/types'
import type {
  Domain, Subdomain, Vulnerability, Alert, AuditLog, RiskLevel,
  AlertSeverity, SubdomainStatus, TrendPoint,
} from '@/types/domain'

// ---- helpers ------------------------------------------------------

/**
 * Compact relative time, e.g. "12 min ago", "3 h ago", "2 d ago".
 * The API emits naive UTC timestamps with no timezone marker; `new Date()`
 * would parse those as local time, skewing the result by the UTC offset, so
 * normalize to UTC by appending `Z` when no offset is present.
 */
export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return 'never'
  const hasTz = /[zZ]|[+-]\d{2}:?\d{2}$/.test(iso)
  const t = new Date(hasTz ? iso : `${iso}Z`).getTime()
  if (Number.isNaN(t)) return 'never'
  const s = Math.max(0, Math.round((Date.now() - t) / 1000))
  if (s < 60) return 'just now'
  const m = Math.round(s / 60)
  if (m < 60) return `${m} min ago`
  const h = Math.round(m / 60)
  if (h < 24) return `${h} h ago`
  const d = Math.round(h / 24)
  return `${d} d ago`
}

const isHighConfidence = (v: ApiVuln) =>
  v.confidence_score >= 90 || v.vuln_type.includes('s3') || v.vuln_type.startsWith('cve:')

/** UI risk roll-up for a domain from its open (non-FP) findings. */
function rollupRisk(openVulns: ApiVuln[], scanned: boolean): RiskLevel {
  if (openVulns.some(isHighConfidence)) return 'high'
  if (openVulns.length) return 'medium'
  return scanned ? 'low' : 'none'
}

function normalizeSeverity(sev: string): AlertSeverity {
  if (sev === 'critical' || sev === 'high') return 'high'
  if (sev === 'medium') return 'medium'
  return 'info'
}

/** Build a subdomain_id → { host, domain } index from the flat asset list. */
async function loadAssetIndex(): Promise<{ assets: Asset[]; byId: Map<number, Asset> }> {
  const { assets } = await scanAPI.listAssets({ limit: 1000 })
  const byId = new Map<number, Asset>()
  assets.forEach((a) => byId.set(a.id, a))
  return { assets, byId }
}

// ---- domains ------------------------------------------------------

export async function fetchDomains(): Promise<Domain[]> {
  const [domains, { assets }, vulns] = await Promise.all([
    domainAPI.list({ limit: 500 }),
    scanAPI.listAssets({ limit: 1000 }),
    vulnerabilityAPI.list({ limit: 1000 }),
  ])

  const subsByDomain = new Map<number, Asset[]>()
  assets.forEach((a) => {
    const list = subsByDomain.get(a.domain_id) ?? []
    list.push(a)
    subsByDomain.set(a.domain_id, list)
  })

  const openByDomain = new Map<number, ApiVuln[]>()
  vulns.filter((v) => !v.is_false_positive).forEach((v) => {
    const list = openByDomain.get(v.domain_id) ?? []
    list.push(v)
    openByDomain.set(v.domain_id, list)
  })

  return domains.map((d: ApiDomain): Domain => {
    const subs = subsByDomain.get(d.id) ?? []
    const open = openByDomain.get(d.id) ?? []
    const sources = new Set<string>()
    subs.forEach((s) => (s.sources ?? []).forEach((src) => sources.add(src)))
    return {
      id: d.id,
      domain_name: d.domain_name,
      enabled: d.enabled,
      monitor_mode: d.monitor_mode ?? 'active',
      last_scanned: timeAgo(d.last_scanned),
      subdomain_count: subs.length,
      open_vulnerabilities: open.length,
      risk: rollupRisk(open, Boolean(d.last_scanned)),
      source_count: sources.size,
    }
  })
}

export async function createDomain(name: string, mode: 'active' | 'passive' = 'active'): Promise<void> {
  await domainAPI.create(name, mode)
}

export async function setDomainMonitorMode(id: number, mode: 'active' | 'passive'): Promise<void> {
  await domainAPI.update(id, { monitor_mode: mode })
}

export async function deleteDomain(id: number): Promise<void> {
  await domainAPI.delete(id)
}

// ---- domain detail ------------------------------------------------

export interface DomainDetail {
  domain: Domain
  subdomains: Subdomain[]
}

function subStatus(isAlive: boolean, cname: string | null): SubdomainStatus {
  if (isAlive) return 'live'
  return cname ? 'orphan' : 'dns_orphan'
}

export async function fetchDomainDetail(id: number): Promise<DomainDetail> {
  const results = await scanAPI.getResults(id)
  const vulnBySub = new Map<number, string>()
  results.vulnerabilities
    .filter((v) => !v.is_false_positive)
    .forEach((v) => { if (!vulnBySub.has(v.subdomain_id)) vulnBySub.set(v.subdomain_id, v.vuln_type) })

  const subdomains: Subdomain[] = results.subdomains.map((s) => ({
    id: s.id,
    domain_id: id,
    host: s.subdomain,
    a_records: s.resolved_ips ?? [],
    cname_record: s.cname,
    source: s.sources?.[0] ?? 'dns',
    status: subStatus(s.is_alive, s.cname),
    gone: Boolean(s.is_gone),
    vuln_type: vulnBySub.get(s.id) ?? null,
  }))

  const sources = new Set<string>()
  results.subdomains.forEach((s) => (s.sources ?? []).forEach((src) => sources.add(src)))
  const open = results.vulnerabilities.filter((v) => !v.is_false_positive)

  const domain: Domain = {
    id: results.domain.id,
    domain_name: results.domain.domain_name,
    enabled: results.domain.enabled,
    monitor_mode: results.domain.monitor_mode ?? 'active',
    last_scanned: timeAgo(results.domain.last_scanned),
    subdomain_count: results.counts.subdomains,
    open_vulnerabilities: open.length,
    risk: rollupRisk(
      open.map((v) => ({ confidence_score: v.confidence_score, vuln_type: v.vuln_type } as ApiVuln)),
      Boolean(results.domain.last_scanned),
    ),
    source_count: sources.size,
  }

  return { domain, subdomains }
}

export async function rescanDomain(id: number): Promise<void> {
  await scanAPI.triggerScan(id)
}

// ---- vulnerabilities ----------------------------------------------

export async function fetchVulnerabilities(): Promise<Vulnerability[]> {
  const [vulns, { byId }] = await Promise.all([
    vulnerabilityAPI.list({ limit: 1000 }),
    loadAssetIndex(),
  ])
  return vulns.map((v): Vulnerability => {
    const asset = byId.get(v.subdomain_id)
    return {
      id: v.id,
      host: asset?.subdomain ?? `subdomain #${v.subdomain_id}`,
      domain: asset?.domain_name ?? '',
      vuln_type: v.vuln_type,
      confidence_score: v.confidence_score,
      found_at: timeAgo(v.found_at),
      status: v.is_false_positive ? 'false_positive' : 'open',
    }
  })
}

export async function setVulnerabilityFalsePositive(id: number, fp: boolean): Promise<void> {
  if (fp) await vulnerabilityAPI.markFalsePositive(id, 'Flagged from dashboard')
  else await vulnerabilityAPI.unmarkFalsePositive(id)
}

// ---- alerts -------------------------------------------------------

export async function fetchAlerts(): Promise<Alert[]> {
  const alerts = await alertAPI.list('all', 200)
  return alerts.map((a): Alert => ({
    id: a.id,
    severity: normalizeSeverity(a.severity),
    title: a.message || a.alert_type.replace(/_/g, ' '),
    host: a.domain,
    created_at: timeAgo(a.created_at),
  }))
}

// ---- audit logs ---------------------------------------------------

export async function fetchAuditLogs(): Promise<AuditLog[]> {
  const logs = await settingsAPI.listAuditLogs(100)
  return logs.map((l): AuditLog => ({
    id: l.id,
    actor: l.user || `user #${l.user_id}`,
    action: l.action,
    target: l.resource || l.details || '—',
    source_ip: l.ip_address || '—',
    created_at: timeAgo(l.timestamp),
  }))
}

// ---- dashboard ----------------------------------------------------

export interface DashboardData {
  stats: DashboardStats
  totalSubdomains: number
  domains: Domain[]
  vulnerabilities: Vulnerability[]
  alerts: Alert[]
  trend: TrendPoint[]
}

export async function fetchDashboard(): Promise<DashboardData> {
  const [stats, timeline, domains, vulnerabilities, alerts, assetList] = await Promise.all([
    domainAPI.getDashboardStats(),
    vulnerabilityAPI.getTimeline(14),
    fetchDomains(),
    fetchVulnerabilities(),
    fetchAlerts(),
    scanAPI.listAssets({ limit: 1 }),
  ])

  const trend: TrendPoint[] = timeline.slice(-14).map((p, i) => ({
    day: i + 1,
    new_subdomains: p.count,
    has_vulnerability: p.count > 0,
  }))

  return {
    stats,
    totalSubdomains: assetList.total,
    domains,
    vulnerabilities,
    alerts,
    trend,
  }
}
