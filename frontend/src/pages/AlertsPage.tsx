import { Box, Card, Avatar, Typography, useTheme } from '@mui/material'
import ChatOutlined from '@mui/icons-material/ChatOutlined'
import GppMaybeOutlined from '@mui/icons-material/GppMaybeOutlined'
import WarningAmberOutlined from '@mui/icons-material/WarningAmberOutlined'
import InfoOutlined from '@mui/icons-material/InfoOutlined'
import { FONT_MONO } from '@/styles/theme'
import { TintChip, severityMeta } from '@/components/common/Widgets'
import { mockAlerts } from '@/data/mock'

const sevIcon = { high: GppMaybeOutlined, medium: WarningAmberOutlined, info: InfoOutlined }

export function AlertsPage() {
  const theme = useTheme()
  return (
    <Card>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, p: 2.2, borderBottom: 1, borderColor: 'divider' }}>
        <ChatOutlined sx={{ fontSize: 18, color: 'secondary.main' }} />
        <Typography variant="h6" sx={{ fontSize: 15 }}>Slack notification history</Typography>
      </Box>
      {mockAlerts.map((a) => {
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
  )
}

const tint = (color: string, mode: string) =>
  mode === 'dark' ? color.replace('rgb(', 'rgba(').replace(')', ',0.16)') : color.replace('rgb(', 'rgba(').replace(')', ',0.12)')
