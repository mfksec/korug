import React, { useCallback, useEffect, useState } from 'react'
import {
  Box, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  TextField, Chip, Stack, Typography, ToggleButtonGroup, ToggleButton, Link,
  Tooltip, CircularProgress, InputAdornment, Button,
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import RefreshIcon from '@mui/icons-material/Refresh'
import CloudIcon from '@mui/icons-material/Cloud'
import { scanAPI, type Asset } from '@/api/scans'
import { apiErrorMessage } from '@/utils/apiError'

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

export const AssetsPage: React.FC = () => {
  const [assets, setAssets] = useState<Asset[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [filter, setFilter] = useState<LiveFilter>('all')

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

  // Debounce the search box; refetch on filter change immediately.
  useEffect(() => {
    const t = window.setTimeout(load, 300)
    return () => window.clearTimeout(t)
  }, [load])

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
              No assets yet. Run a scan on a domain from the Dashboard, then come back here.
            </Typography>
          </Box>
        ) : (
          <>
            <Box sx={{ px: 2, py: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Showing {assets.length} of {total} assets
              </Typography>
            </Box>
            <TableContainer sx={{ maxHeight: '70vh' }}>
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Subdomain</TableCell>
                    <TableCell>Domain</TableCell>
                    <TableCell>IP(s)</TableCell>
                    <TableCell>HTTP</TableCell>
                    <TableCell>Title / Server</TableCell>
                    <TableCell>Tech</TableCell>
                    <TableCell>Sources</TableCell>
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
                          {!a.resolves && <Chip size="small" variant="outlined" label="no DNS" sx={{ height: 18, fontSize: 10 }} />}
                          {a.is_alive && <Chip size="small" color="success" label="alive" sx={{ height: 18, fontSize: 10 }} />}
                        </Stack>
                        {a.cname && <Typography variant="caption" color="text.secondary">CNAME → {a.cname}</Typography>}
                      </TableCell>
                      <TableCell sx={{ fontSize: '0.8rem' }}>{a.domain_name}</TableCell>
                      <TableCell sx={{ fontSize: '0.8rem' }}>{a.resolved_ips.join(', ') || '—'}</TableCell>
                      <TableCell>
                        {a.status_code
                          ? <Chip size="small" label={a.status_code}
                                  color={a.status_code < 300 ? 'success' : a.status_code < 400 ? 'info' : a.status_code < 500 ? 'warning' : 'error'} />
                          : <Chip size="small" label="—" variant="outlined" />}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 220 }}>
                        <Typography variant="body2" noWrap title={a.http_title || ''}>{a.http_title || '—'}</Typography>
                        <Typography variant="caption" color="text.secondary">{a.web_server || ''}</Typography>
                      </TableCell>
                      <TableCell sx={{ maxWidth: 180 }}>
                        <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
                          {a.technologies.slice(0, 4).map((t) => <Chip key={t} size="small" variant="outlined" label={t} />)}
                        </Stack>
                      </TableCell>
                      <TableCell sx={{ maxWidth: 160, fontSize: '0.72rem', color: 'text.secondary' }}>
                        {a.sources.join(', ') || '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
      </Paper>
    </Box>
  )
}
