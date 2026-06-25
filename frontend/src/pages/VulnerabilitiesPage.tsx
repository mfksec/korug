import React, { useState, useEffect } from 'react'
import { Container, Box, Grid, Tabs, Tab, Typography, CircularProgress, Alert, Button, Menu, MenuItem,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, Stack, Paper, Link } from '@mui/material'
import { alpha, useTheme } from '@mui/material/styles'
import { AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { vulnerabilityAPI } from '@/api/vulnerabilities'
import { Vulnerability } from '@/types'
import { StatsCard } from '@/components/dashboard/StatsCard'
import FileDownloadIcon from '@mui/icons-material/FileDownload'

/** Parse a vulnerability into a categorized, display-friendly finding. */
const SEVERITY_COLOR: Record<string, 'error' | 'warning' | 'info' | 'default'> = {
  CRITICAL: 'error', HIGH: 'error', MEDIUM: 'warning', LOW: 'info', UNKNOWN: 'default',
}
function parseFinding(v: Vulnerability) {
  let d: Record<string, unknown> = {}
  try { d = v.details ? JSON.parse(v.details) : {} } catch { /* details may be plain text */ }
  const isCve = v.vuln_type.startsWith('cve:')
  const severity = String(d.severity || (v.confidence_score >= 90 ? 'CRITICAL' : v.confidence_score >= 70 ? 'HIGH' : v.confidence_score >= 50 ? 'MEDIUM' : 'LOW')).toUpperCase()
  return {
    v,
    category: isCve ? 'CVE' : 'Takeover',
    label: isCve ? (d.cve_id as string) || v.vuln_type.slice(4) : v.vuln_type.replace(/_/g, ' '),
    severity,
    summary: (d.summary as string) || (d.message as string) || (typeof v.details === 'string' && v.details && v.details[0] !== '{' ? v.details : ''),
    product: d.product ? `${d.product} ${d.version || ''}`.trim() : '',
    cveId: isCve ? (d.cve_id as string) : '',
  }
}

interface TimelineData {
  date: string
  count: number
}

interface TypeData {
  name: string
  value: number
  color: string
}

interface ConfidenceData {
  severity: string
  score_range: string
  count: number
  percentage: number
}

interface VulnStats {
  total: number
  critical: number
  high: number
  medium: number
  low: number
  avg_confidence: number
  by_type: Record<string, number>
}

// Color mapping for vulnerability types
const TYPE_COLORS: Record<string, string> = {
  'XSS': '#FF6B6B',
  'SQLi': '#4ECDC4',
  'CSRF': '#95E1D3',
  'RCE': '#F38181',
  'Other': '#AA96DA',
}

const SEVERITY_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN']

const FindingsPanel: React.FC<{ findings: Vulnerability[]; severityFilter: string }> = ({ findings, severityFilter }) => {
  const parsed = findings
    .map(parseFinding)
    .filter((f) => severityFilter === 'ALL' || f.severity === severityFilter)
  const groups = ['Takeover', 'CVE'].map((cat) => ({
    cat,
    items: parsed
      .filter((f) => f.category === cat)
      .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)),
  })).filter((g) => g.items.length > 0)

  if (parsed.length === 0) {
    return (
      <Box sx={{ py: 6, textAlign: 'center' }}>
        <Typography color="text.secondary">
          {severityFilter === 'ALL'
            ? 'No findings yet. Scan a subdomain from the Assets page to check it for takeover risks and CVEs.'
            : `No ${severityFilter.toLowerCase()}-severity findings.`}
        </Typography>
      </Box>
    )
  }

  return (
    <Stack spacing={3}>
      {groups.map((g) => (
        <Paper key={g.cat} variant="outlined" sx={{ borderRadius: 2 }}>
          <Box sx={{ px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h6">{g.cat === 'CVE' ? 'CVEs' : 'Subdomain Takeover'}</Typography>
            <Chip size="small" label={g.items.length} />
          </Box>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Severity</TableCell>
                  <TableCell>{g.cat === 'CVE' ? 'CVE' : 'Type'}</TableCell>
                  {g.cat === 'CVE' && <TableCell>Component</TableCell>}
                  <TableCell>Details</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {g.items.map((f) => (
                  <TableRow key={f.v.id} hover sx={{ opacity: f.v.is_false_positive ? 0.5 : 1 }}>
                    <TableCell>
                      <Chip size="small" label={f.severity} color={SEVERITY_COLOR[f.severity] || 'default'} />
                    </TableCell>
                    <TableCell sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
                      {f.cveId
                        ? <Link href={`https://nvd.nist.gov/vuln/detail/${f.cveId}`} target="_blank" rel="noopener noreferrer" underline="hover">{f.label}</Link>
                        : f.label}
                    </TableCell>
                    {g.cat === 'CVE' && <TableCell sx={{ fontSize: '0.82rem' }}>{f.product || '—'}</TableCell>}
                    <TableCell sx={{ fontSize: '0.82rem', color: 'text.secondary', maxWidth: 520 }}>{f.summary || '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      ))}
    </Stack>
  )
}

export const VulnerabilitiesPage: React.FC = () => {
  const theme = useTheme()
  // Theme-aware tokens for recharts (which otherwise hardcodes light-mode grays)
  const axisColor = theme.palette.text.secondary
  const gridColor = theme.palette.divider
  const chartColor = theme.palette.primary.main
  const axisTick = { fill: axisColor, fontSize: 12 }
  const tooltipStyle = {
    backgroundColor: theme.palette.background.paper,
    border: `1px solid ${theme.palette.divider}`,
    borderRadius: 8,
    color: theme.palette.text.primary,
  }
  const legendStyle = { color: axisColor }

  const [tabValue, setTabValue] = useState(0)
  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [trendData, setTrendData] = useState<TimelineData[]>([])
  const [typeData, setTypeData] = useState<TypeData[]>([])
  const [confidenceData, setConfidenceData] = useState<ConfidenceData[]>([])
  const [stats, setStats] = useState<VulnStats | null>(null)
  const [findings, setFindings] = useState<Vulnerability[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [exportAnchor, setExportAnchor] = useState<null | HTMLElement>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)

        // Fetch all data in parallel
        const [trendResponse, statsResponse, confidenceResponse, findingsResponse] = await Promise.all([
          vulnerabilityAPI.getTimeline(30),
          vulnerabilityAPI.getStats(),
          vulnerabilityAPI.getConfidenceDistribution(),
          vulnerabilityAPI.list({ limit: 1000 }),
        ])

        setTrendData(trendResponse)
        setStats(statsResponse)
        setConfidenceData(confidenceResponse)
        setFindings(findingsResponse)

        // Transform by_type data for pie chart
        const typeChartData: TypeData[] = Object.entries(statsResponse.by_type).map(([name, value]) => ({
          name,
          value,
          color: TYPE_COLORS[name] || '#999999',
        }))
        setTypeData(typeChartData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch vulnerability data')
        console.error('Error fetching vulnerability data:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  const exportAsJSON = () => {
    const data = {
      stats,
      timeline: trendData,
      byType: typeData,
      confidenceDistribution: confidenceData,
      exportedAt: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `vulnerabilities_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    setExportAnchor(null)
  }

  const exportAsCSV = () => {
    const csv = [
      ['Vulnerability Statistics'],
      ['Metric', 'Value'],
      ['Total Vulnerabilities', stats?.total || 0],
      ['Critical', stats?.critical || 0],
      ['High', stats?.high || 0],
      ['Medium', stats?.medium || 0],
      ['Low', stats?.low || 0],
      ['Average Confidence', stats?.avg_confidence.toFixed(2) || 0],
      [],
      ['Vulnerabilities by Type'],
      ['Type', 'Count'],
      ...(typeData?.map(t => [t.name, t.value]) || []),
    ]
      .map(row => row.map(cell => `"${cell}"`).join(','))
      .join('\n')
    
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `vulnerabilities_${new Date().toISOString().split('T')[0]}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    setExportAnchor(null)
  }

  if (loading) {
    return (
      <Box>
        <Container maxWidth="lg" sx={{ py: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '500px' }}>
          <CircularProgress />
        </Container>
      </Box>
    )
  }

  // Severity breakdown derived from the findings actually shown (matches the table).
  const parsedAll = findings.map(parseFinding)
  const sevCount = (sev: string) => (sev === 'ALL' ? parsedAll.length : parsedAll.filter((f) => f.severity === sev).length)
  const SEVERITY_CARDS = [
    { key: 'ALL', label: 'All Findings', accent: theme.palette.primary.main },
    { key: 'CRITICAL', label: 'Critical', accent: theme.palette.error.main },
    { key: 'HIGH', label: 'High', accent: theme.palette.error.light },
    { key: 'MEDIUM', label: 'Medium', accent: theme.palette.warning.main },
    { key: 'LOW', label: 'Low', accent: theme.palette.info.main },
  ]

  return (
    <Box>
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
            Vulnerability Analytics
          </Typography>
          <Button
            variant="outlined"
            startIcon={<FileDownloadIcon />}
            onClick={(e) => setExportAnchor(e.currentTarget)}
          >
            Export
          </Button>
          <Menu
            anchorEl={exportAnchor}
            open={Boolean(exportAnchor)}
            onClose={() => setExportAnchor(null)}
          >
            <MenuItem onClick={exportAsJSON}>Export as JSON</MenuItem>
            <MenuItem onClick={exportAsCSV}>Export as CSV</MenuItem>
          </Menu>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 3 }}>
          <Tab label={`Findings (${findings.length})`} />
          <Tab label="30-Day Trend" />
          <Tab label="By Type" />
          <Tab label="Confidence Score" />
          <Tab label="Statistics" />
        </Tabs>

        {/* Findings — clickable severity summary + categorized list (Takeover vs CVE) */}
        {tabValue === 0 && (
          <>
            <Grid container spacing={2} sx={{ mb: 3 }}>
              {SEVERITY_CARDS.map((c) => (
                <Grid item xs={6} sm={4} md={2.4} key={c.key}>
                  <StatsCard
                    title={c.label}
                    value={sevCount(c.key)}
                    accent={c.accent}
                    selected={severityFilter === c.key}
                    onClick={() => setSeverityFilter(c.key)}
                  />
                </Grid>
              ))}
            </Grid>
            <FindingsPanel findings={findings} severityFilter={severityFilter} />
          </>
        )}

        {/* 30-Day Trend Chart */}
        {tabValue === 1 && (
          <Box sx={{ bgcolor: 'background.paper', p: 3, borderRadius: 2, boxShadow: 1 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Vulnerabilities Discovered (Last 30 Days)
            </Typography>
            <ResponsiveContainer width="100%" height={400}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={chartColor} stopOpacity={0.45} />
                    <stop offset="100%" stopColor={chartColor} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                <XAxis dataKey="date" tick={axisTick} stroke={gridColor} />
                <YAxis tick={axisTick} stroke={gridColor} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: gridColor }} />
                <Legend wrapperStyle={legendStyle} />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke={chartColor}
                  strokeWidth={2}
                  fill="url(#trendFill)"
                  activeDot={{ r: 5 }}
                  name="Vulnerabilities Found"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Box>
        )}

        {/* Vulnerability Type Distribution */}
        {tabValue === 2 && (
          <Box sx={{ bgcolor: 'background.paper', p: 3, borderRadius: 2, boxShadow: 1 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Vulnerabilities by Type
            </Typography>
            {typeData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <PieChart>
                  <Pie
                    data={typeData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: ${value}`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {typeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <Typography color="textSecondary">No data available</Typography>
            )}
          </Box>
        )}

        {/* Confidence Score Distribution */}
        {tabValue === 3 && (
          <Box sx={{ bgcolor: 'background.paper', p: 3, borderRadius: 2, boxShadow: 1 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Vulnerabilities by Confidence Score
            </Typography>
            {confidenceData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={confidenceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                  <XAxis dataKey="severity" tick={axisTick} stroke={gridColor} />
                  <YAxis tick={axisTick} stroke={gridColor} allowDecimals={false} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: alpha(chartColor, 0.08) }} />
                  <Legend wrapperStyle={legendStyle} />
                  <Bar dataKey="count" fill={chartColor} name="Count" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Typography color="textSecondary">No data available</Typography>
            )}
          </Box>
        )}

        {/* Statistics */}
        {tabValue === 4 && stats && (
          <Box sx={{ bgcolor: 'background.paper', p: 3, borderRadius: 2, boxShadow: 1 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Summary Statistics
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 2 }}>
              <Box sx={{ p: 2, bgcolor: 'action.hover', borderRadius: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Total Vulnerabilities
                </Typography>
                <Typography variant="h4">{stats.total}</Typography>
              </Box>
              <Box sx={{ p: 2, borderRadius: 2, bgcolor: (t) => alpha(t.palette.error.main, t.palette.mode === 'dark' ? 0.18 : 0.1) }}>
                <Typography variant="body2" color="text.secondary">
                  Critical Severity
                </Typography>
                <Typography variant="h4" color="error.main">{stats.critical}</Typography>
              </Box>
              <Box sx={{ p: 2, borderRadius: 2, bgcolor: (t) => alpha(t.palette.warning.main, t.palette.mode === 'dark' ? 0.18 : 0.12) }}>
                <Typography variant="body2" color="text.secondary">
                  High Severity
                </Typography>
                <Typography variant="h4" color="warning.main">{stats.high}</Typography>
              </Box>
              <Box sx={{ p: 2, borderRadius: 2, bgcolor: (t) => alpha(t.palette.info.main, t.palette.mode === 'dark' ? 0.18 : 0.12) }}>
                <Typography variant="body2" color="text.secondary">
                  Average Confidence
                </Typography>
                <Typography variant="h4" color="info.main">{stats.avg_confidence.toFixed(1)}%</Typography>
              </Box>
            </Box>
          </Box>
        )}
      </Container>
    </Box>
  )
}
