import { useEffect, useMemo, useState } from 'react'
import {
  Box, Card, Avatar, Typography, Table, TableBody, TableCell, TableHead, TableRow,
  TableContainer, TableSortLabel, Chip, Select, MenuItem, useTheme, LinearProgress,
} from '@mui/material'
import { FONT_MONO } from '@/styles/theme'
import { SearchField } from '@/components/common/Widgets'
import { fetchAuditLogs } from '@/data/apiAdapters'
import type { AuditLog } from '@/types/domain'

const actionColor: Record<string, 'secondary' | 'info' | 'success' | 'error' | 'warning' | 'default'> = {
  'auth.login': 'secondary', 'scan.started': 'info', 'scan.completed': 'success',
  'domain.add': 'success', 'domain.delete': 'error', 'vuln.flag_fp': 'warning',
  'settings.update': 'default', 'report.export': 'secondary',
}

type SortCol = 'when' | 'actor' | 'action'

export function AuditLogsPage() {
  const theme = useTheme()
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [action, setAction] = useState('all')
  const [sortBy, setSortBy] = useState<SortCol>('when')
  const [dir, setDir] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    fetchAuditLogs().then(setLogs).catch(() => setLogs([])).finally(() => setLoading(false))
  }, [])

  // The API returns logs newest-first; we tag the original index so "when"
  // sorting stays chronological without needing the raw timestamp.
  const indexed = useMemo(() => logs.map((l, i) => ({ l, i })), [logs])
  const actions = useMemo(() => Array.from(new Set(logs.map((l) => l.action))).sort(), [logs])

  const rows = useMemo(() => {
    const q = search.toLowerCase()
    let list = indexed.filter(({ l }) =>
      l.actor.toLowerCase().includes(q) || l.action.toLowerCase().includes(q) || l.target.toLowerCase().includes(q))
    if (action !== 'all') list = list.filter(({ l }) => l.action === action)
    const sign = dir === 'asc' ? 1 : -1
    return [...list].sort((a, b) => {
      if (sortBy === 'actor') return a.l.actor.localeCompare(b.l.actor) * sign
      if (sortBy === 'action') return a.l.action.localeCompare(b.l.action) * sign
      return (a.i - b.i) * sign  // 'when': index 0 is newest
    }).map(({ l }) => l)
  }, [indexed, search, action, sortBy, dir])

  const sort = (col: SortCol) => {
    if (sortBy === col) setDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortBy(col); setDir(col === 'when' ? 'desc' : 'asc') }
  }

  const avatarColor = (actor: string) =>
    actor === 'admin' ? theme.palette.brand.text : actor === 'scanner' ? theme.palette.info.main : theme.palette.warning.main

  const head = (col: SortCol, label: string, align: 'left' | 'right' = 'left') => (
    <TableCell align={align} sortDirection={sortBy === col ? dir : false} sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>
      <TableSortLabel active={sortBy === col} direction={sortBy === col ? dir : 'asc'} onClick={() => sort(col)}>{label}</TableSortLabel>
    </TableCell>
  )

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.2, flexWrap: 'wrap' }}>
        <SearchField value={search} onChange={setSearch} placeholder="Search audit log…" sx={{ flex: 1, minWidth: 220, maxWidth: 340 }} />
        <Select size="small" value={action} onChange={(e) => setAction(e.target.value)} sx={{ fontWeight: 700, fontSize: 13, bgcolor: 'background.paper', minWidth: 160 }}>
          <MenuItem value="all">All actions</MenuItem>
          {actions.map((a) => <MenuItem key={a} value={a}>{a}</MenuItem>)}
        </Select>
      </Box>

      <Card>
        <TableContainer>
          <Table sx={{ '& td, & th': { borderColor: 'divider' } }}>
            <TableHead>
              <TableRow sx={{ bgcolor: 'surface.subtle' }}>
                {head('actor', 'Actor')}
                {head('action', 'Action')}
                <TableCell sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>Target</TableCell>
                <TableCell sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>Source IP</TableCell>
                {head('when', 'When', 'right')}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((l) => {
                const c = actionColor[l.action] || 'default'
                const chipColor = c === 'default' ? theme.palette.text.secondary : c === 'secondary' ? theme.palette.brand.text : theme.palette[c].main
                return (
                  <TableRow key={l.id} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Avatar sx={{ width: 24, height: 24, fontSize: 10, fontWeight: 700, bgcolor: tint(avatarColor(l.actor), theme.palette.mode), color: avatarColor(l.actor) }}>{l.actor.slice(0, 2).toUpperCase()}</Avatar>
                        <Typography sx={{ fontSize: 13, fontWeight: 700 }}>{l.actor}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip label={l.action} size="small" sx={{ fontFamily: FONT_MONO, fontWeight: 500, fontSize: 12, bgcolor: tint(chipColor, theme.palette.mode), color: chipColor }} />
                    </TableCell>
                    <TableCell sx={{ fontFamily: FONT_MONO, fontSize: 12.5, color: 'text.secondary' }}>{l.target}</TableCell>
                    <TableCell sx={{ fontFamily: FONT_MONO, fontSize: 12.5, color: 'text.disabled' }}>{l.source_ip}</TableCell>
                    <TableCell align="right" sx={{ fontSize: 12.5, color: 'text.disabled' }}>{l.created_at}</TableCell>
                  </TableRow>
                )
              })}
              {rows.length === 0 && !loading && (
                <TableRow><TableCell colSpan={5} align="center" sx={{ py: 4, color: 'text.disabled' }}>No audit log entries match your filter.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
        {loading && <LinearProgress />}
      </Card>
    </Box>
  )
}

const tint = (color: string, mode: string) =>
  mode === 'dark' ? color.replace('rgb(', 'rgba(').replace(')', ',0.16)') : color.replace('rgb(', 'rgba(').replace(')', ',0.12)')
