import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Box, Button, Card, Grid, Avatar, Typography, Table, TableBody, TableCell,
  TableHead, TableRow, TableContainer, TableSortLabel, useTheme, Chip, Link,
  LinearProgress, Snackbar, Alert, Tooltip,
} from '@mui/material'
import ArrowBackOutlined from '@mui/icons-material/ArrowBackOutlined'
import DnsOutlined from '@mui/icons-material/DnsOutlined'
import RefreshOutlined from '@mui/icons-material/RefreshOutlined'
import VerifiedUserOutlined from '@mui/icons-material/VerifiedUserOutlined'
import OpenInNewOutlined from '@mui/icons-material/OpenInNewOutlined'
import { FONT_MONO } from '@/styles/theme'
import { ConfidenceBar, TintChip, vulnTypeMeta, changeTypeMeta } from '@/components/common/Widgets'
import { scanAPI, type SubdomainDetail, type Certificate } from '@/api/scans'
import { vulnerabilityAPI } from '@/api/vulnerabilities'
import { timeAgo } from '@/data/apiAdapters'
import { apiErrorMessage } from '@/utils/apiError'

function vulnMessage(details: string | null): string {
  if (!details) return ''
  try {
    const parsed = JSON.parse(details)
    if (parsed && typeof parsed === 'object' && parsed.message) return parsed.message
  } catch { /* not JSON */ }
  return details
}

function assetStatus(a: SubdomainDetail['asset']): { label: string; color: 'success' | 'warning' | 'error' | 'default' } {
  if (a.is_gone) return { label: 'Gone', color: 'default' }
  if (a.is_alive) return { label: 'Live', color: 'success' }
  if (a.resolves) return { label: 'Resolving', color: 'warning' }
  return { label: 'No DNS', color: 'error' }
}

