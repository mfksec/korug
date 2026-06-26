import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Grid, Card, CardContent, Box, Typography, Button, useTheme, Avatar, LinearProgress,
} from '@mui/material'
import {
  BarChart, Bar, Cell, XAxis, ResponsiveContainer, PieChart, Pie, Tooltip as RTooltip,
} from 'recharts'
import PublicOutlined from '@mui/icons-material/PublicOutlined'
import DnsOutlined from '@mui/icons-material/DnsOutlined'
import GppMaybeOutlined from '@mui/icons-material/GppMaybeOutlined'
import WarningAmberOutlined from '@mui/icons-material/WarningAmberOutlined'
import ChevronRightOutlined from '@mui/icons-material/ChevronRightOutlined'
import { FONT_MONO } from '@/styles/theme'
import { StatCard, vulnTypeMeta, confidenceColor, severityMeta } from '@/components/common/Widgets'
import { fetchDashboard, type DashboardData } from '@/data/apiAdapters'
import type { RiskLevel } from '@/types/domain'

export function DashboardPage() {
  const theme = useTheme()
  const navigate = useNavigate()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboard().then(setData).catch(() => setData(null)).finally(() => setLoading(false))
  }, [])

  const domains = data?.domains ?? []
  const vulns = data?.vulnerabilities ?? []
  const alerts = data?.alerts ?? []
  const trend = data?.trend ?? []

  const openVulns = vulns.filter((v) => v.status === 'open')
  const activeDomains = domains.filter((d) => d.enabled).length
  const highRisk = data?.stats.high_risk_domains ?? domains.filter((d) => d.risk === 'high').length

  const riskCounts = { high: 0, medium: 0, low: 0, none: 0 }
  domains.forEach((d) => { riskCounts[d.risk]++ })
  const riskColors = { high: theme.palette.error.main, medium: theme.palette.warning.main, low: theme.palette.success.main, none: theme.palette.divider }
  const riskLabels = { high: 'High risk', medium: 'Medium risk', low: 'Low risk', none: 'No issues' }
  const pieData = (['high', 'medium', 'low', 'none'] as RiskLevel[]).map((k) => ({ name: riskLabels[k], value: riskCounts[k], color: riskColors[k] }))

  const SectionCard = ({ title, onView, children }: { title: string; onView: () => void; children: React.ReactNode }) => (
    <Card sx={{ height: '100%' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 2.2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" sx={{ fontSize: 15 }}>{title}</Typography>
        <Button size="small" endIcon={<ChevronRightOutlined />} onClick={onView} sx={{ color: 'secondary.main', fontSize: 12.5 }}>View all</Button>
      </Box>
      {children}
    </Card>
  )

  return (
    <Box>
      {loading && <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />}

      <Grid container spacing={2} sx={{ mb: 2.5 }}>
        <Grid item xs={12} sm={6} md={3}><StatCard label="Domains" value={data?.stats.total_domains ?? domains.length} sub={`${activeDomains} actively monitored`} accent="secondary" icon={<PublicOutlined sx={{ fontSize: 17 }} />} /></Grid>
        <Grid item xs={12} sm={6} md={3}><StatCard label="Subdomains" value={data?.totalSubdomains ?? 0} sub="across all sources" accent="info" icon={<DnsOutlined sx={{ fontSize: 17 }} />} /></Grid>
        <Grid item xs={12} sm={6} md={3}><StatCard label="Open issues" value={data?.stats.total_vulnerabilities ?? openVulns.length} sub="awaiting triage" accent="error" icon={<GppMaybeOutlined sx={{ fontSize: 17 }} />} /></Grid>
        <Grid item xs={12} sm={6} md={3}><StatCard label="High risk" value={highRisk} sub="domains need attention" accent="warning" icon={<WarningAmberOutlined sx={{ fontSize: 17 }} />} /></Grid>
      </Grid>

      <Grid container spacing={2} sx={{ mb: 2.5 }}>
        <Grid item xs={12} md={7.5}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="h6" sx={{ fontSize: 16 }}>Findings activity</Typography>
                <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>Vulnerabilities found · last 14 days</Typography>
              </Box>
              <Box sx={{ height: 170, mt: 2 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={trend} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
                    <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: theme.palette.text.disabled, fontFamily: FONT_MONO }} />
                    <RTooltip cursor={{ fill: theme.palette.surface.subtle }} contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="new_subdomains" name="Vulnerabilities" radius={[4, 4, 0, 0]} maxBarSize={26}>
                      {trend.map((d, i) => <Cell key={i} fill={d.has_vulnerability ? theme.palette.error.main : theme.palette.brand.main} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Box>
              <Box sx={{ display: 'flex', gap: 2.5, mt: 1.5, pt: 1.5, borderTop: 1, borderColor: 'divider' }}>
                <Legend color={theme.palette.error.main} label="Vulnerabilities found" />
                <Legend color={theme.palette.brand.main} label="Quiet day" />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4.5}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ fontSize: 16, mb: 2 }}>Risk distribution</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2.5 }}>
                <Box sx={{ position: 'relative', width: 130, height: 130, flexShrink: 0 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={pieData} dataKey="value" innerRadius={44} outerRadius={62} startAngle={90} endAngle={-270} stroke="none">
                        {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <Box sx={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography sx={{ fontFamily: FONT_MONO, fontWeight: 700, fontSize: 24, lineHeight: 1 }}>{domains.length}</Typography>
                    <Typography sx={{ fontSize: 11, color: 'text.disabled' }}>domains</Typography>
                  </Box>
                </Box>
                <Box sx={{ flex: 1 }}>
                  {pieData.map((d) => (
                    <Box key={d.name} sx={{ display: 'flex', alignItems: 'center', gap: 1.1, py: 0.7 }}>
                      <Box sx={{ width: 10, height: 10, borderRadius: '3px', bgcolor: d.color }} />
                      <Typography sx={{ flex: 1, fontSize: 13, color: 'text.secondary' }}>{d.name}</Typography>
                      <Typography sx={{ fontFamily: FONT_MONO, fontWeight: 700, fontSize: 13 }}>{d.value}</Typography>
                    </Box>
                  ))}
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <SectionCard title="Latest vulnerabilities" onView={() => navigate('/vulnerabilities')}>
            {openVulns.slice(0, 4).map((v) => {
              const m = vulnTypeMeta(v.vuln_type)
              const cc = theme.palette[confidenceColor(v.confidence_score)].main
              return (
                <Box key={v.id} sx={{ display: 'flex', alignItems: 'center', gap: 1.5, px: 2.2, py: 1.6, borderBottom: 1, borderColor: 'divider' }}>
                  <Avatar variant="rounded" sx={{ width: 30, height: 30, bgcolor: tint(theme.palette[m.color].main, theme.palette.mode), color: theme.palette[m.color].main }}><m.Icon sx={{ fontSize: 16 }} /></Avatar>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography noWrap sx={{ fontFamily: FONT_MONO, fontSize: 13 }}>{v.host}</Typography>
                    <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>{m.label} · {v.found_at}</Typography>
                  </Box>
                  <Typography sx={{ fontFamily: FONT_MONO, fontWeight: 700, fontSize: 13, color: cc }}>{v.confidence_score}%</Typography>
                </Box>
              )
            })}
            {!loading && openVulns.length === 0 && <Box sx={{ p: 3, color: 'text.disabled', fontSize: 13 }}>No open vulnerabilities.</Box>}
          </SectionCard>
        </Grid>
        <Grid item xs={12} md={6}>
          <SectionCard title="Recent alerts" onView={() => navigate('/alerts')}>
            {alerts.slice(0, 4).map((a) => {
              const m = severityMeta(a.severity)
              const c = m.color === 'secondary' ? theme.palette.brand.text : theme.palette[m.color].main
              return (
                <Box key={a.id} sx={{ display: 'flex', alignItems: 'center', gap: 1.5, px: 2.2, py: 1.6, borderBottom: 1, borderColor: 'divider' }}>
                  <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: c, flexShrink: 0 }} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography sx={{ fontSize: 13, fontWeight: 700 }}>{a.title}</Typography>
                    <Typography noWrap sx={{ fontFamily: FONT_MONO, fontSize: 12, color: 'text.disabled' }}>{a.host}</Typography>
                  </Box>
                  <Typography sx={{ fontSize: 12, color: 'text.disabled', whiteSpace: 'nowrap' }}>{a.created_at}</Typography>
                </Box>
              )
            })}
            {!loading && alerts.length === 0 && <Box sx={{ p: 3, color: 'text.disabled', fontSize: 13 }}>No recent alerts.</Box>}
          </SectionCard>
        </Grid>
      </Grid>
    </Box>
  )
}

const Legend = ({ color, label }: { color: string; label: string }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.9 }}>
    <Box sx={{ width: 10, height: 10, borderRadius: '3px', bgcolor: color }} />
    <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>{label}</Typography>
  </Box>
)

const tint = (color: string, mode: string) =>
  mode === 'dark' ? color.replace('rgb(', 'rgba(').replace(')', ',0.16)') : color.replace('rgb(', 'rgba(').replace(')', ',0.12)')
