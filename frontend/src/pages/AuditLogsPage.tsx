import React, { useState, useEffect } from 'react'
import {
  Container,
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  Alert,
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material'
import { Navbar } from '@/components/common/Navbar'
import { settingsAPI, type AuditLog, type AuditStats } from '@/api/settings'
import { formatDate } from '@/utils/formatters'

export const AuditLogsPage: React.FC = () => {
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [stats, setStats] = useState<AuditStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterAction, setFilterAction] = useState<string>('')

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)
        const [logsData, statsData] = await Promise.all([
          settingsAPI.listAuditLogs(100),
          settingsAPI.getAuditStats(),
        ])
        setAuditLogs(logsData)
        setStats(statsData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load audit logs')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const getActionColor = (action: string) => {
    switch (action) {
      case 'login':
      case 'logout':
        return 'info'
      case 'create_domain':
      case 'create_api_key':
        return 'success'
      case 'delete_domain':
      case 'delete_api_key':
        return 'error'
      case 'run_scan':
      case 'export_data':
        return 'warning'
      default:
        return 'default'
    }
  }

  const getStatusColor = (status: string) => {
    return status === 'success' ? 'success' : 'error'
  }

  const filteredLogs = filterAction
    ? auditLogs.filter(log => log.action === filterAction)
    : auditLogs

  // Get unique actions for filter
  const uniqueActions = Array.from(new Set(auditLogs.map(log => log.action)))

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
        <Typography variant="h4" sx={{ mb: 4, fontWeight: 'bold' }}>
          Audit Logs
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Statistics Cards */}
        {stats && (
          <Grid container spacing={2} sx={{ mb: 4 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Total Actions
                  </Typography>
                  <Typography variant="h5">{stats.total_actions}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Active API Keys
                  </Typography>
                  <Typography variant="h5">{stats.api_keys_active}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Last Login
                  </Typography>
                  <Typography variant="body2">
                    {formatDate(stats.last_login)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Unique Actions
                  </Typography>
                  <Typography variant="h5">{Object.keys(stats.by_action).length}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Action Distribution */}
        {stats && Object.keys(stats.by_action).length > 0 && (
          <Card sx={{ mb: 4 }}>
            <CardHeader title="Action Distribution" />
            <CardContent>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {Object.entries(stats.by_action).map(([action, count]) => (
                  <Chip
                    key={action}
                    label={`${action}: ${count}`}
                    color={getActionColor(action) as any}
                    variant="outlined"
                  />
                ))}
              </Box>
            </CardContent>
          </Card>
        )}

        {/* Audit Logs Table */}
        <Card>
          <CardHeader
            title="Activity Log"
            subheader={`Showing ${filteredLogs.length} of ${auditLogs.length} entries`}
          />
          <CardContent>
            <FormControl sx={{ mb: 2, minWidth: 200 }}>
              <InputLabel>Filter by Action</InputLabel>
              <Select
                value={filterAction}
                label="Filter by Action"
                onChange={(e) => setFilterAction(e.target.value)}
              >
                <MenuItem value="">All Actions</MenuItem>
                {uniqueActions.map(action => (
                  <MenuItem key={action} value={action}>
                    {action.replace(/_/g, ' ')}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TableContainer>
              <Table>
                <TableHead sx={{ bgcolor: '#f5f5f5' }}>
                  <TableRow>
                    <TableCell>Timestamp</TableCell>
                    <TableCell>Action</TableCell>
                    <TableCell>Resource</TableCell>
                    <TableCell>Details</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>IP Address</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredLogs.length > 0 ? (
                    filteredLogs.map(log => (
                      <TableRow key={log.id}>
                        <TableCell sx={{ fontSize: '0.85rem' }}>
                          {formatDate(log.timestamp)}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={log.action.replace(/_/g, ' ')}
                            color={getActionColor(log.action) as any}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>{log.resource || '-'}</TableCell>
                        <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {log.details || '-'}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={log.status}
                            color={getStatusColor(log.status) as any}
                            size="small"
                          />
                        </TableCell>
                        <TableCell sx={{ fontSize: '0.85rem' }}>
                          {log.ip_address || '-'}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                        <Typography color="textSecondary">
                          No audit logs found
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Container>
    </Box>
  )
}
