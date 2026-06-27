import { ReactNode } from 'react'
import {
  Card, CardContent, Box, Typography, Chip, LinearProgress, TextField,
  InputAdornment, useTheme,
} from '@mui/material'
import SearchOutlined from '@mui/icons-material/SearchOutlined'
import Inventory2Outlined from '@mui/icons-material/Inventory2Outlined'
import LinkOutlined from '@mui/icons-material/LinkOutlined'
import DnsOutlined from '@mui/icons-material/DnsOutlined'
import { FONT_MONO } from '@/styles/theme'
import GppMaybeOutlined from '@mui/icons-material/GppMaybeOutlined'
import { RiskLevel, SubdomainStatus, AlertSeverity } from '@/types/domain'

// ---- meta helpers -------------------------------------------------

// Backend vuln_type is open-ended (takeover types or "cve:CVE-…"); map the
// known takeover kinds and fall back to a generic CVE/finding presentation.
export function vulnTypeMeta(type: string) {
  switch (type) {
    case 'subdomain_takeover': return { label: 'Subdomain takeover', color: 'error' as const, Icon: LinkOutlined }
    case 's3_bucket_takeover': return { label: 'S3 takeover', color: 'error' as const, Icon: Inventory2Outlined }
    case 'cname_orphan': return { label: 'CNAME orphan', color: 'warning' as const, Icon: LinkOutlined }
    case 'dns_orphan': return { label: 'DNS orphan', color: 'info' as const, Icon: DnsOutlined }
    default:
      if (type.startsWith('cve:')) return { label: type.slice(4).toUpperCase(), color: 'error' as const, Icon: GppMaybeOutlined }
      return { label: type.replace(/_/g, ' '), color: 'info' as const, Icon: GppMaybeOutlined }
  }
}

export function riskMeta(risk: RiskLevel) {
  switch (risk) {
    case 'high': return { label: 'High', color: 'error' as const }
    case 'medium': return { label: 'Medium', color: 'warning' as const }
    case 'low': return { label: 'Low', color: 'success' as const }
    default: return { label: 'None', color: 'default' as const }
  }
}

export function subStatusMeta(status: SubdomainStatus) {
  switch (status) {
    case 'live': return { label: 'Live', color: 'success' as const }
    case 'orphan': return { label: 'Orphaned', color: 'warning' as const }
    default: return { label: 'DNS orphan', color: 'error' as const }
  }
}

export function severityMeta(sev: AlertSeverity) {
  switch (sev) {
    case 'high': return { label: 'Critical', color: 'error' as const }
    case 'medium': return { label: 'Warning', color: 'warning' as const }
    default: return { label: 'Info', color: 'secondary' as const }
  }
}

export const confidenceColor = (c: number): 'error' | 'warning' | 'info' =>
  c >= 90 ? 'error' : c >= 83 ? 'warning' : 'info'

// Attack-surface change types → label + chip color for the Changes feed.
export function changeTypeMeta(type: string): { label: string; color: 'error' | 'warning' | 'success' | 'info' | 'secondary' | 'default' } {
  switch (type) {
    case 'subdomain_added': return { label: 'New subdomain', color: 'success' }
    case 'subdomain_readded': return { label: 'Reappeared', color: 'success' }
    case 'subdomain_removed': return { label: 'Disappeared', color: 'default' }
    case 'went_live': return { label: 'Went live', color: 'warning' }
    case 'went_offline': return { label: 'Went offline', color: 'default' }
    case 'ip_changed': return { label: 'IP changed', color: 'info' }
    case 'tech_changed': return { label: 'Tech changed', color: 'info' }
    case 'ports_changed': return { label: 'Ports changed', color: 'warning' }
    case 'new_certificate': return { label: 'New certificate', color: 'secondary' }
    default: return { label: type.replace(/_/g, ' '), color: 'default' }
  }
}

// ---- shared widgets ----------------------------------------------

interface TintChipProps { label: string; color: 'error' | 'warning' | 'success' | 'info' | 'secondary' | 'default'; dot?: boolean }
export function TintChip({ label, color, dot }: TintChipProps) {
  const theme = useTheme()
  if (color === 'default') {
    return <Chip size="small" label={label} sx={{ bgcolor: theme.palette.surface.raised, color: 'text.secondary', fontWeight: 700 }} />
  }
  const main = theme.palette[color].main
  return (
    <Chip
      size="small"
      label={label}
      icon={dot ? <Box sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: main, ml: 1 }} /> : undefined}
      sx={{ bgcolor: alphaTint(main, theme.palette.mode), color: main, fontWeight: 700, '& .MuiChip-icon': { ml: 1 } }}
    />
  )
}

