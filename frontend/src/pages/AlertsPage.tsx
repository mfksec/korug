import { useEffect, useMemo, useState } from 'react'
import { Box, Card, Avatar, Typography, useTheme, LinearProgress } from '@mui/material'
import ChatOutlined from '@mui/icons-material/ChatOutlined'
import GppMaybeOutlined from '@mui/icons-material/GppMaybeOutlined'
import WarningAmberOutlined from '@mui/icons-material/WarningAmberOutlined'
import InfoOutlined from '@mui/icons-material/InfoOutlined'
import { FONT_MONO } from '@/styles/theme'
import { TintChip, severityMeta, SearchField, Segmented } from '@/components/common/Widgets'
import { fetchAlerts } from '@/data/apiAdapters'
import type { Alert, AlertSeverity } from '@/types/domain'

const sevIcon = { high: GppMaybeOutlined, medium: WarningAmberOutlined, info: InfoOutlined }
const sevRank: Record<AlertSeverity, number> = { high: 3, medium: 2, info: 1 }

export function AlertsPage() {
  const theme = useTheme()
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [sev, setSev] = useState<'all' | AlertSeverity>('all')
  const [sortBy, setSortBy] = useState<'newest' | 'severity'>('newest')

  useEffect(() => {
    fetchAlerts().then(setAlerts).catch(() => setAlerts([])).finally(() => setLoading(false))
  }, [])

  const rows = useMemo(() => {
    const q = search.toLowerCase()
    let list = alerts.filter((a) => a.title.toLowerCase().includes(q) || a.host.toLowerCase().includes(q))
    if (sev !== 'all') list = list.filter((a) => a.severity === sev)
    // `alerts` arrives newest-first from the API; preserve that for "newest".
    if (sortBy === 'severity') list = [...list].sort((a, b) => sevRank[b.severity] - sevRank[a.severity])
    return list
  }, [alerts, search, sev, sortBy])

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.2, flexWrap: 'wrap' }}>
        <SearchField value={search} onChange={setSearch} placeholder="Search alerts…" sx={{ flex: 1, minWidth: 220, maxWidth: 340 }} />
        <Segmented value={sev} onChange={setSev} options={[{ value: 'all', label: 'All' }, { value: 'high', label: 'Critical' }, { value: 'medium', label: 'Warning' }, { value: 'info', label: 'Info' }]} />
        <Box sx={{ flex: 1 }} />
        <Segmented value={sortBy} onChange={setSortBy} options={[{ value: 'newest', label: 'Newest' }, { value: 'severity', label: 'Severity' }]} />
      </Box>

      <Card>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, p: 2.2, borderBottom: 1, borderColor: 'divider' }}>
          <ChatOutlined sx={{ fontSize: 18, color: 'secondary.main' }} />
          <Typography variant="h6" sx={{ fontSize: 15 }}>Notification history</Typography>
        </Box>
        {loading && <LinearProgress />}
        {!loading && rows.length === 0 && (
          <Box sx={{ p: 4, textAlign: 'center', color: 'text.disabled' }}>No alerts match your filter.</Box>
        )}
        {rows.map((a) => {
          const m = severityMeta(a.severity)
          const c = m.color === 'secondary' ? theme.palette.brand.text : theme.palette[m.color].main
          const Icon = sevIcon[a.severity]
          return (
            <Box key={a.id} sx={{ display: 'flex', alignItems: 'center', gap: 1.8, px: 2.2, py: 1.9, borderBottom: 1, borderColor: 'divider' }}>
              <Avatar variant="rounded" sx={{ width: 34, height: 34, bgcolor: tint(c, theme.palette.mode), color: c }}><Icon sx={{ fontSize: 18 }} /></Avatar>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography sx={{ fontSize: 14, fontWeight: 700 }}>{a.title}</Typography>
                <Typography noWrap sx={{ fontFamily: FONT_MONO, fontSize: 12.5, color: 'text.disabled' }}>{a.host}</Typography>
              </Box>
              <TintChip label={m.label} color={m.color} />
              <Typography sx={{ fontSize: 12.5, color: 'text.disabled', whiteSpace: 'nowrap', minWidth: 70, textAlign: 'right' }}>{a.created_at}</Typography>
            </Box>
          )
        })}
      </Card>
    </Box>
  )
}

const tint = (color: string, mode: string) =>
  mode === 'dark' ? color.replace('rgb(', 'rgba(').replace(')', ',0.16)') : color.replace('rgb(', 'rgba(').replace(')', ',0.12)')
