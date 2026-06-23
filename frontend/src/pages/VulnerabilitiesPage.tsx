import React, { useState, useEffect } from 'react'
import { Container, Box, Tabs, Tab, Typography, CircularProgress, Alert, Button, Menu, MenuItem } from '@mui/material'
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { vulnerabilityAPI } from '@/api/vulnerabilities'
import FileDownloadIcon from '@mui/icons-material/FileDownload'

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

export const VulnerabilitiesPage: React.FC = () => {
  const [tabValue, setTabValue] = useState(0)
  const [trendData, setTrendData] = useState<TimelineData[]>([])
  const [typeData, setTypeData] = useState<TypeData[]>([])
  const [confidenceData, setConfidenceData] = useState<ConfidenceData[]>([])
  const [stats, setStats] = useState<VulnStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [exportAnchor, setExportAnchor] = useState<null | HTMLElement>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)

        // Fetch all data in parallel
        const [trendResponse, statsResponse, confidenceResponse] = await Promise.all([
          vulnerabilityAPI.getTimeline(30),
          vulnerabilityAPI.getStats(),
          vulnerabilityAPI.getConfidenceDistribution(),
        ])

        setTrendData(trendResponse)
        setStats(statsResponse)
        setConfidenceData(confidenceResponse)

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
          <Tab label="30-Day Trend" />
          <Tab label="By Type" />
          <Tab label="Confidence Score" />
          <Tab label="Statistics" />
        </Tabs>

        {/* 30-Day Trend Chart */}
        {tabValue === 0 && (
          <Box sx={{ bgcolor: '#fff', p: 3, borderRadius: 2, boxShadow: 1 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Vulnerabilities Discovered (Last 30 Days)
            </Typography>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#1976d2"
                  strokeWidth={2}
                  name="Vulnerabilities Found"
                />
              </LineChart>
            </ResponsiveContainer>
          </Box>
        )}

        {/* Vulnerability Type Distribution */}
        {tabValue === 1 && (
          <Box sx={{ bgcolor: '#fff', p: 3, borderRadius: 2, boxShadow: 1 }}>
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
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <Typography color="textSecondary">No data available</Typography>
            )}
          </Box>
        )}

        {/* Confidence Score Distribution */}
        {tabValue === 2 && (
          <Box sx={{ bgcolor: '#fff', p: 3, borderRadius: 2, boxShadow: 1 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Vulnerabilities by Confidence Score
            </Typography>
            {confidenceData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={confidenceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="severity" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" fill="#1976d2" name="Count" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Typography color="textSecondary">No data available</Typography>
            )}
          </Box>
        )}

        {/* Statistics */}
        {tabValue === 3 && stats && (
          <Box sx={{ bgcolor: '#fff', p: 3, borderRadius: 2, boxShadow: 1 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Summary Statistics
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 2 }}>
              <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
                <Typography variant="body2" color="textSecondary">
                  Total Vulnerabilities
                </Typography>
                <Typography variant="h4">{stats.total}</Typography>
              </Box>
              <Box sx={{ p: 2, bgcolor: '#ffebee', borderRadius: 1 }}>
                <Typography variant="body2" color="textSecondary">
                  Critical Severity
                </Typography>
                <Typography variant="h4">{stats.critical}</Typography>
              </Box>
              <Box sx={{ p: 2, bgcolor: '#fff3e0', borderRadius: 1 }}>
                <Typography variant="body2" color="textSecondary">
                  High Severity
                </Typography>
                <Typography variant="h4">{stats.high}</Typography>
              </Box>
              <Box sx={{ p: 2, bgcolor: '#e3f2fd', borderRadius: 1 }}>
                <Typography variant="body2" color="textSecondary">
                  Average Confidence
                </Typography>
                <Typography variant="h4">{stats.avg_confidence.toFixed(1)}%</Typography>
              </Box>
            </Box>
          </Box>
        )}
      </Container>
    </Box>
  )
}