export function SubdomainDetailPage() {
  const theme = useTheme()
  const navigate = useNavigate()
  const { id } = useParams()
  const subId = Number(id)
  const [detail, setDetail] = useState<SubdomainDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState('')
  const [certSort, setCertSort] = useState<'not_after' | 'issuer' | 'not_before'>('not_after')
  const [certDir, setCertDir] = useState<'asc' | 'desc'>('desc')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setDetail(await scanAPI.getSubdomainDetail(subId))
    } catch (err) {
      setToast(apiErrorMessage(err, 'Failed to load subdomain'))
    } finally {
      setLoading(false)
    }
  }, [subId])

  useEffect(() => { load() }, [load])

  const rescan = async () => {
    setBusy(true)
    try {
      const { new_vulnerabilities } = await scanAPI.scanSubdomain(subId)
      setToast(`Rescan complete — ${new_vulnerabilities} new finding(s)`)
      await load()
    } catch (err) {
      setToast(apiErrorMessage(err, 'Rescan failed'))
    } finally {
      setBusy(false)
    }
  }

  const refreshCerts = async () => {
    setBusy(true)
    try {
      const { new_certificates } = await scanAPI.refreshCertificates(subId)
      setToast(`Certificates refreshed — ${new_certificates} new`)
      await load()
    } catch (err) {
      setToast(apiErrorMessage(err, 'Certificate refresh failed'))
    } finally {
      setBusy(false)
    }
  }

  const toggleFp = async (vulnId: number, isFp: boolean) => {
    try {
      if (isFp) await vulnerabilityAPI.unmarkFalsePositive(vulnId)
      else await vulnerabilityAPI.markFalsePositive(vulnId, 'Flagged from subdomain detail')
      await load()
    } catch (err) {
      setToast(apiErrorMessage(err, 'Failed to update finding'))
    }
  }

  const certs = useMemo(() => {
    if (!detail) return []
    const sign = certDir === 'asc' ? 1 : -1
    return [...detail.certificates].sort((a, b) => {
      if (certSort === 'issuer') return String(a.issuer ?? '').localeCompare(String(b.issuer ?? '')) * sign
      const key = certSort
      return String(a[key] ?? '').localeCompare(String(b[key] ?? '')) * sign
    })
  }, [detail, certSort, certDir])

  const sortCert = (col: typeof certSort) => {
    if (certSort === col) setCertDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setCertSort(col); setCertDir('desc') }
  }

  if (!detail) {
    return (
      <Box>
        <Button startIcon={<ArrowBackOutlined />} onClick={() => navigate(-1)} sx={{ color: 'text.secondary', mb: 2 }}>Back</Button>
        {loading ? <LinearProgress sx={{ borderRadius: 1 }} /> : <Typography sx={{ color: 'text.disabled' }}>Subdomain not found.</Typography>}
        <Snackbar open={!!toast} autoHideDuration={3000} onClose={() => setToast('')} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
          <Alert severity="error" variant="filled" onClose={() => setToast('')}>{toast}</Alert>
        </Snackbar>
      </Box>
    )
  }

  const a = detail.asset
  const st = assetStatus(a)
  const dns = a.dns_records
  const openVulns = detail.vulnerabilities.filter((v) => !v.is_false_positive)
  const stats = [
    { label: 'Status', value: st.label },
    { label: 'Resolved IPs', value: (a.resolved_ips ?? []).length },
    { label: 'Open issues', value: openVulns.length },
    { label: 'Certificates', value: detail.certificates.length },
  ]

  const sectionTitle = (text: string) => (
    <Typography variant="h6" sx={{ fontSize: 15, mb: 1.4, mt: 3 }}>{text}</Typography>
  )

  return (
    <Box>
      <Button startIcon={<ArrowBackOutlined />} onClick={() => a.domain_id ? navigate(`/domains/${a.domain_id}`) : navigate('/assets')} sx={{ color: 'text.secondary', mb: 2 }}>
        {a.domain_name ? a.domain_name : 'Back'}
      </Button>

      {(loading || busy) && <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />}

      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2, mb: 2.5, flexWrap: 'wrap' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.8 }}>
          <Avatar variant="rounded" sx={{ width: 46, height: 46, bgcolor: theme.palette.brand.subtle, color: theme.palette.brand.text }}><DnsOutlined sx={{ fontSize: 24 }} /></Avatar>
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, flexWrap: 'wrap' }}>
              <Typography variant="h4" sx={{ fontFamily: FONT_MONO, fontSize: 20 }}>{a.subdomain}</Typography>
              <TintChip label={st.label} color={st.color} dot />
              {a.is_cloudflare && <Chip size="small" label="Cloudflare" sx={{ fontWeight: 700, fontSize: 11 }} />}
            </Box>
            <Typography sx={{ fontSize: 13, color: 'text.disabled', mt: 0.4 }}>
              Last seen {timeAgo(a.last_seen)}{a.final_url ? ' · ' : ''}
              {a.final_url && <Link href={a.final_url} target="_blank" rel="noopener" sx={{ color: 'text.secondary' }}>{a.final_url} <OpenInNewOutlined sx={{ fontSize: 12, verticalAlign: 'middle' }} /></Link>}
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1.2 }}>
          <Button variant="outlined" color="inherit" disabled={busy} startIcon={<VerifiedUserOutlined />} onClick={refreshCerts} sx={{ borderColor: 'divider', color: 'text.secondary' }}>Refresh certs</Button>
          <Button variant="contained" color="primary" disabled={busy} startIcon={<RefreshOutlined />} onClick={rescan}>Rescan host</Button>
        </Box>
      </Box>

      <Grid container spacing={1.8} sx={{ mb: 1 }}>
        {stats.map((s) => (
          <Grid item xs={6} md={3} key={s.label}>
            <Card><Box sx={{ p: 2 }}>
              <Typography sx={{ fontSize: 12, fontWeight: 700, color: 'text.disabled', textTransform: 'uppercase', letterSpacing: '.4px', mb: 0.9 }}>{s.label}</Typography>
              <Typography sx={{ fontFamily: FONT_MONO, fontWeight: 700, fontSize: 22 }}>{s.value}</Typography>
            </Box></Card>
          </Grid>
        ))}
      </Grid>

      {/* DNS + fingerprint */}
      {sectionTitle('DNS & fingerprint')}
      <Card><Box sx={{ p: 2.2, display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
        <Box>
          {([['A', dns.A], ['AAAA', dns.AAAA], ['MX', dns.MX], ['NS', dns.NS]] as [string, string[]][]).map(([k, v]) => (
            <Box key={k} sx={{ display: 'flex', gap: 1, mb: 0.6 }}>
              <Typography sx={{ fontSize: 12, fontWeight: 700, color: 'text.disabled', minWidth: 48 }}>{k}</Typography>
              <Typography sx={{ fontFamily: FONT_MONO, fontSize: 12.5, color: 'text.secondary' }}>{v?.length ? v.join(', ') : '—'}</Typography>
            </Box>
          ))}
          <Box sx={{ display: 'flex', gap: 1, mb: 0.6 }}>
            <Typography sx={{ fontSize: 12, fontWeight: 700, color: 'text.disabled', minWidth: 48 }}>CNAME</Typography>
            <Typography sx={{ fontFamily: FONT_MONO, fontSize: 12.5, color: 'text.secondary' }}>{dns.CNAME || '—'}</Typography>
          </Box>
        </Box>
        <Box>
          <Box sx={{ display: 'flex', gap: 1, mb: 0.6 }}>
            <Typography sx={{ fontSize: 12, fontWeight: 700, color: 'text.disabled', minWidth: 86 }}>HTTP status</Typography>
            <Typography sx={{ fontFamily: FONT_MONO, fontSize: 12.5, color: 'text.secondary' }}>{a.status_code ?? '—'}</Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1, mb: 0.6 }}>
            <Typography sx={{ fontSize: 12, fontWeight: 700, color: 'text.disabled', minWidth: 86 }}>Server</Typography>
            <Typography sx={{ fontFamily: FONT_MONO, fontSize: 12.5, color: 'text.secondary' }}>{a.web_server || '—'}</Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1, mb: 0.6, flexWrap: 'wrap' }}>
            <Typography sx={{ fontSize: 12, fontWeight: 700, color: 'text.disabled', minWidth: 86 }}>Tech</Typography>
            {(a.technologies ?? []).length ? a.technologies.map((t) => <Chip key={t} size="small" label={t} sx={{ fontSize: 11, height: 22 }} />) : <Typography sx={{ fontSize: 12.5, color: 'text.secondary' }}>—</Typography>}
          </Box>
          <Box sx={{ display: 'flex', gap: 1, mb: 0.6, flexWrap: 'wrap' }}>
            <Typography sx={{ fontSize: 12, fontWeight: 700, color: 'text.disabled', minWidth: 86 }}>Open ports</Typography>
            {(a.open_ports ?? []).length ? a.open_ports.map((p) => <Chip key={p.port} size="small" label={p.service ? `${p.port}/${p.service}` : p.port} sx={{ fontFamily: FONT_MONO, fontSize: 11, height: 22 }} />) : <Typography sx={{ fontSize: 12.5, color: 'text.secondary' }}>—</Typography>}
          </Box>
        </Box>
      </Box></Card>

      {/* Vulnerabilities */}
      {sectionTitle('Vulnerabilities')}
      <Card>
        <TableContainer>
          <Table sx={{ '& td, & th': { borderColor: 'divider' } }}>
            <TableHead>
              <TableRow sx={{ bgcolor: 'surface.subtle' }}>
                {['Type', 'Detail', 'Confidence', 'Found', 'Action'].map((h, i) => (
                  <TableCell key={h} align={i === 4 ? 'right' : 'left'} sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>{h}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {detail.vulnerabilities.map((v) => {
                const m = vulnTypeMeta(v.vuln_type)
                const open = !v.is_false_positive
                return (
                  <TableRow key={v.id} hover sx={{ opacity: open ? 1 : 0.55 }}>
                    <TableCell><Typography sx={{ fontSize: 13, fontWeight: 700, color: theme.palette[m.color].main }}>{m.label}</Typography></TableCell>
                    <TableCell sx={{ fontSize: 12.5, color: 'text.secondary', maxWidth: 420 }}>{vulnMessage(v.details)}</TableCell>
                    <TableCell><ConfidenceBar value={Math.round(v.confidence_score)} /></TableCell>
                    <TableCell sx={{ fontSize: 12.5, color: 'text.disabled' }}>{timeAgo(v.found_at)}</TableCell>
                    <TableCell align="right">
                      <Button size="small" variant="outlined" color="inherit" onClick={() => toggleFp(v.id, v.is_false_positive)} sx={{ borderColor: 'divider', color: open ? 'text.secondary' : 'secondary.main', whiteSpace: 'nowrap' }}>
                        {open ? 'Flag FP' : 'Restore'}
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
              {detail.vulnerabilities.length === 0 && (
                <TableRow><TableCell colSpan={5} align="center" sx={{ py: 4, color: 'text.disabled' }}>No vulnerabilities found for this host.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* Certificates */}
      {sectionTitle('Certificates (crt.sh)')}
      <Card>
        <TableContainer>
          <Table sx={{ '& td, & th': { borderColor: 'divider' } }}>
            <TableHead>
              <TableRow sx={{ bgcolor: 'surface.subtle' }}>
                <CertHead col="issuer" label="Issuer" sortBy={certSort} dir={certDir} onSort={sortCert} />
                <TableCell sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>Common name</TableCell>
                <CertHead col="not_before" label="Issued" sortBy={certSort} dir={certDir} onSort={sortCert} />
                <CertHead col="not_after" label="Expires" sortBy={certSort} dir={certDir} onSort={sortCert} />
                <TableCell sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>SANs</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {certs.map((c) => <CertRow key={c.id} c={c} />)}
              {certs.length === 0 && (
                <TableRow><TableCell colSpan={5} align="center" sx={{ py: 4, color: 'text.disabled' }}>No certificates recorded. Use “Refresh certs”.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* Change timeline */}
      {sectionTitle('Change history')}
      <Card><Box sx={{ p: detail.changes.length ? 1 : 2.2 }}>
        {detail.changes.length === 0 && <Typography sx={{ color: 'text.disabled', fontSize: 13 }}>No changes recorded yet.</Typography>}
        {detail.changes.map((ch) => {
          const m = changeTypeMeta(ch.change_type)
          const detailText = [ch.old_value, ch.new_value].filter(Boolean).join('  →  ')
          return (
            <Box key={ch.id} sx={{ display: 'flex', alignItems: 'center', gap: 1.6, px: 1.4, py: 1.3, borderBottom: 1, borderColor: 'divider', '&:last-child': { borderBottom: 0 } }}>
              <TintChip label={m.label} color={m.color} />
              <Typography sx={{ flex: 1, fontFamily: FONT_MONO, fontSize: 12.5, color: 'text.secondary' }}>{detailText || '—'}</Typography>
              <Typography sx={{ fontSize: 12.5, color: 'text.disabled', whiteSpace: 'nowrap' }}>{timeAgo(ch.detected_at)}</Typography>
            </Box>
          )
        })}
      </Box></Card>

      <Snackbar open={!!toast} autoHideDuration={3200} onClose={() => setToast('')} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert severity="info" variant="filled" onClose={() => setToast('')}>{toast}</Alert>
      </Snackbar>
    </Box>
  )
}

function CertHead({ col, label, sortBy, dir, onSort }: { col: 'not_after' | 'issuer' | 'not_before'; label: string; sortBy: string; dir: 'asc' | 'desc'; onSort: (c: 'not_after' | 'issuer' | 'not_before') => void }) {
  return (
    <TableCell sortDirection={sortBy === col ? dir : false} sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>
      <TableSortLabel active={sortBy === col} direction={sortBy === col ? dir : 'asc'} onClick={() => onSort(col)}>{label}</TableSortLabel>
    </TableCell>
  )
}

function CertRow({ c }: { c: Certificate }) {
  const expired = c.not_after ? new Date(c.not_after).getTime() < Date.now() : false
  const fmt = (iso: string | null) => (iso ? new Date(iso).toISOString().slice(0, 10) : '—')
  const sans = c.sans ?? []
  return (
    <TableRow hover>
      <TableCell sx={{ fontSize: 12.5, color: 'text.secondary', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.issuer || '—'}</TableCell>
      <TableCell sx={{ fontFamily: FONT_MONO, fontSize: 12.5 }}>{c.common_name || '—'}</TableCell>
      <TableCell sx={{ fontFamily: FONT_MONO, fontSize: 12.5, color: 'text.disabled' }}>{fmt(c.not_before)}</TableCell>
      <TableCell sx={{ fontFamily: FONT_MONO, fontSize: 12.5, color: expired ? 'error.main' : 'text.disabled' }}>{fmt(c.not_after)}</TableCell>
      <TableCell>
        <Tooltip title={sans.join(', ')}>
          <Typography sx={{ fontFamily: FONT_MONO, fontSize: 12, color: 'text.secondary' }}>{sans.length ? `${sans.length} name${sans.length > 1 ? 's' : ''}` : '—'}</Typography>
        </Tooltip>
      </TableCell>
    </TableRow>
  )
}
