import React, { useEffect, useState } from 'react'
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Box, Tabs, Tab,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, Stack,
  Typography, CircularProgress, Alert, Link, Tooltip, Grid, Paper,
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import CloudIcon from '@mui/icons-material/Cloud'
import { scanAPI, type ScanResults } from '@/api/scans'
import { apiErrorMessage } from '@/utils/apiError'

interface Props {
  domainId: number | null
  domainName?: string
  open: boolean
  onClose: () => void
}

/** Only treat http(s) URLs as safe link targets (blocks javascript:/data: schemes). */
const safeHref = (url: string | null): string | null => {
  if (!url) return null
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? url : null
  } catch {
    return null
  }
}

const Stat: React.FC<{ label: string; value: number | string }> = ({ label, value }) => (
  <Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center', borderRadius: 2 }}>
    <Typography variant="h5" sx={{ fontWeight: 700 }}>{value}</Typography>
    <Typography variant="caption" color="text.secondary">{label}</Typography>
  </Paper>
)

export const DomainDetailDialog: React.FC<Props> = ({ domainId, domainName, open, onClose }) => {
  const [tab, setTab] = useState(0)
  const [data, setData] = useState<ScanResults | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    if (domainId == null) return
    setLoading(true)
    setError(null)
    try {
      setData(await scanAPI.getResults(domainId))
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to load results'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open && domainId != null) { setTab(0); load() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, domainId])

  const subdomains = data?.subdomains ?? []
  const ipGroups = data?.ip_groups ?? []
  const vulns = data?.vulnerabilities ?? []

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{domainName || data?.domain.domain_name || 'Domain'}</span>
        <Button size="small" startIcon={<RefreshIcon />} onClick={load} disabled={loading}>Refresh</Button>
      </DialogTitle>
      <DialogContent dividers>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {loading && !data ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}><CircularProgress /></Box>
        ) : !data || data.counts.subdomains === 0 ? (
          <Box sx={{ py: 6, textAlign: 'center' }}>
            <Typography color="text.secondary">
              No scan results yet. Run a scan on this domain, then refresh.
            </Typography>
          </Box>
        ) : (
          <>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6} sm={3}><Stat label="Subdomains" value={data.counts.subdomains} /></Grid>
              <Grid item xs={6} sm={3}><Stat label="Alive" value={data.counts.alive} /></Grid>
              <Grid item xs={6} sm={3}><Stat label="Vulnerabilities" value={data.counts.vulnerabilities} /></Grid>
              <Grid item xs={6} sm={3}><Stat label="Cloudflare" value={data.counts.cloudflare} /></Grid>
            </Grid>

            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
              <Tab label={`Subdomains (${subdomains.length})`} />
              <Tab label={`By IP (${ipGroups.length})`} />
              <Tab label={`Vulnerabilities (${vulns.length})`} />
            </Tabs>

            {/* Subdomains */}
            {tab === 0 && (
              <TableContainer sx={{ maxHeight: 460 }}>
                <Table stickyHeader size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Subdomain</TableCell>
                      <TableCell>IP(s)</TableCell>
                      <TableCell>HTTP</TableCell>
                      <TableCell>Title / Server</TableCell>
                      <TableCell>Tech</TableCell>
                      <TableCell>Ports</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {subdomains.map((s) => (
                      <TableRow key={s.id} hover>
                        <TableCell>
                          <Stack direction="row" spacing={0.5} alignItems="center">
                            {safeHref(s.final_url)
                              ? <Link href={safeHref(s.final_url)!} target="_blank" rel="noopener noreferrer" underline="hover">{s.subdomain}</Link>
                              : s.subdomain}
                            {s.is_cloudflare && (
                              <Tooltip title="Behind Cloudflare"><CloudIcon sx={{ fontSize: 15, color: 'warning.main' }} /></Tooltip>
                            )}
                          </Stack>
                          {s.cname && <Typography variant="caption" color="text.secondary">CNAME → {s.cname}</Typography>}
                        </TableCell>
                        <TableCell sx={{ fontSize: '0.8rem' }}>{s.resolved_ips.join(', ') || '—'}</TableCell>
                        <TableCell>
                          {s.status_code
                            ? <Chip size="small" label={s.status_code}
                                    color={s.status_code < 300 ? 'success' : s.status_code < 400 ? 'info' : s.status_code < 500 ? 'warning' : 'error'} />
                            : <Chip size="small" label="—" variant="outlined" />}
                        </TableCell>
                        <TableCell sx={{ maxWidth: 220 }}>
                          <Typography variant="body2" noWrap title={s.http_title || ''}>{s.http_title || '—'}</Typography>
                          <Typography variant="caption" color="text.secondary">{s.web_server || ''}</Typography>
                        </TableCell>
                        <TableCell sx={{ maxWidth: 180 }}>
                          <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
                            {s.technologies.slice(0, 4).map((t) => <Chip key={t} size="small" variant="outlined" label={t} />)}
                          </Stack>
                        </TableCell>
                        <TableCell sx={{ maxWidth: 170 }}>
                          {s.open_ports.length === 0 ? '—' : (
                            <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
                              {s.open_ports.map((p) => (
                                <Tooltip key={p.port} title={[p.service, p.product, p.version].filter(Boolean).join(' ') || ''}>
                                  <Chip size="small" variant="outlined"
                                        label={p.service ? `${p.port}/${p.service}` : `${p.port}`} />
                                </Tooltip>
                              ))}
                            </Stack>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {/* IP groups */}
            {tab === 1 && (
              <TableContainer sx={{ maxHeight: 460 }}>
                <Table stickyHeader size="small">
                  <TableHead>
                    <TableRow><TableCell>IP Address</TableCell><TableCell>Count</TableCell><TableCell>Subdomains</TableCell></TableRow>
                  </TableHead>
                  <TableBody>
                    {ipGroups.map((g) => (
                      <TableRow key={g.ip} hover>
                        <TableCell sx={{ fontWeight: 600 }}>{g.ip}</TableCell>
                        <TableCell>{g.count}</TableCell>
                        <TableCell sx={{ fontSize: '0.85rem' }}>{g.subdomains.join(', ')}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {/* Vulnerabilities */}
            {tab === 2 && (
              vulns.length === 0 ? (
                <Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>No vulnerabilities found.</Typography>
              ) : (
                <TableContainer sx={{ maxHeight: 460 }}>
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow><TableCell>Type</TableCell><TableCell>Confidence</TableCell><TableCell>Details</TableCell></TableRow>
                    </TableHead>
                    <TableBody>
                      {vulns.map((v) => (
                        <TableRow key={v.id} hover>
                          <TableCell>{v.vuln_type.replace(/_/g, ' ')}</TableCell>
                          <TableCell>
                            <Chip size="small" label={`${v.confidence_score.toFixed(0)}%`}
                                  color={v.confidence_score >= 90 ? 'error' : v.confidence_score >= 70 ? 'warning' : 'default'} />
                          </TableCell>
                          <TableCell sx={{ fontSize: '0.8rem', maxWidth: 360 }}>{v.details || '—'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )
            )}
          </>
        )}
      </DialogContent>
      <DialogActions><Button onClick={onClose}>Close</Button></DialogActions>
    </Dialog>
  )
}
