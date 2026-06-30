import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Box, Button, Card, Grid, Avatar, Typography, Table, TableBody, TableCell,
  TableHead, TableRow, TableContainer, TableSortLabel, useTheme, Tooltip, LinearProgress, Snackbar, Alert,
} from '@mui/material'
import ArrowBackOutlined from '@mui/icons-material/ArrowBackOutlined'
import PublicOutlined from '@mui/icons-material/PublicOutlined'
import FileDownloadOutlined from '@mui/icons-material/FileDownloadOutlined'
import RefreshOutlined from '@mui/icons-material/RefreshOutlined'
import WarningAmberOutlined from '@mui/icons-material/WarningAmberOutlined'
import { FONT_MONO } from '@/styles/theme'
import { SearchField, Segmented, RiskChip, TintChip, riskMeta, subStatusMeta } from '@/components/common/Widgets'
import { fetchDomainDetail, rescanDomain, setDomainMonitorMode, type DomainDetail } from '@/data/apiAdapters'
import { exportAPI } from '@/api/export'
import { useAuth } from '@/hooks/useAuth'
import { downloadBlob } from '@/utils/download'
import { apiErrorMessage } from '@/utils/apiError'

export function DomainDetailPage() {
  const theme = useTheme()
  const navigate = useNavigate()
  const { isAdmin } = useAuth()
  const { id } = useParams()
  const domainId = Number(id)
  const [detail, setDetail] = useState<DomainDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState('')
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'live' | 'issues' | 'gone'>('all')
  const [sortBy, setSortBy] = useState<'host' | 'status'>('host')
  const [dir, setDir] = useState<'asc' | 'desc'>('asc')
  const [exporting, setExporting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setDetail(await fetchDomainDetail(domainId))
    } catch (err) {
      setToast(apiErrorMessage(err, 'Failed to load domain'))
    } finally {
      setLoading(false)
    }
  }, [domainId])

  useEffect(() => { load() }, [load])

  const domain = detail?.domain
  const subs = useMemo(() => {
    if (!detail) return []
    let list = detail.subdomains.filter((s) => s.host.toLowerCase().includes(search.toLowerCase()))
    if (filter === 'live') list = list.filter((s) => s.status === 'live' && !s.gone)
    else if (filter === 'issues') list = list.filter((s) => s.vuln_type)
    else if (filter === 'gone') list = list.filter((s) => s.gone)
    const sign = dir === 'asc' ? 1 : -1
    return [...list].sort((a, b) => {
      if (sortBy === 'status') return a.status.localeCompare(b.status) * sign
      return a.host.localeCompare(b.host) * sign
    })
  }, [detail, search, filter, sortBy, dir])

  const sort = (col: 'host' | 'status') => {
    if (sortBy === col) setDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortBy(col); setDir('asc') }
  }

  const rescan = async () => {
    try {
      await rescanDomain(domainId)
      setToast('Rescan started')
    } catch (err) {
      setToast(apiErrorMessage(err, 'Failed to start rescan'))
    }
  }

  const exportXlsx = async () => {
    setExporting(true)
    try {
      const blob = await exportAPI.domainXlsx(domainId)
      const name = detail?.domain?.domain_name ?? 'domain'
      downloadBlob(blob, `korug-${name}.xlsx`)
    } catch (err) {
      setToast(apiErrorMessage(err, 'Failed to export'))
    } finally {
      setExporting(false)
    }
  }

  const changeMode = async (mode: 'active' | 'passive') => {
    if (!detail || detail.domain.monitor_mode === mode) return
    try {
      await setDomainMonitorMode(domainId, mode)
      setToast(`Monitoring set to ${mode}`)
      await load()
    } catch (err) {
      setToast(apiErrorMessage(err, 'Failed to update monitoring mode'))
    }
  }

  if (!domain) {
    return (
      <Box>
        <Button startIcon={<ArrowBackOutlined />} onClick={() => navigate('/domains')} sx={{ color: 'text.secondary', mb: 2 }}>All domains</Button>
        {loading ? <LinearProgress sx={{ borderRadius: 1 }} /> : <Typography sx={{ color: 'text.disabled' }}>Domain not found.</Typography>}
        <Snackbar open={!!toast} autoHideDuration={3000} onClose={() => setToast('')} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
          <Alert severity="error" variant="filled" onClose={() => setToast('')}>{toast}</Alert>
        </Snackbar>
      </Box>
    )
  }

  const stats = [
    { label: 'Subdomains', value: domain.subdomain_count, color: 'text.primary' as const },
    { label: 'Open issues', value: domain.open_vulnerabilities, color: domain.open_vulnerabilities > 0 ? 'error.main' : 'text.primary' as const },
    { label: 'Sources', value: domain.source_count, color: 'text.primary' as const },
    { label: 'Risk', value: riskMeta(domain.risk).label, color: 'text.primary' as const },
  ]

  return (
    <Box>
      <Button startIcon={<ArrowBackOutlined />} onClick={() => navigate('/domains')} sx={{ color: 'text.secondary', mb: 2 }}>All domains</Button>

      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2, mb: 2.5, flexWrap: 'wrap' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.8 }}>
          <Avatar variant="rounded" sx={{ width: 46, height: 46, bgcolor: theme.palette.brand.subtle, color: theme.palette.brand.text }}><PublicOutlined sx={{ fontSize: 24 }} /></Avatar>
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2 }}>
              <Typography variant="h4" sx={{ fontSize: 22 }}>{domain.domain_name}</Typography>
              <RiskChip risk={domain.risk} />
            </Box>
            <Typography sx={{ fontSize: 13, color: 'text.disabled', mt: 0.4 }}>Last scanned {domain.last_scanned} · monitoring {domain.enabled ? 'enabled' : 'paused'}</Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, flexWrap: 'wrap' }}>
          {isAdmin && <Segmented value={domain.monitor_mode} onChange={changeMode} options={[{ value: 'active', label: 'Active' }, { value: 'passive', label: 'Passive' }]} ariaLabel="Monitoring mode" />}
          <Button variant="outlined" color="inherit" startIcon={<FileDownloadOutlined />} onClick={exportXlsx} disabled={exporting} sx={{ borderColor: 'divider', color: 'text.secondary' }}>{exporting ? 'Exporting…' : 'Export XLSX'}</Button>
          {isAdmin && <Button variant="contained" color="primary" startIcon={<RefreshOutlined />} onClick={rescan}>Rescan</Button>}
        </Box>
      </Box>

      <Grid container spacing={1.8} sx={{ mb: 2.5 }}>
        {stats.map((s) => (
          <Grid item xs={6} md={3} key={s.label}>
            <Card><Box sx={{ p: 2 }}>
              <Typography sx={{ fontSize: 12, fontWeight: 700, color: 'text.disabled', textTransform: 'uppercase', letterSpacing: '.4px', mb: 0.9 }}>{s.label}</Typography>
              <Typography sx={{ fontFamily: FONT_MONO, fontWeight: 700, fontSize: 24, color: s.color }}>{s.value}</Typography>
            </Box></Card>
          </Grid>
        ))}
      </Grid>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.8, flexWrap: 'wrap' }}>
        <Typography variant="h6" sx={{ fontSize: 16 }}>Discovered subdomains</Typography>
        <Box sx={{ flex: 1 }} />
        <SearchField value={search} onChange={setSearch} placeholder="Filter hosts…" sx={{ minWidth: 220 }} />
        <Segmented value={filter} onChange={setFilter} options={[{ value: 'all', label: 'All' }, { value: 'live', label: 'Live' }, { value: 'issues', label: 'Issues' }, { value: 'gone', label: 'Gone' }]} />
      </Box>

      <Card>
        <TableContainer>
          <Table sx={{ '& td, & th': { borderColor: 'divider' } }}>
            <TableHead>
              <TableRow sx={{ bgcolor: 'surface.subtle' }}>
                <TableCell sortDirection={sortBy === 'host' ? dir : false} sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>
                  <TableSortLabel active={sortBy === 'host'} direction={sortBy === 'host' ? dir : 'asc'} onClick={() => sort('host')}>Host</TableSortLabel>
                </TableCell>
                <TableCell sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>DNS records</TableCell>
                <TableCell sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>Source</TableCell>
                <TableCell sortDirection={sortBy === 'status' ? dir : false} sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>
                  <TableSortLabel active={sortBy === 'status'} direction={sortBy === 'status' ? dir : 'asc'} onClick={() => sort('status')}>Status</TableSortLabel>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {subs.map((s) => {
                const m = subStatusMeta(s.status)
                const recs = [s.a_records.length ? `A ${s.a_records.join(', ')}` : '', s.cname_record ? `CNAME ${s.cname_record}` : ''].filter(Boolean).join('  ·  ') || '—'
                return (
                  <TableRow key={s.id} hover sx={{ cursor: 'pointer', opacity: s.gone ? 0.55 : 1 }} onClick={() => navigate(`/subdomains/${s.id}`)}>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography sx={{ fontFamily: FONT_MONO, fontSize: 13 }}>{s.host}</Typography>
                        {s.vuln_type && <Tooltip title={m.label}><WarningAmberOutlined sx={{ fontSize: 15, color: 'error.main' }} /></Tooltip>}
                      </Box>
                    </TableCell>
                    <TableCell sx={{ fontFamily: FONT_MONO, fontSize: 12, color: 'text.secondary' }}>{recs}</TableCell>
                    <TableCell sx={{ fontSize: 12.5, color: 'text.secondary' }}>{s.source}</TableCell>
                    <TableCell><TintChip label={s.gone ? 'Gone' : m.label} color={s.gone ? 'default' : m.color} dot /></TableCell>
                  </TableRow>
                )
              })}
              {subs.length === 0 && !loading && (
                <TableRow><TableCell colSpan={4} align="center" sx={{ py: 5, color: 'text.disabled' }}>No subdomains match your filter.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      <Snackbar open={!!toast} autoHideDuration={3000} onClose={() => setToast('')} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert severity="info" variant="filled" onClose={() => setToast('')}>{toast}</Alert>
      </Snackbar>
    </Box>
  )
}
