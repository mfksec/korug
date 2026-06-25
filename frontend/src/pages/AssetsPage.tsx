import React, { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Box, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  TextField, Chip, Stack, Typography, ToggleButtonGroup, ToggleButton, Link,
  Tooltip, CircularProgress, InputAdornment, Button, IconButton, Snackbar, Alert,
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import RefreshIcon from '@mui/icons-material/Refresh'
import CloudIcon from '@mui/icons-material/Cloud'
import RadarIcon from '@mui/icons-material/Radar'
import { scanAPI, type Asset } from '@/api/scans'
import { apiErrorMessage } from '@/utils/apiError'
import { formatDate } from '@/utils/formatters'

/** Only treat http(s) URLs as safe link targets (blocks javascript:/data: schemes). */
const safeHref = (url: string | null): string | null => {
  if (!url) return null
  try {
    const p = new URL(url)
    return p.protocol === 'http:' || p.protocol === 'https:' ? url : null
  } catch {
    return null
  }
}

type LiveFilter = 'all' | 'alive' | 'resolved'

/** Compact, scannable rendering of the non-address DNS records. */
const DnsCell: React.FC<{ a: Asset }> = ({ a }) => {
  const d = a.dns_records
  const rows: string[] = []
  if (d.CNAME) rows.push(`CNAME → ${d.CNAME}`)
  if (d.MX?.length) rows.push(`MX: ${d.MX.join(', ')}`)
  if (d.NS?.length) rows.push(`NS: ${d.NS.join(', ')}`)
  if (d.AAAA?.length) rows.push(`AAAA: ${d.AAAA.length}`)
  if (!rows.length) return <Typography variant="caption" color="text.secondary">—</Typography>
  return (
    <Stack spacing={0.25}>
      {rows.map((r) => (
        <Typography key={r} variant="caption" sx={{ fontFamily: 'monospace', fontSize: 11 }} noWrap title={r}>{r}</Typography>
      ))}
    </Stack>
  )
}

export const AssetsPage: React.FC = () => {
  const [assets, setAssets] = useState<Asset[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchParams] = useSearchParams()
  const [q, setQ] = useState(searchParams.get('q') ?? '')
  const [filter, setFilter] = useState<LiveFilter>('all')
  const [scanning, setScanning] = useState<Set<number>>(new Set())
  const [toast, setToast] = useState<{ msg: string; sev: 'success' | 'error' } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await scanAPI.listAssets({
        q: q.trim() || undefined,
        alive: filter === 'alive' ? true : undefined,
        resolved: filter === 'resolved' ? true : undefined,
        limit: 1000,
      })
      setAssets(res.assets)
      setTotal(res.total)
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to load assets'))
    } finally {
      setLoading(false)
    }
  }, [q, filter])

  // Sync the search box when arriving via the header search (?q=…).
  useEffect(() => {
    const term = searchParams.get('q') ?? ''
    setQ((prev) => (prev === term ? prev : term))
  }, [searchParams])

  useEffect(() => {
    const t = window.setTimeout(load, 300)
    return () => window.clearTimeout(t)
  }, [load])

  const scanOne = async (asset: Asset) => {
    setScanning((p) => new Set(p).add(asset.id))
    try {
      const { asset: updated, new_vulnerabilities } = await scanAPI.scanSubdomain(asset.id)
      setAssets((prev) => prev.map((a) => (a.id === asset.id ? { ...a, ...updated } : a)))
      setToast({
        msg: new_vulnerabilities > 0
          ? `${asset.subdomain}: ${new_vulnerabilities} new finding(s)`
          : `${asset.subdomain} rescanned`,
        sev: 'success',
      })
    } catch (err) {
      setToast({ msg: apiErrorMessage(err, 'Scan failed'), sev: 'error' })
    } finally {
      setScanning((p) => { const n = new Set(p); n.delete(asset.id); return n })
    }
  }

  return (
    <Box>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}
             justifyContent="space-between" alignItems={{ sm: 'center' }}>
        <Box>
          <Typography variant="h6">Detected Assets</Typography>
          <Typography variant="body2" color="text.secondary">
            Every subdomain discovered across all monitored domains.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <TextField
            size="small" placeholder="Search subdomains…" value={q}
            onChange={(e) => setQ(e.target.value)}
            InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> }}
          />
          <ToggleButtonGroup size="small" exclusive value={filter}
                             onChange={(_, v) => v && setFilter(v)}>
            <ToggleButton value="all">All</ToggleButton>
            <ToggleButton value="resolved">Resolves</ToggleButton>
            <ToggleButton value="alive">Alive</ToggleButton>
          </ToggleButtonGroup>
          <Tooltip title="Refresh">
            <Button size="small" startIcon={<RefreshIcon />} onClick={load} disabled={loading}>Refresh</Button>
          </Tooltip>
        </Stack>
      </Stack>

      <Paper>
        {error && <Box sx={{ p: 2 }}><Typography color="error">{error}</Typography></Box>}
        {loading && assets.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}><CircularProgress /></Box>
        ) : assets.length === 0 ? (
          <Box sx={{ py: 6, textAlign: 'center' }}>
            <Typography color="text.secondary">
              No assets yet. Add a domain on the Dashboard — discovery starts automatically.
            </Typography>
          </Box>
        ) : (
          <>
            <Box sx={{ px: 2, py: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Showing {assets.length} of {total} assets
              </Typography>
            </Box>
            <TableContainer sx={{ maxHeight: '72vh' }}>
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Subdomain</TableCell>
                    <TableCell>Domain</TableCell>
                    <TableCell>IP(s)</TableCell>
                    <TableCell>DNS Records</TableCell>
                    <TableCell>Server</TableCell>
                    <TableCell>Tech</TableCell>
                    <TableCell>Discovered</TableCell>
                    <TableCell align="right">Scan</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {assets.map((a) => (
                    <TableRow key={a.id} hover>
                      <TableCell>
                        <Stack direction="row" spacing={0.5} alignItems="center">
                          {safeHref(a.final_url)
                            ? <Link href={safeHref(a.final_url)!} target="_blank" rel="noopener noreferrer" underline="hover">{a.subdomain}</Link>
                            : a.subdomain}
                          {a.is_cloudflare && (
                            <Tooltip title="Behind Cloudflare"><CloudIcon sx={{ fontSize: 15, color: 'warning.main' }} /></Tooltip>
                          )}
                          {a.is_alive && <Chip size="small" color="success" label="alive" sx={{ height: 18, fontSize: 10 }} />}
                          {!a.resolves && <Chip size="small" variant="outlined" label="no DNS" sx={{ height: 18, fontSize: 10 }} />}
                        </Stack>
                      </TableCell>
                      <TableCell sx={{ fontSize: '0.8rem' }}>{a.domain_name}</TableCell>
                      <TableCell sx={{ fontSize: '0.8rem', fontFamily: 'monospace' }}>{a.resolved_ips.join(', ') || '—'}</TableCell>
                      <TableCell sx={{ maxWidth: 240 }}><DnsCell a={a} /></TableCell>
                      <TableCell sx={{ fontSize: '0.8rem', maxWidth: 160 }}>
                        <Typography variant="body2" noWrap title={a.web_server || ''}>{a.web_server || '—'}</Typography>
                        {a.status_code != null && (
                          <Chip size="small" label={a.status_code} sx={{ height: 18, fontSize: 10 }}
                                color={a.status_code < 300 ? 'success' : a.status_code < 400 ? 'info' : a.status_code < 500 ? 'warning' : 'error'} />
                        )}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 180 }}>
                        <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
                          {a.technologies.slice(0, 4).map((t) => <Chip key={t} size="small" variant="outlined" label={t} />)}
                          {a.technologies.length === 0 && '—'}
                        </Stack>
                      </TableCell>
                      <TableCell sx={{ fontSize: '0.78rem', whiteSpace: 'nowrap' }}>{formatDate(a.first_discovered)}</TableCell>
                      <TableCell align="right">
                        <Tooltip title="Re-scan this subdomain (DNS, HTTP, tech, takeover)">
                          <span>
                            <IconButton size="small" color="primary" disabled={scanning.has(a.id)} onClick={() => scanOne(a)}>
                              {scanning.has(a.id) ? <CircularProgress size={16} /> : <RadarIcon fontSize="small" />}
                            </IconButton>
                          </span>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
      </Paper>

      <Snackbar open={Boolean(toast)} autoHideDuration={4000} onClose={() => setToast(null)}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        {toast ? <Alert severity={toast.sev} onClose={() => setToast(null)}>{toast.msg}</Alert> : undefined}
      </Snackbar>
    </Box>
  )
}
