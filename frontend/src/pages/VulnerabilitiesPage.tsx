import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Box, Button, Card, Avatar, Typography, Table, TableBody, TableCell, TableHead,
  TableRow, TableContainer, TableSortLabel, Select, MenuItem, useTheme, Snackbar, Alert,
  LinearProgress,
} from '@mui/material'
import FileDownloadOutlined from '@mui/icons-material/FileDownloadOutlined'
import { FONT_MONO } from '@/styles/theme'
import { SearchField, Segmented, ConfidenceBar, vulnTypeMeta } from '@/components/common/Widgets'
import { fetchVulnerabilities, setVulnerabilityFalsePositive } from '@/data/apiAdapters'
import { apiErrorMessage } from '@/utils/apiError'
import { Vulnerability, VulnType } from '@/types/domain'

type SortCol = 'host' | 'vuln_type' | 'confidence_score'

export function VulnerabilitiesPage() {
  const theme = useTheme()
  const [vulns, setVulns] = useState<Vulnerability[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [type, setType] = useState<'all' | VulnType>('all')
  const [status, setStatus] = useState<'open' | 'false_positive' | 'all'>('open')
  const [sortBy, setSortBy] = useState<SortCol>('confidence_score')
  const [dir, setDir] = useState<'asc' | 'desc'>('desc')
  const [toast, setToast] = useState('')

  const load = useCallback(async () => {
    try {
      setVulns(await fetchVulnerabilities())
    } catch (err) {
      setToast(apiErrorMessage(err, 'Failed to load vulnerabilities'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const rows = useMemo(() => {
    let list = vulns.filter((v) => v.host.toLowerCase().includes(search.toLowerCase()) || v.domain.toLowerCase().includes(search.toLowerCase()))
    if (type !== 'all') list = list.filter((v) => v.vuln_type === type)
    if (status !== 'all') list = list.filter((v) => v.status === status)
    const sign = dir === 'asc' ? 1 : -1
    return [...list].sort((a, b) => {
      if (sortBy === 'confidence_score') return (a.confidence_score - b.confidence_score) * sign
      return String(a[sortBy]).localeCompare(String(b[sortBy])) * sign
    })
  }, [vulns, search, type, status, sortBy, dir])

  const sort = (col: SortCol) => {
    if (sortBy === col) setDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortBy(col); setDir(col === 'confidence_score' ? 'desc' : 'asc') }
  }

  const toggleFp = async (v: Vulnerability) => {
    const open = v.status === 'open'
    // optimistic flip, reconciled on error
    setVulns((list) => list.map((x) => (x.id === v.id ? { ...x, status: open ? 'false_positive' : 'open' } : x)))
    try {
      await setVulnerabilityFalsePositive(v.id, open)
      setToast(open ? 'Marked as false positive' : 'Restored to open')
    } catch (err) {
      setVulns((list) => list.map((x) => (x.id === v.id ? { ...x, status: v.status } : x)))
      setToast(apiErrorMessage(err, 'Failed to update vulnerability'))
    }
  }

  const head = (col: SortCol, label: string) => (
    <TableCell sortDirection={sortBy === col ? dir : false} sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>
      <TableSortLabel active={sortBy === col} direction={sortBy === col ? dir : 'asc'} onClick={() => sort(col)}>{label}</TableSortLabel>
    </TableCell>
  )

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.2, flexWrap: 'wrap' }}>
        <SearchField value={search} onChange={setSearch} placeholder="Search hosts…" sx={{ flex: 1, minWidth: 220, maxWidth: 340 }} />
        <Select size="small" value={type} onChange={(e) => setType(e.target.value as 'all' | VulnType)} sx={{ fontWeight: 700, fontSize: 13, bgcolor: 'background.paper' }}>
          <MenuItem value="all">All types</MenuItem>
          <MenuItem value="s3_bucket_takeover">S3 bucket takeover</MenuItem>
          <MenuItem value="cname_orphan">CNAME orphan</MenuItem>
          <MenuItem value="dns_orphan">DNS orphan</MenuItem>
        </Select>
        <Segmented value={status} onChange={setStatus} options={[{ value: 'open', label: 'Open' }, { value: 'false_positive', label: 'False positive' }, { value: 'all', label: 'All' }]} />
        <Box sx={{ flex: 1 }} />
        <Button variant="outlined" color="inherit" startIcon={<FileDownloadOutlined />} sx={{ borderColor: 'divider', color: 'text.secondary' }}>Export</Button>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />}

      <Card>
        <TableContainer>
          <Table sx={{ '& td, & th': { borderColor: 'divider' } }}>
            <TableHead>
              <TableRow sx={{ bgcolor: 'surface.subtle' }}>
                {head('host', 'Affected host')}
                {head('vuln_type', 'Type')}
                {head('confidence_score', 'Confidence')}
                <TableCell sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>Found</TableCell>
                <TableCell align="right" sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>Action</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((v) => {
                const m = vulnTypeMeta(v.vuln_type)
                const open = v.status === 'open'
                return (
                  <TableRow key={v.id} hover sx={{ opacity: open ? 1 : 0.55 }}>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.4 }}>
                        <Avatar variant="rounded" sx={{ width: 32, height: 32, bgcolor: tint(theme.palette[m.color].main, theme.palette.mode), color: theme.palette[m.color].main }}><m.Icon sx={{ fontSize: 16 }} /></Avatar>
                        <Box>
                          <Typography sx={{ fontFamily: FONT_MONO, fontSize: 13 }}>{v.host}</Typography>
                          <Typography sx={{ fontSize: 11.5, color: 'text.disabled' }}>{v.domain}</Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell><Typography sx={{ fontSize: 13, fontWeight: 700, color: theme.palette[m.color].main }}>{m.label}</Typography></TableCell>
                    <TableCell><ConfidenceBar value={v.confidence_score} /></TableCell>
                    <TableCell sx={{ fontSize: 13, color: 'text.secondary' }}>{v.found_at}</TableCell>
                    <TableCell align="right">
                      <Button size="small" variant="outlined" color="inherit" onClick={() => toggleFp(v)} sx={{ borderColor: 'divider', color: open ? 'text.secondary' : 'secondary.main', whiteSpace: 'nowrap' }}>
                        {open ? 'Flag FP' : 'Restore'}
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
              {rows.length === 0 && !loading && (
                <TableRow><TableCell colSpan={5} align="center" sx={{ py: 6, color: 'text.disabled' }}>No vulnerabilities match your filters.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      <Snackbar open={!!toast} autoHideDuration={2600} onClose={() => setToast('')} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert severity="success" variant="filled" onClose={() => setToast('')}>{toast}</Alert>
      </Snackbar>
    </Box>
  )
}

const tint = (color: string, mode: string) =>
  mode === 'dark' ? color.replace('rgb(', 'rgba(').replace(')', ',0.16)') : color.replace('rgb(', 'rgba(').replace(')', ',0.12)')
