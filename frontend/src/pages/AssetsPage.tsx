import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Card, Typography, Table, TableBody, TableCell, TableHead, TableRow,
  TableContainer, TableSortLabel, Snackbar, Alert, LinearProgress,
} from '@mui/material'
import { FONT_MONO } from '@/styles/theme'
import { SearchField, Segmented, TintChip } from '@/components/common/Widgets'
import { scanAPI, type Asset } from '@/api/scans'
import { timeAgo } from '@/data/apiAdapters'
import { apiErrorMessage } from '@/utils/apiError'

type SortCol = 'subdomain' | 'domain_name' | 'status' | 'last_seen'
type Filter = 'all' | 'live' | 'gone' | 'resolving'

function assetStatus(a: Asset): { key: string; label: string; color: 'success' | 'warning' | 'error' | 'default' } {
  if (a.is_gone) return { key: 'gone', label: 'Gone', color: 'default' }
  if (a.is_alive) return { key: 'live', label: 'Live', color: 'success' }
  if (a.resolves) return { key: 'resolving', label: 'Resolving', color: 'warning' }
  return { key: 'dns', label: 'No DNS', color: 'error' }
}

const statusRank: Record<string, number> = { live: 3, resolving: 2, dns: 1, gone: 0 }

export function AssetsPage() {
  const navigate = useNavigate()
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [sortBy, setSortBy] = useState<SortCol>('subdomain')
  const [dir, setDir] = useState<'asc' | 'desc'>('asc')
  const [toast, setToast] = useState('')

  const load = useCallback(async () => {
    try {
      const { assets } = await scanAPI.listAssets({ limit: 2000 })
      setAssets(assets)
    } catch (err) {
      setToast(apiErrorMessage(err, 'Failed to load assets'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const rows = useMemo(() => {
    const q = search.toLowerCase()
    let list = assets.filter((a) =>
      a.subdomain.toLowerCase().includes(q) || (a.domain_name ?? '').toLowerCase().includes(q))
    if (filter === 'live') list = list.filter((a) => a.is_alive && !a.is_gone)
    else if (filter === 'gone') list = list.filter((a) => a.is_gone)
    else if (filter === 'resolving') list = list.filter((a) => a.resolves && !a.is_alive && !a.is_gone)
    const sign = dir === 'asc' ? 1 : -1
    return [...list].sort((a, b) => {
      if (sortBy === 'status') return (statusRank[assetStatus(a).key] - statusRank[assetStatus(b).key]) * sign
      if (sortBy === 'last_seen') return (String(a.last_seen ?? '').localeCompare(String(b.last_seen ?? ''))) * sign
      if (sortBy === 'domain_name') return (a.domain_name ?? '').localeCompare(b.domain_name ?? '') * sign
      return a.subdomain.localeCompare(b.subdomain) * sign
    })
  }, [assets, search, filter, sortBy, dir])

  const sort = (col: SortCol) => {
    if (sortBy === col) setDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortBy(col); setDir(col === 'last_seen' || col === 'status' ? 'desc' : 'asc') }
  }

  const head = (col: SortCol, label: string) => (
    <TableCell sortDirection={sortBy === col ? dir : false} sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>
      <TableSortLabel active={sortBy === col} direction={sortBy === col ? dir : 'asc'} onClick={() => sort(col)}>{label}</TableSortLabel>
    </TableCell>
  )

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.2, flexWrap: 'wrap' }}>
        <SearchField value={search} onChange={setSearch} placeholder="Search assets…" sx={{ flex: 1, minWidth: 240, maxWidth: 360 }} />
        <Segmented value={filter} onChange={setFilter} options={[{ value: 'all', label: 'All' }, { value: 'live', label: 'Live' }, { value: 'resolving', label: 'Resolving' }, { value: 'gone', label: 'Gone' }]} />
        <Box sx={{ flex: 1 }} />
        <Typography sx={{ fontSize: 13, color: 'text.disabled' }}>{rows.length} of {assets.length} assets</Typography>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />}

      <Card>
        <TableContainer>
          <Table sx={{ '& td, & th': { borderColor: 'divider' } }}>
            <TableHead>
              <TableRow sx={{ bgcolor: 'surface.subtle' }}>
                {head('subdomain', 'Host')}
                {head('domain_name', 'Domain')}
                <TableCell sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>Addresses</TableCell>
                {head('status', 'Status')}
                {head('last_seen', 'Last seen')}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((a) => {
                const st = assetStatus(a)
                const ips = (a.resolved_ips ?? []).slice(0, 2).join(', ') || (a.cname ? `CNAME ${a.cname}` : '—')
                return (
                  <TableRow key={a.id} hover sx={{ cursor: 'pointer', opacity: a.is_gone ? 0.6 : 1 }} onClick={() => navigate(`/subdomains/${a.id}`)}>
                    <TableCell sx={{ fontFamily: FONT_MONO, fontSize: 13 }}>{a.subdomain}</TableCell>
                    <TableCell sx={{ fontSize: 13, color: 'text.secondary' }}>{a.domain_name}</TableCell>
                    <TableCell sx={{ fontFamily: FONT_MONO, fontSize: 12, color: 'text.secondary' }}>{ips}</TableCell>
                    <TableCell><TintChip label={st.label} color={st.color} dot /></TableCell>
                    <TableCell sx={{ fontSize: 13, color: 'text.disabled', whiteSpace: 'nowrap' }}>{timeAgo(a.last_seen)}</TableCell>
                  </TableRow>
                )
              })}
              {rows.length === 0 && !loading && (
                <TableRow><TableCell colSpan={5} align="center" sx={{ py: 6, color: 'text.disabled' }}>No assets match your search or filter.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      <Snackbar open={!!toast} autoHideDuration={3000} onClose={() => setToast('')} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert severity="error" variant="filled" onClose={() => setToast('')}>{toast}</Alert>
      </Snackbar>
    </Box>
  )
}