function alphaTint(color: string, mode: string) {
  // pale tint for light mode, translucent for dark
  return mode === 'dark'
    ? color.replace('rgb(', 'rgba(').replace(')', ',0.16)')
    : color.replace('rgb(', 'rgba(').replace(')', ',0.12)')
}

export function RiskChip({ risk }: { risk: RiskLevel }) {
  const m = riskMeta(risk)
  return <TintChip label={m.label} color={m.color} dot={m.color !== 'default'} />
}

export function ConfidenceBar({ value }: { value: number }) {
  const theme = useTheme()
  const main = theme.palette[confidenceColor(value)].main
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
      <LinearProgress
        variant="determinate"
        value={value}
        sx={{
          width: 56, height: 6, borderRadius: 3, bgcolor: theme.palette.surface.raised,
          '& .MuiLinearProgress-bar': { bgcolor: main, borderRadius: 3 },
        }}
      />
      <Typography sx={{ fontFamily: FONT_MONO, fontWeight: 700, fontSize: 13, color: main, minWidth: 36 }}>
        {value}%
      </Typography>
    </Box>
  )
}

interface StatCardProps { label: string; value: ReactNode; sub?: string; icon: ReactNode; accent: 'secondary' | 'info' | 'error' | 'warning' }
export function StatCard({ label, value, sub, icon, accent }: StatCardProps) {
  const theme = useTheme()
  const main = accent === 'secondary' ? theme.palette.brand.text : theme.palette[accent].main
  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
          <Typography sx={{ fontSize: 12.5, fontWeight: 700, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '.4px' }}>
            {label}
          </Typography>
          <Box sx={{ width: 32, height: 32, borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: alphaTint(theme.palette[accent === 'secondary' ? 'secondary' : accent].main, theme.palette.mode), color: main }}>
            {icon}
          </Box>
        </Box>
        <Typography sx={{ fontFamily: FONT_MONO, fontWeight: 700, fontSize: 30, lineHeight: 1, letterSpacing: '-1px' }}>
          {value}
        </Typography>
        {sub && <Typography sx={{ fontSize: 12, color: 'text.disabled', mt: 0.75 }}>{sub}</Typography>}
      </CardContent>
    </Card>
  )
}

export interface SegOption<T> { value: T; label: string }
interface SegmentedProps<T> { value: T; options: SegOption<T>[]; onChange: (v: T) => void }
export function Segmented<T extends string>({ value, options, onChange }: SegmentedProps<T>) {
  const theme = useTheme()
  return (
    <Box sx={{ display: 'flex', gap: 0.25, p: '3px', bgcolor: theme.palette.surface.subtle, border: 1, borderColor: 'divider', borderRadius: 2 }}>
      {options.map((o) => {
        const active = o.value === value
        return (
          <Box
            key={o.value}
            component="button"
            onClick={() => onChange(o.value)}
            sx={{
              border: 'none', cursor: 'pointer', px: 1.6, py: 0.8, borderRadius: 1.5,
              fontSize: 12.5, fontWeight: 700, fontFamily: 'inherit',
              color: active ? 'text.primary' : 'text.disabled',
              bgcolor: active ? 'background.paper' : 'transparent',
              boxShadow: active ? theme.shadows[1] : 'none',
            }}
          >
            {o.label}
          </Box>
        )
      })}
    </Box>
  )
}

interface SearchFieldProps { value: string; onChange: (v: string) => void; placeholder?: string; sx?: object }
export function SearchField({ value, onChange, placeholder = 'Search…', sx }: SearchFieldProps) {
  return (
    <TextField
      size="small"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      sx={{ '& .MuiOutlinedInput-root': { bgcolor: 'background.paper' }, ...sx }}
      InputProps={{
        startAdornment: (
          <InputAdornment position="start">
            <SearchOutlined sx={{ fontSize: 18, color: 'text.disabled' }} />
          </InputAdornment>
        ),
      }}
    />
  )
}
