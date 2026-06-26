import { useEffect, useState } from 'react'
import {
  Box, Card, Avatar, Typography, Table, TableBody, TableCell, TableHead, TableRow,
  TableContainer, Chip, useTheme, LinearProgress,
} from '@mui/material'
import { FONT_MONO } from '@/styles/theme'
import { fetchAuditLogs } from '@/data/apiAdapters'
import type { AuditLog } from '@/types/domain'

const actionColor: Record<string, 'secondary' | 'info' | 'success' | 'error' | 'warning' | 'default'> = {
  'auth.login': 'secondary', 'scan.started': 'info', 'scan.completed': 'success',
  'domain.add': 'success', 'domain.delete': 'error', 'vuln.flag_fp': 'warning',
  'settings.update': 'default', 'report.export': 'secondary',
}

export function AuditLogsPage() {
  const theme = useTheme()
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAuditLogs().then(setLogs).catch(() => setLogs([])).finally(() => setLoading(false))
  }, [])

  const avatarColor = (actor: string) =>
    actor === 'admin' ? theme.palette.brand.text : actor === 'scanner' ? theme.palette.info.main : theme.palette.warning.main

  return (
    <Card>
      <TableContainer>
        <Table sx={{ '& td, & th': { borderColor: 'divider' } }}>
          <TableHead>
            <TableRow sx={{ bgcolor: 'surface.subtle' }}>
              {['Actor', 'Action', 'Target', 'Source IP', 'When'].map((h, i) => (
                <TableCell key={h} align={i === 4 ? 'right' : 'left'} sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' }}>{h}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {logs.map((l) => {
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
          </TableBody>
        </Table>
      </TableContainer>
      {loading && <LinearProgress />}
      {!loading && logs.length === 0 && (
        <Box sx={{ p: 4, textAlign: 'center', color: 'text.disabled' }}>No audit log entries.</Box>
      )}
    </Card>
  )
}

const tint = (color: string, mode: string) =>
  mode === 'dark' ? color.replace('rgb(', 'rgba(').replace(')', ',0.16)') : color.replace('rgb(', 'rgba(').replace(')', ',0.12)')
