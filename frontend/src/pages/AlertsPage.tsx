import React, { useState, useEffect } from 'react'
import {
  Container,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
  Menu,
  MenuItem,
} from '@mui/material'
import { Navbar } from '@/components/common/Navbar'
import { formatDate } from '@/utils/formatters'
import { alertAPI, type Alert as AlertType } from '@/api/alerts'
import FileDownloadIcon from '@mui/icons-material/FileDownload'

type SeverityColor = 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'

const getSeverityColor = (severity: string): SeverityColor => {
  switch (severity) {
    case 'critical':
      return 'error'
    case 'high':
      return 'warning'
    case 'medium':
      return 'info'
    case 'low':
      return 'success'
    default:
      return 'default'
  }
}

export const AlertsPage: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertType[]>([])
  const [selectedAlert, setSelectedAlert] = useState<AlertType | null>(null)
  const [openDialog, setOpenDialog] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [exportAnchor, setExportAnchor] = useState<null | HTMLElement>(null)

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await alertAPI.list('all')
        setAlerts(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch alerts')
        console.error('Error fetching alerts:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchAlerts()
  }, [])

  const handleOpenDialog = (alert: AlertType) => {
    setSelectedAlert(alert)
    setOpenDialog(true)
  }

  const handleCloseDialog = () => {
    setOpenDialog(false)
    setSelectedAlert(null)
  }

  const handleResolveAlert = async (alertId: number): Promise<void> => {
    try {
      await alertAPI.resolve(alertId)
      setAlerts(
        alerts.map((alert) =>
          alert.id === alertId
            ? { ...alert, is_resolved: true, resolved_at: new Date().toISOString() }
            : alert
        )
      )
      handleCloseDialog()
    } catch (err) {
      console.error('Error resolving alert:', err)
    }
  }

  const exportAsJSON = (): void => {
    const data = {
      alerts,
      activeCount: activeAlerts.length,
      resolvedCount: resolvedAlerts.length,
      exportedAt: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `alerts_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    setExportAnchor(null)
  }

  const exportAsCSV = (): void => {
    const csv = [
      ['Security Alerts'],
      ['Domain', 'Alert Type', 'Severity', 'Status', 'Created At', 'Resolved At'],
      ...alerts.map(alert => [
        alert.domain,
        alert.alert_type.replace(/_/g, ' '),
        alert.severity,
        alert.is_resolved ? 'Resolved' : 'Active',
        new Date(alert.created_at).toISOString(),
        alert.resolved_at ? new Date(alert.resolved_at).toISOString() : '',
      ]),
    ]
      .map(row => row.map(cell => `"${cell}"`).join(','))
      .join('\n')
    
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `alerts_${new Date().toISOString().split('T')[0]}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    setExportAnchor(null)
  }

  const activeAlerts = alerts.filter((a) => !a.is_resolved)
  const resolvedAlerts = alerts.filter((a) => a.is_resolved)

  if (loading) {
    return (
      <Box>
        <Navbar />
        <Container maxWidth="lg" sx={{ py: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '500px' }}>
          <CircularProgress />
        </Container>
      </Box>
    )
  }

  return (
    <Box>
      <Navbar />
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
            Security Alerts
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
        <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
          Active: {activeAlerts.length} | Resolved: {resolvedAlerts.length}
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Active Alerts */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Active Alerts
          </Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead sx={{ bgcolor: '#f5f5f5' }}>
                <TableRow>
                  <TableCell>Domain</TableCell>
                  <TableCell>Alert Type</TableCell>
                  <TableCell>Severity</TableCell>
                  <TableCell>Detected</TableCell>
                  <TableCell>Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {activeAlerts.length > 0 ? (
                  activeAlerts.map((alert) => (
                    <TableRow key={alert.id}>
                      <TableCell>{alert.domain}</TableCell>
                      <TableCell>{alert.alert_type.replace(/_/g, ' ')}</TableCell>
                      <TableCell>
                        <Chip
                          label={alert.severity.toUpperCase()}
                          color={getSeverityColor(alert.severity)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{formatDate(alert.created_at)}</TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => handleOpenDialog(alert)}
                        >
                          View Details
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} align="center" sx={{ py: 3 }}>
                      <Typography color="textSecondary">
                        No active alerts
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>

        {/* Resolved Alerts */}
        {resolvedAlerts.length > 0 && (
          <Box>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Resolved Alerts
            </Typography>
            <TableContainer component={Paper}>
              <Table>
                <TableHead sx={{ bgcolor: '#f5f5f5' }}>
                  <TableRow>
                    <TableCell>Domain</TableCell>
                    <TableCell>Alert Type</TableCell>
                    <TableCell>Severity</TableCell>
                    <TableCell>Resolved</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {resolvedAlerts.map((alert) => (
                    <TableRow key={alert.id} sx={{ opacity: 0.7 }}>
                      <TableCell>{alert.domain}</TableCell>
                      <TableCell>{alert.alert_type.replace(/_/g, ' ')}</TableCell>
                      <TableCell>
                        <Chip
                          label={alert.severity.toUpperCase()}
                          color={getSeverityColor(alert.severity)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{alert.resolved_at ? formatDate(alert.resolved_at) : '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {/* Alert Details Dialog */}
        {selectedAlert && (
          <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
            <DialogTitle>Alert Details</DialogTitle>
            <DialogContent>
              <Box sx={{ pt: 2 }}>
                <Typography variant="subtitle2" color="textSecondary">
                  Domain
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {selectedAlert.domain}
                </Typography>

                <Typography variant="subtitle2" color="textSecondary">
                  Alert Type
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {selectedAlert.alert_type.replace(/_/g, ' ')}
                </Typography>

                <Typography variant="subtitle2" color="textSecondary">
                  Severity
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Chip
                    label={selectedAlert.severity.toUpperCase()}
                    color={getSeverityColor(selectedAlert.severity)}
                  />
                </Box>

                <Typography variant="subtitle2" color="textSecondary">
                  Message
                </Typography>
                <Typography variant="body2" sx={{ mb: 2 }}>
                  {selectedAlert.message}
                </Typography>

                <Typography variant="subtitle2" color="textSecondary">
                  Detected At
                </Typography>
                <Typography variant="body2">
                  {formatDate(selectedAlert.created_at)}
                </Typography>
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={handleCloseDialog}>Cancel</Button>
              {!selectedAlert.is_resolved && (
                <Button
                  variant="contained"
                  color="error"
                  onClick={() => handleResolveAlert(selectedAlert.id)}
                >
                  Mark as Resolved
                </Button>
              )}
            </DialogActions>
          </Dialog>
        )}
      </Container>
    </Box>
  )
}
