import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Card, Table, TableBody, TableCell, TableHead, TableRow,
  TableContainer, TableSortLabel, Select, MenuItem, Snackbar, Alert, LinearProgress,
} from '@mui/material'
import TimelineOutlined from '@mui/icons-material/TimelineOutlined'
import { FONT_MONO } from '@/styles/theme'
import { SearchField, Segmented, TintChip, changeTypeMeta, EmptyState } from '@/components/common/Widgets'
import { changeAPI, type AssetChange } from '@/api/changes'
import { timeAgo } from '@/data/apiAdapters'
import { apiErrorMessage } from '@/utils/apiError'

type SortCol = 'change_type' | 'target' | 'detected_at'
type Window = '1' | '7' | '30' | 'all'

const TYPES = [
  'subdomain_added', 'subdomain_removed', 'subdomain_readded', 'went_live',
  'went_offline', 'ip_changed', 'tech_changed', 'ports_changed', 'new_certificate',
]

export function ChangesPage() {
  const navigate = useNavigate()
  const [changes, setChanges] = useState<AssetChange[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [type, setType] = useState<'all' | string>('all')
  const [win, setWin] = useState<Window>('7')
  const [sortBy, setSortBy] = useState<SortCol>('detected_at')
  const [dir, setDir] = useState<'asc' | 'desc'>('desc')
  const [toast, setToast] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = win === 'all' ? { limit: 1000 } : { limit: 1000, since_days: Number(win) }
      const { changes } = await changeAPI.list(params)
      setChanges(changes)
    } catch (err) {
      setToast(apiErrorMessage(err, 'Failed to load changes'))
    } finally {
      setLoading(false)
    }
  }, [win])

  useEffect(() => { load() }, [load])

  const rows = useMemo(() => {
    const q = search.toLowerCase()
    let list = changes.filter((c) => (c.target ?? '').toLowerCase().includes(q) || (c.domain_name ?? '').toLowerCase().includes(q))
    if (type !== 'all') list = list.filter((c) => c.change_type === type)
    const sign = dir === 'asc' ? 1 : -1
    return [...list].sort((a, b) => {
      if (sortBy === 'detected_at') return String(a.detected_at ?? '').localeCompare(String(b.detected_at ?? '')) * sign
      if (sortBy === 'target') return (a.target ?? '').localeCompare(b.target ?? '') * sign
      return a.change_type.localeCompare(b.change_type) * sign
    })
  }, [changes, search, type, sortBy, dir])

  const sort = (col: SortCol) => {
    if (sortBy === col) setDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortBy(col); setDir(col === 'detected_at' ? 'desc' : 'asc') }
  }

  const head = (col: SortCol, label: string) => (
    <TableCell sortDirection={sortBy === col ? dir : false} sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>
      <TableSortLabel active={sortBy === col} direction={sortBy === col ? dir : 'asc'} onClick={() => sort(col)}>{label}</TableSortLabel>
    </TableCell>
  )

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.2, flexWrap: 'wrap' }}>
        <SearchField value={search} onChange={setSearch} placeholder="Search hosts…" sx={{ flex: 1, minWidth: 220, maxWidth: 320 }} />
        <Select size="small" value={type} onChange={(e) => setType(e.target.value)} sx={{ fontWeight: 700, fontSize: 13, bgcolor: 'background.paper' }}>
          <MenuItem value="all">All changes</MenuItem>
          {TYPES.map((t) => <MenuItem key={t} value={t}>{changeTypeMeta(t).label}</MenuItem>)}
        </Select>
        <Segmented value={win} onChange={setWin} options={[{ value: '1', label: '24h' }, { value: '7', label: '7d' }, { value: '30', label: '30d' }, { value: 'all', label: 'All' }]} />
      </Box>

      {loading && <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />}

      {!loading && rows.length === 0 ? (
        changes.length === 0 ? (
          <EmptyState
            icon={<TimelineOutlined />}
            title="No changes in this window"
            description="As Körüg re-scans your domains it records attack-surface changes — new or removed subdomains, IP and tech changes, new certificates. Widen the time window or run a scan to populate this feed."
          />
        ) : (
          <EmptyState icon={<TimelineOutlined />} title="No changes match your filters" description="Try a different search term or change type." />
        )
      ) : (
      <Card>
        <TableContainer>
          <Table sx={{ '& td, & th': { borderColor: 'divider' } }}>
            <TableHead>
              <TableRow sx={{ bgcolor: 'surface.subtle' }}>
                {head('change_type', 'Change')}
                {head('target', 'Host')}
                <TableCell sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>Detail</TableCell>
                <TableCell sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>Domain</TableCell>
                {head('detected_at', 'When')}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((c) => {
                const m = changeTypeMeta(c.change_type)
                const detail = [c.old_value, c.new_value].filter(Boolean).join('  →  ') || '—'
                return (
                  <TableRow key={c.id} hover sx={{ cursor: c.subdomain_id ? 'pointer' : 'default' }}
                    onClick={() => c.subdomain_id && navigate(`/subdomains/${c.subdomain_id}`)}>
                    <TableCell><TintChip label={m.label} color={m.color} dot /></TableCell>
                    <TableCell sx={{ fontFamily: FONT_MONO, fontSize: 13 }}>{c.target ?? '—'}</TableCell>
                    <TableCell sx={{ fontFamily: FONT_MONO, fontSize: 12, color: 'text.secondary', maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{detail}</TableCell>
                    <TableCell sx={{ fontSize: 13, color: 'text.secondary' }}>{c.domain_name ?? '—'}</TableCell>
                    <TableCell sx={{ fontSize: 13, color: 'text.disabled', whiteSpace: 'nowrap' }}>{timeAgo(c.detected_at)}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>
      )}

      <Snackbar open={!!toast} autoHideDuration={3000} onClose={() => setToast('')} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert severity="error" variant="filled" onClose={() => setToast('')}>{toast}</Alert>
      </Snackbar>
    </Box>
  )
}
