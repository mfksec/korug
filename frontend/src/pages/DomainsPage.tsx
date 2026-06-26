import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Button, Table, TableBody, TableCell, TableHead, TableRow, TableContainer,
  Card, IconButton, TableSortLabel, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, InputAdornment, Typography, useTheme, Snackbar, Alert,
} from '@mui/material'
import AddOutlined from '@mui/icons-material/AddOutlined'
import DeleteOutline from '@mui/icons-material/DeleteOutline'
import PublicOutlined from '@mui/icons-material/PublicOutlined'
import { FONT_MONO } from '@/styles/theme'
import { SearchField, Segmented, RiskChip } from '@/components/common/Widgets'
import { mockDomains } from '@/data/mock'
import { Domain, RiskLevel } from '@/types/domain'

type SortCol = 'domain_name' | 'subdomain_count' | 'open_vulnerabilities' | 'risk'
const riskRank: Record<RiskLevel, number> = { high: 3, medium: 2, low: 1, none: 0 }

export function DomainsPage() {
  const theme = useTheme()
  const navigate = useNavigate()
  const [domains, setDomains] = useState<Domain[]>(mockDomains)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'active' | 'issues' | 'high'>('all')
  const [sortBy, setSortBy] = useState<SortCol>('risk')
  const [dir, setDir] = useState<'asc' | 'desc'>('desc')
  const [addOpen, setAddOpen] = useState(false)
  const [addValue, setAddValue] = useState('')
  const [toast, setToast] = useState('')

  const rows = useMemo(() => {
    let list = domains.filter((d) => d.domain_name.toLowerCase().includes(search.toLowerCase()))
    if (filter === 'active') list = list.filter((d) => d.enabled)
    else if (filter === 'issues') list = list.filter((d) => d.open_vulnerabilities > 0)
    else if (filter === 'high') list = list.filter((d) => d.risk === 'high')
    const sign = dir === 'asc' ? 1 : -1
    return [...list].sort((a, b) => {
      if (sortBy === 'domain_name') return a.domain_name.localeCompare(b.domain_name) * sign
      if (sortBy === 'risk') return (riskRank[a.risk] - riskRank[b.risk]) * sign
      return ((a[sortBy] as number) - (b[sortBy] as number)) * sign
    })
  }, [domains, search, filter, sortBy, dir])

  const sort = (col: SortCol) => {
    if (sortBy === col) setDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortBy(col); setDir(col === 'domain_name' ? 'asc' : 'desc') }
  }

  const addDomain = () => {
    const name = addValue.trim()
    if (!name) return
    const id = Math.max(...domains.map((d) => d.id)) + 1
    setDomains([{ id, domain_name: name, enabled: true, subdomain_count: 0, open_vulnerabilities: 0, risk: 'none', source_count: 2, last_scanned: 'scanning…' }, ...domains])
    setAddOpen(false); setAddValue(''); setToast(`Added ${name} — scan started`)
  }

  const head = (col: SortCol, label: string, align: 'left' | 'right' = 'left') => (
    <TableCell align={align} sortDirection={sortBy === col ? dir : false} sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>
      <TableSortLabel active={sortBy === col} direction={sortBy === col ? dir : 'asc'} onClick={() => sort(col)}>{label}</TableSortLabel>
    </TableCell>
  )

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.2, flexWrap: 'wrap' }}>
        <SearchField value={search} onChange={setSearch} placeholder="Search domains…" sx={{ flex: 1, minWidth: 240, maxWidth: 360 }} />
        <Segmented value={filter} onChange={setFilter} options={[{ value: 'all', label: 'All' }, { value: 'active', label: 'Active' }, { value: 'issues', label: 'With issues' }, { value: 'high', label: 'High risk' }]} />
        <Box sx={{ flex: 1 }} />
        <Button variant="contained" color="primary" startIcon={<AddOutlined />} onClick={() => setAddOpen(true)}>Add domain</Button>
      </Box>

      <Card>
        <TableContainer>
          <Table sx={{ '& td, & th': { borderColor: 'divider' } }}>
            <TableHead>
              <TableRow sx={{ bgcolor: 'surface.subtle' }}>
                {head('domain_name', 'Domain')}
                {head('subdomain_count', 'Subdomains')}
                {head('open_vulnerabilities', 'Issues')}
                {head('risk', 'Risk')}
                <TableCell sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>Last scan</TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((d) => (
                <TableRow key={d.id} hover sx={{ cursor: 'pointer' }} onClick={() => navigate(`/domains/${d.id}`)}>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.4 }}>
                      <Box sx={{ width: 9, height: 9, borderRadius: '50%', bgcolor: d.enabled ? 'success.main' : 'text.disabled' }} />
                      <Box>
                        <Typography sx={{ fontFamily: FONT_MONO, fontWeight: 500, fontSize: 14 }}>{d.domain_name}</Typography>
                        <Typography sx={{ fontSize: 11.5, color: 'text.disabled' }}>{d.source_count} sources · {d.enabled ? 'Active' : 'Paused'}</Typography>
                      </Box>
                    </Box>
                  </TableCell>
                  <TableCell sx={{ fontFamily: FONT_MONO, fontSize: 14 }}>{d.subdomain_count}</TableCell>
                  <TableCell sx={{ fontFamily: FONT_MONO, fontSize: 14, fontWeight: 700, color: d.open_vulnerabilities > 0 ? 'error.main' : 'text.disabled' }}>{d.open_vulnerabilities}</TableCell>
                  <TableCell><RiskChip risk={d.risk} /></TableCell>
                  <TableCell sx={{ fontSize: 13, color: 'text.secondary', whiteSpace: 'nowrap' }}>{d.last_scanned}</TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={(e) => { e.stopPropagation(); setDomains(domains.filter((x) => x.id !== d.id)); setToast('Domain removed') }} sx={{ color: 'text.disabled', '&:hover': { color: 'error.main', bgcolor: theme.palette.error.main.replace('rgb(', 'rgba(').replace(')', ',0.12)') } }}>
                      <DeleteOutline sx={{ fontSize: 18 }} />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {rows.length === 0 && (
                <TableRow><TableCell colSpan={6} align="center" sx={{ py: 6, color: 'text.disabled' }}>No domains match your search or filter.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      <Dialog open={addOpen} onClose={() => setAddOpen(false)} PaperProps={{ sx: { borderRadius: 3, width: 480 } }}>
        <DialogTitle sx={{ fontFamily: theme.typography.h6.fontFamily, fontWeight: 700 }}>Add domain</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontSize: 13, color: 'text.disabled', mb: 2 }}>Körüg will begin discovering subdomains across all enabled sources immediately.</Typography>
          <TextField
            autoFocus fullWidth value={addValue} onChange={(e) => setAddValue(e.target.value)} placeholder="example.com"
            InputProps={{ startAdornment: <InputAdornment position="start"><PublicOutlined sx={{ fontSize: 18, color: 'text.disabled' }} /></InputAdornment>, sx: { fontFamily: FONT_MONO } }}
          />
          <Typography sx={{ fontSize: 12, color: 'text.disabled', mt: 1 }}>Tip: paste multiple domains separated by commas to add in bulk.</Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setAddOpen(false)} sx={{ color: 'text.secondary' }}>Cancel</Button>
          <Button variant="contained" color="primary" startIcon={<AddOutlined />} onClick={addDomain}>Add &amp; scan</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={!!toast} autoHideDuration={2600} onClose={() => setToast('')} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert severity="success" variant="filled" onClose={() => setToast('')}>{toast}</Alert>
      </Snackbar>
    </Box>
  )
}
