import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Box, Button, Card, Grid, Avatar, Typography, Table, TableBody, TableCell,
  TableHead, TableRow, TableContainer, useTheme, Tooltip,
} from '@mui/material'
import ArrowBackOutlined from '@mui/icons-material/ArrowBackOutlined'
import PublicOutlined from '@mui/icons-material/PublicOutlined'
import FileDownloadOutlined from '@mui/icons-material/FileDownloadOutlined'
import RefreshOutlined from '@mui/icons-material/RefreshOutlined'
import WarningAmberOutlined from '@mui/icons-material/WarningAmberOutlined'
import { FONT_MONO } from '@/styles/theme'
import { SearchField, Segmented, RiskChip, TintChip, riskMeta, subStatusMeta } from '@/components/common/Widgets'
import { mockDomains, mockSubdomains } from '@/data/mock'

export function DomainDetailPage() {
  const theme = useTheme()
  const navigate = useNavigate()
  const { id } = useParams()
  const domain = mockDomains.find((d) => d.id === Number(id)) || mockDomains[0]
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'live' | 'issues'>('all')

  const subs = useMemo(() => {
    let list = mockSubdomains(domain).filter((s) => s.host.toLowerCase().includes(search.toLowerCase()))
    if (filter === 'live') list = list.filter((s) => s.status === 'live')
    else if (filter === 'issues') list = list.filter((s) => s.vuln_type)
    return list
  }, [domain, search, filter])

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
        <Box sx={{ display: 'flex', gap: 1.2 }}>
          <Button variant="outlined" color="inherit" startIcon={<FileDownloadOutlined />} sx={{ borderColor: 'divider', color: 'text.secondary' }}>Export XLSX</Button>
          <Button variant="contained" color="primary" startIcon={<RefreshOutlined />}>Rescan</Button>
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
        <Segmented value={filter} onChange={setFilter} options={[{ value: 'all', label: 'All' }, { value: 'live', label: 'Live' }, { value: 'issues', label: 'Issues' }]} />
      </Box>

      <Card>
        <TableContainer>
          <Table sx={{ '& td, & th': { borderColor: 'divider' } }}>
            <TableHead>
              <TableRow sx={{ bgcolor: 'surface.subtle' }}>
                {['Host', 'DNS records', 'Source', 'Status'].map((h) => (
                  <TableCell key={h} sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>{h}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {subs.map((s) => {
                const m = subStatusMeta(s.status)
                const recs = [s.a_records.length ? `A ${s.a_records.join(', ')}` : '', s.cname_record ? `CNAME ${s.cname_record}` : ''].filter(Boolean).join('  ·  ') || '—'
                return (
                  <TableRow key={s.id} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography sx={{ fontFamily: FONT_MONO, fontSize: 13 }}>{s.host}</Typography>
                        {s.vuln_type && <Tooltip title={m.label}><WarningAmberOutlined sx={{ fontSize: 15, color: 'error.main' }} /></Tooltip>}
                      </Box>
                    </TableCell>
                    <TableCell sx={{ fontFamily: FONT_MONO, fontSize: 12, color: 'text.secondary' }}>{recs}</TableCell>
                    <TableCell sx={{ fontSize: 12.5, color: 'text.secondary' }}>{s.source}</TableCell>
                    <TableCell><TintChip label={m.label} color={m.color} dot /></TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>
    </Box>
  )
}
